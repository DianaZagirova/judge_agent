#!/usr/bin/env python3
"""
Normalize aging theories from evaluation results against seed ontology.
Maps theory mentions to standardized theory names using LLM-based matching.
"""
import json
import os
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import openai
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from src.load_env import load_env

# Load environment
load_env()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Configuration
OPENAI_MODEL = "gpt-4.1-nano"  # Cheaper model for mapping
RESULTS_JSON = "/home/diana.z/hack/llm_judge/all_results.json"
ONTOLOGY_JSON = "/home/diana.z/hack/llm_judge/ontologies/seed_ontology/seed_ontology.json"
OUTPUT_JSON = "/home/diana.z/hack/llm_judge/normalization_output/normalized_theories.json"
WORKING_ONTOLOGY_JSON = "/home/diana.z/hack/llm_judge/ontologies/working_ontologies/working_ontology.json"
CACHE_JSON = "/home/diana.z/hack/llm_judge/normalization_output/theory_cache.json"

# Pricing for gpt-4.1-nano (adjust if needed)
COST_PER_1K_PROMPT_TOKENS = 0.00004  # Placeholder - update with actual
COST_PER_1K_COMPLETION_TOKENS = 0.0001  # Placeholder - update with actual

# Batch processing
BATCH_SIZE = 40  # Number of theories per batch (per LLM call) - safe size to avoid incomplete responses
MAX_WORKERS = 10
RETRIES = 3


def load_seed_ontology() -> List[Dict]:
    """Load the seed ontology and extract theory names."""
    with open(ONTOLOGY_JSON, 'r', encoding='utf-8') as f:
        ontology = json.load(f)
    return ontology


def load_theory_cache() -> Dict[str, Dict]:
    """Load theory normalization cache from disk."""
    if os.path.exists(CACHE_JSON):
        try:
            with open(CACHE_JSON, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            print(f"  Loaded cache with {len(cache)} entries")
            return cache
        except Exception as e:
            print(f"  Warning: Could not load cache: {e}")
            return {}
    return {}


def save_theory_cache(cache: Dict[str, Dict]):
    """Save theory normalization cache to disk."""
    try:
        os.makedirs(os.path.dirname(CACHE_JSON), exist_ok=True)
        with open(CACHE_JSON, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  Warning: Could not save cache: {e}")


def save_batch_results(batch_num: int, results: List[Dict], metadata: Dict = None):
    """Save intermediate results after each batch."""
    try:
        temp_dir = "/home/diana.z/hack/llm_judge/normalization_output/temp_batches"
        os.makedirs(temp_dir, exist_ok=True)
        
        output_data = {
            'batch_number': batch_num,
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'metadata': metadata or {}
        }
        
        temp_file = f"{temp_dir}/batch_{batch_num:03d}_results.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Also save cumulative results
        cumulative_file = f"{temp_dir}/cumulative_results.json"
        if os.path.exists(cumulative_file):
            with open(cumulative_file, 'r', encoding='utf-8') as f:
                cumulative = json.load(f)
                cumulative['results'].extend(results)
                cumulative['total_batches'] = batch_num
                cumulative['last_updated'] = datetime.now().isoformat()
        else:
            cumulative = {
                'results': results,
                'total_batches': batch_num,
                'last_updated': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
        
        with open(cumulative_file, 'w', encoding='utf-8') as f:
            json.dump(cumulative, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"  Warning: Could not save batch results: {e}")


def extract_theory_names(ontology: List[Dict]) -> List[str]:
    """Extract all theory names from ontology."""
    return [theory["Theory Name"] for theory in ontology]


def load_valid_papers() -> List[Dict]:
    """Load all valid papers from results JSON."""
    with open(RESULTS_JSON, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Filter only valid papers with non-null aging_theory
    valid_papers = [
        {
            'doi': r['doi'],
            'aging_theory': r.get('aging_theory'),
            'title': r.get('title', ''),
            'reasoning': r.get('reasoning', '')
        }
        for r in results 
        if r.get('result') == 'valid' and r.get('aging_theory')
    ]
    
    print(f"Loaded {len(valid_papers)} valid papers with theories")
    return valid_papers


def create_normalization_prompt_batch(papers_batch: List[Dict], ontology: List[Dict], conservative_mode: bool = False) -> str:
    """Create prompt for batch theory normalization."""
    # Format theories with their main concepts for better understanding
    theories_list_items = []
    for theory in ontology:
        theory_name = theory.get('Theory Name', 'Unknown')
        main_concepts = theory.get('Main Concepts', '')
        # Format main concepts
        if main_concepts:
            # Truncate if too long
            concepts_str = main_concepts[:200] if len(main_concepts) > 200 else main_concepts
            theories_list_items.append(f"- {theory_name}: {concepts_str}")
        else:
            theories_list_items.append(f"- {theory_name}")
    
    theories_list = "\n".join(theories_list_items)
    
    # Create numbered list of theories to normalize
    theories_to_normalize = []
    for i, paper in enumerate(papers_batch, 1):
        theory_text = paper['aging_theory']
        if isinstance(theory_text, list):
            theory_text = ", ".join(str(t) for t in theory_text)
        theories_to_normalize.append(f"{i}. {theory_text}")
    
    theories_input = "\n".join(theories_to_normalize)
    
    # Save to debug files
    debug_dir = "/home/diana.z/hack/llm_judge/debug_prompts"
    os.makedirs(debug_dir, exist_ok=True)
    
    # Save theories_input (what papers are asking to map)
    with open(f"{debug_dir}/theories_input.txt", "w", encoding="utf-8") as f:
        f.write(f"=== THEORIES TO MAP (Batch of {len(papers_batch)}) ===\n\n")
        f.write(theories_input)
    
    # Save theories_list (available ontology)
    with open(f"{debug_dir}/theories_list_ontology.txt", "w", encoding="utf-8") as f:
        f.write(f"=== AVAILABLE STANDARDIZED THEORIES ({len(ontology)} total) ===\n\n")
        f.write(theories_list)
    
    if conservative_mode:
        # CONSERVATIVE MODE PROMPT - Strict, high confidence only, no NEW theories
        prompt = f"""Map the {len(papers_batch)} aging theories to standardized theory names from the provided list.

#CRITICAL: You MUST provide EXACTLY {len(papers_batch)} results in the EXACT same order as the numbered list below. Do not skip any entry.

#INSTRUCTIONS:
1. For EACH numbered theory (1 through {len(papers_batch)}), provide a result in the exact same order
2. Copy the EXACT theory text as "initial_theory_name" - do not rephrase or modify it
3. ONLY map if confidence is HIGH (7-10). If confidence is 6 or below, return null
4. You can map to multiple theories if the text clearly mentions multiple distinct concepts
5. ONLY use theory names that are in the "Available standardized names" list below
6. If text is nonsense/unintelligible, return null
7. MAINTAIN ORDER: Result position must match input position (entry 1 → result 1, entry 2 → result 2, etc.)

#Available standardized names (USE ONLY THESE):
{theories_list}

#Initial theories to map (process in order):     
{theories_input}

#Output Format (JSON only, no markdown):
#IMPORTANT: Return EXACTLY {len(papers_batch)} entries in the results array, in the same order as above.
{{
  "results": [
    {{
      "initial_theory_name": "free radical theory",
      "mapped_names": ["Free Radical/Oxidative Stress Theory"],
      "confidence": [9]
    }},
    {{
      "initial_theory_name": "mitochondrial and telomere theory",
      "mapped_names": ["Mitochondrial Decline Theory (MFRTA)", "Replicative Senescence/Telomere Theory"],
      "confidence": [9, 9]
    }},
    {{
      "initial_theory_name": "very vague complete nonsense concept",
      "mapped_names": null,
      "confidence": null
    }}
  ]
}}
#Answer:
"""
    else:
        # LEARNING MODE PROMPT - Flexible, allows NEW theories
        prompt = f"""Map the {len(papers_batch)} aging theories to standardized theory names, or identify new theories.

#CRITICAL: You MUST provide EXACTLY {len(papers_batch)} results in the EXACT same order as the numbered list below. Do not skip any entry.

#INSTRUCTIONS:
1. For EACH numbered theory (1 through {len(papers_batch)}), provide a result in the exact same order
2. Copy the EXACT theory text as "initial_theory_name" - do not rephrase or modify it  
3. You can map to 1 or multiple theories if the text mentions multiple concepts
4. For each match, provide a confidence score (1-10): how certain you are
5. If theory text is complete nonsense/unintelligible, output null for it
6. If the theory doesn't match any standardized theory well (confidence < 6), prefix with "NEW_" and provide a clean theory name
7. For NEW_ theories, also provide 5-10 relevant keywords that describe this theory
8. MAINTAIN ORDER: Result position must match input position (entry 1 → result 1, entry 2 → result 2, etc.)

#Available standardized names:
{theories_list}

#Initial theories to map (process in order):     
{theories_input}

#Output Format (JSON only, no markdown):
#IMPORTANT: Return EXACTLY {len(papers_batch)} entries in the results array, in the same order as above.
{{
  "results": [
    {{
      "initial_theory_name": "free radical theory",
      "mapped_names": ["Free Radical/Oxidative Stress Theory"],
      "confidence": [9],
      "keywords": []
    }},
    {{
      "initial_theory_name": "mitochondrial and telomere theory",
      "mapped_names": ["Mitochondrial Decline Theory (MFRTA)", "Replicative Senescence/Telomere Theory"],
      "confidence": [9, 9],
      "keywords": []
    }},
    {{
      "initial_theory_name": "very vague complete nonsense concept",
      "mapped_names": null,
      "confidence": null,
      "keywords": []
    }},
    {{
      "initial_theory_name": "quantum theory of aging of human",
      "mapped_names": ["NEW_Quantum Theory"],
      "confidence": [5],
      "keywords": ["quantum mechanics", "aging", "quantum biology", "coherence", "entanglement"]
    }}
  ]
}}
#Answer:
"""
    
    # Save full prompt for debugging
    mode_str = "conservative" if conservative_mode else "learning"
    with open(f"{debug_dir}/last_prompt_{mode_str}.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    
    print(f"  Debug: Saved prompt to {debug_dir}/last_prompt_{mode_str}.txt")
    
    return prompt


def normalize_theory_batch(
    papers_batch: List[Dict], 
    ontology: List[Dict],
    retries: int = RETRIES,
    conservative_mode: bool = False
) -> List[Dict]:
    """
    Normalize a batch of papers' theories using a single LLM call.
    
    Returns list of dicts with:
    - doi
    - initial_theory
    - norm_theories (list)
    - reasoning
    - tokens/cost metadata
    """
    # Initialize results for all papers in batch
    results = []
    for paper in papers_batch:
        results.append({
            'doi': paper['doi'],
            'initial_theory': paper['aging_theory'],
            'norm_theories': None,
            'mapping_reasoning': None,
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'cost_usd': 0.0,
            'success': 0,
            'error_message': None,
            'new_theory_keywords': [],
            'retry_attempt': 0
        })
    
    prompt = create_normalization_prompt_batch(papers_batch, ontology, conservative_mode=conservative_mode)
    
    n = 0
    while n < retries:
        try:
            resp = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert in aging biology. Respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=16500
            )
            
            # Check if response was truncated
            finish_reason = resp.choices[0].finish_reason
            if finish_reason == "length":
                print(f"  ⚠ WARNING: Response truncated due to max_tokens limit!")
                print(f"  Consider increasing max_tokens or reducing batch size")
            
            response_text = resp.choices[0].message.content.strip()
            
            # Save raw response for debugging
            debug_dir = "/home/diana.z/hack/llm_judge/debug_prompts"
            with open(f"{debug_dir}/last_llm_response.json", "w", encoding="utf-8") as f:
                f.write(response_text)
            
            # Clean markdown if present
            if response_text.startswith("```"):
                response_text = response_text.strip("```json\n").strip("```\n").strip("```")
            
            batch_result = json.loads(response_text)
            
            # Distribute tokens/cost across all papers in batch
            total_prompt_tokens = resp.usage.prompt_tokens
            total_completion_tokens = resp.usage.completion_tokens
            total_tokens = resp.usage.total_tokens
            total_cost = calculate_cost(total_prompt_tokens, total_completion_tokens)
            
            tokens_per_paper = total_tokens // len(papers_batch)
            cost_per_paper = total_cost / len(papers_batch)
            
            # Process each result in simplified format
            result_list = batch_result.get('results', [])
            
            # Check if we got results for all papers
            if len(result_list) < len(papers_batch):
                print(f"  ⚠ Warning: LLM returned {len(result_list)}/{len(papers_batch)} results (incomplete response)")
            
            # BUILD NAME-BASED LOOKUP: Map theory names to LLM results
            def normalize_theory_key(theory):
                """Normalize theory text for matching."""
                if isinstance(theory, list):
                    theory = ", ".join(str(t) for t in theory)
                return str(theory).lower().strip()
            
            llm_results_by_name = {}
            for result_item in result_list:
                llm_theory_name = result_item.get('initial_theory_name', '')
                key = normalize_theory_key(llm_theory_name)
                llm_results_by_name[key] = result_item
            
            print(f"  LLM returned {len(llm_results_by_name)} unique theory mappings")
            
            # MATCH BY NAME instead of position
            for idx, paper in enumerate(papers_batch):
                actual_theory = paper['aging_theory']
                actual_theory_str = normalize_theory_key(actual_theory)
                
                # Look up by name
                if actual_theory_str in llm_results_by_name:
                    result_item = llm_results_by_name[actual_theory_str]
                    
                    mapped_names = result_item.get('mapped_names')
                    confidences = result_item.get('confidence')
                    keywords = result_item.get('keywords', [])
                    
                    # Handle null mapping
                    if mapped_names is None or confidences is None:
                        results[idx]['norm_theories'] = None
                        results[idx]['mapping_reasoning'] = f"No confident mapping for: {normalize_theory_key(actual_theory)}"
                        results[idx]['new_theory_keywords'] = []
                    else:
                        # CONSERVATIVE MODE VALIDATION
                        if conservative_mode:
                            # Get seed ontology theory names for validation
                            seed_theory_names = {t.get('Theory Name', '').lower().strip() for t in ontology}
                            
                            # Ensure they are lists
                            if not isinstance(confidences, list):
                                confidences = [confidences]
                            if not isinstance(mapped_names, list):
                                mapped_names = [mapped_names]
                            
                            # Filter out non-string elements (LLM sometimes nests lists incorrectly)
                            mapped_names = [name for name in mapped_names if isinstance(name, str)]
                            
                            # Rule 1: Filter out low confidence (≤6)
                            filtered_pairs = []
                            for i, (name, conf) in enumerate(zip(mapped_names, confidences)):
                                if conf > 6:  # Only keep confidence > 6
                                    filtered_pairs.append((name, conf))
                            
                            # If no high-confidence mappings, set to null
                            if not filtered_pairs:
                                results[idx]['norm_theories'] = None
                                results[idx]['mapping_reasoning'] = f"No high-confidence mapping (all ≤6) for: {normalize_theory_key(actual_theory)}"
                                results[idx]['new_theory_keywords'] = []
                                results[idx]['prompt_tokens'] = total_prompt_tokens // len(papers_batch)
                                results[idx]['completion_tokens'] = total_completion_tokens // len(papers_batch)
                                results[idx]['total_tokens'] = tokens_per_paper
                                results[idx]['cost_usd'] = cost_per_paper
                                results[idx]['success'] = 1
                                continue
                            
                            # Rule 3 & 4: Check if ALL mapped names are in seed ontology (no NEW_ theories)
                            all_in_seed = True
                            some_in_seed = False
                            for name, conf in filtered_pairs:
                                # Remove NEW_ prefix if present
                                clean_name = name[4:] if name.startswith('NEW_') else name
                                if clean_name.lower().strip() in seed_theory_names:
                                    some_in_seed = True
                                else:
                                    all_in_seed = False
                            
                            # Rule 4: If some in seed and some not, set to null
                            if some_in_seed and not all_in_seed:
                                results[idx]['norm_theories'] = None
                                results[idx]['mapping_reasoning'] = f"Mixed seed/non-seed theories (conservative mode) for: {normalize_theory_key(actual_theory)}"
                                results[idx]['new_theory_keywords'] = []
                                results[idx]['prompt_tokens'] = total_prompt_tokens // len(papers_batch)
                                results[idx]['completion_tokens'] = total_completion_tokens // len(papers_batch)
                                results[idx]['total_tokens'] = tokens_per_paper
                                results[idx]['cost_usd'] = cost_per_paper
                                results[idx]['success'] = 1
                                continue
                            
                            # Rule 3: If none in seed (all are NEW), set to null
                            if not all_in_seed:
                                results[idx]['norm_theories'] = None
                                results[idx]['mapping_reasoning'] = f"No seed ontology match (conservative mode) for: {normalize_theory_key(actual_theory)}"
                                results[idx]['new_theory_keywords'] = []
                                results[idx]['prompt_tokens'] = total_prompt_tokens // len(papers_batch)
                                results[idx]['completion_tokens'] = total_completion_tokens // len(papers_batch)
                                results[idx]['total_tokens'] = tokens_per_paper
                                results[idx]['cost_usd'] = cost_per_paper
                                results[idx]['success'] = 1
                                continue
                            
                            # Use filtered high-confidence pairs
                            mapped_names = [name for name, conf in filtered_pairs]
                            confidences = [conf for name, conf in filtered_pairs]
                        else:
                            # Non-conservative mode: ensure they are lists
                            if not isinstance(confidences, list):
                                confidences = [confidences]
                            if not isinstance(mapped_names, list):
                                mapped_names = [mapped_names]
                            
                            # Filter out non-string elements (LLM sometimes nests lists incorrectly)
                            mapped_names = [name for name in mapped_names if isinstance(name, str)]
                        
                        # END CONSERVATIVE MODE VALIDATION
                        
                        # Build norm_theories list from mapped_names and confidences
                        norm_theories = []
                        
                        # Ensure keywords is a list
                        if not isinstance(keywords, list):
                            keywords = []
                        
                        for i, theory_name in enumerate(mapped_names):
                            # Skip if somehow not a string (defensive check)
                            if not isinstance(theory_name, str):
                                continue
                            
                            conf = confidences[i] if i < len(confidences) else confidences[0]
                            
                            # If confidence is low, ensure NEW_ prefix (non-conservative mode only)
                            if not conservative_mode and conf < 6 and not theory_name.startswith("NEW_"):
                                theory_name = f"NEW_{papers_batch[idx]['aging_theory']}"
                            
                            norm_theories.append({
                                'theory': theory_name,
                                'confidence': conf
                            })
                        
                        results[idx]['norm_theories'] = norm_theories if norm_theories else None
                        results[idx]['mapping_reasoning'] = f"Mapped from: {normalize_theory_key(actual_theory)}"
                        results[idx]['new_theory_keywords'] = keywords if keywords else []
                    
                    results[idx]['prompt_tokens'] = total_prompt_tokens // len(papers_batch)
                    results[idx]['completion_tokens'] = total_completion_tokens // len(papers_batch)
                    results[idx]['total_tokens'] = tokens_per_paper
                    results[idx]['cost_usd'] = cost_per_paper
                    results[idx]['success'] = 1
                else:
                    # Paper not found in LLM results - mark as failed
                    results[idx]['success'] = 0
                    results[idx]['error_message'] = f"Theory not found in LLM response: {normalize_theory_key(actual_theory)}"
                    results[idx]['prompt_tokens'] = total_prompt_tokens // len(papers_batch)
                    results[idx]['completion_tokens'] = total_completion_tokens // len(papers_batch)
                    results[idx]['total_tokens'] = tokens_per_paper
                    results[idx]['cost_usd'] = cost_per_paper
            
            return results
            
        except Exception as e:
            print(f"Error normalizing batch (attempt {n+1}/{retries}): {e}")
            for result in results:
                result['error_message'] = str(e)
            n += 1
            if n < retries:
                time.sleep(2)
    
    # Mark all as failed if all retries exhausted
    for result in results:
        result['success'] = 0
    return results


def calculate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost in USD based on token usage."""
    prompt_cost = (prompt_tokens / 1000) * COST_PER_1K_PROMPT_TOKENS
    completion_cost = (completion_tokens / 1000) * COST_PER_1K_COMPLETION_TOKENS
    return prompt_cost + completion_cost


def estimate_total_cost(num_papers: int, batch_size: int = BATCH_SIZE) -> Dict:
    """
    Estimate total cost before running with batched processing.
    
    Args:
        num_papers: Number of papers to process
        batch_size: Number of papers per LLM call
    """
    # Estimate tokens for batched processing
    # Base prompt (ontology + instructions): ~1500 tokens
    # Per theory in batch: ~50 tokens
    # Expected completion per batch: ~100 tokens per theory
    
    num_batches = (num_papers + batch_size - 1) // batch_size  # Ceiling division
    
    avg_prompt_tokens_per_batch = 1500 + (batch_size * 50)  # Base + theories
    avg_completion_tokens_per_batch = batch_size * 100  # ~100 tokens per theory mapping
    
    total_prompt_tokens = avg_prompt_tokens_per_batch * num_batches
    total_completion_tokens = avg_completion_tokens_per_batch * num_batches
    total_tokens = total_prompt_tokens + total_completion_tokens
    
    total_cost = calculate_cost(total_prompt_tokens, total_completion_tokens)
    cost_per_paper = total_cost / num_papers if num_papers > 0 else 0
    
    return {
        'num_papers': num_papers,
        'num_batches': num_batches,
        'batch_size': batch_size,
        'estimated_cost_per_paper': cost_per_paper,
        'estimated_total_cost': total_cost,
        'estimated_total_tokens': total_tokens,
        'model': OPENAI_MODEL
    }


def normalize_theories_sequential(
    papers: List[Dict],
    ontology: List[Dict],
    conservative_mode: bool = False
) -> List[Dict]:
    """
    Process papers sequentially in batches.
    
    Args:
        papers: List of papers to process
        ontology: Seed ontology
        conservative_mode: If True, always use seed ontology. If False, learn from NEW theories.
    """
    
    results = []
    total_papers = len(papers)
    
    # Group papers into batches of BATCH_SIZE (last batch may be smaller)
    paper_batches = []
    for i in range(0, len(papers), BATCH_SIZE):
        paper_batches.append(papers[i:i + BATCH_SIZE])
    
    last_batch_size = len(paper_batches[-1]) if paper_batches else 0
    print(f"\nProcessing {total_papers} papers in {len(paper_batches)} batches SEQUENTIALLY (up to {BATCH_SIZE} theories per LLM call)...")
    if last_batch_size < BATCH_SIZE:
        print(f"  Note: Last batch has {last_batch_size} papers")
    print(f"Model: {OPENAI_MODEL}")
    
    if conservative_mode:
        print(f"Mode: CONSERVATIVE - Using only seed ontology (no learning across batches)")
    else:
        print(f"Mode: LEARNING - NEW theories from each batch will be added to ontology for next batches")
    
    start_time = time.time()
    papers_processed = 0
    
    # Create a working copy of ontology that will grow with NEW theories
    working_ontology = ontology.copy()
    new_theories_count = 0
    
    # Process batches sequentially
    for batch_num, batch in enumerate(paper_batches, 1):
        try:
            # Choose ontology based on mode
            if conservative_mode:
                # Always use original seed ontology
                current_ontology = ontology
            else:
                # Use growing working ontology
                current_ontology = working_ontology
            
            # Process this batch
            batch_results = normalize_theory_batch(batch, current_ontology, conservative_mode=conservative_mode)
            
            # Extract NEW theories from this batch and add to working ontology (only in learning mode)
            if not conservative_mode:
                for result in batch_results:
                    if result['success'] and result['norm_theories']:
                        for theory_match in result['norm_theories']:
                            theory_name = theory_match['theory']
                            # Skip if not a string (defensive check)
                            if not isinstance(theory_name, str):
                                continue
                            if theory_name.startswith('NEW_'):
                                # Clean theory name (remove NEW_ prefix)
                                clean_name = theory_name[4:]  # Remove "NEW_"
                                
                                # Check if this theory is already in working ontology
                                existing = any(
                                    t.get('Theory Name', '') == clean_name 
                                    for t in working_ontology
                                )
                                
                                if not existing:
                                    # Get keywords from result
                                    keywords = result.get('new_theory_keywords', [])
                                    if not keywords:
                                        keywords = [clean_name.lower()]
                                    
                                    # Create main concepts from keywords
                                    main_concepts = f"Novel theory: {clean_name}. Key concepts: {', '.join(keywords[:10])}"
                                    
                                    # Add to working ontology
                                    new_theory_entry = {
                                        'Theory Name': clean_name,
                                        'Seed Keyword List': keywords,
                                        'Theory Category': 'Emerging/Novel',
                                        'Sub-Category': 'Discovered during normalization',
                                        'Main Concepts': main_concepts
                                    }
                                    working_ontology.append(new_theory_entry)
                                    new_theories_count += 1
                                    print(f"  → Added NEW theory to ontology: {clean_name} (keywords: {', '.join(keywords[:5])})")
            
            results.extend(batch_results)
            papers_processed += len(batch_results)
            
            # Save batch results to temp directory
            batch_metadata = {
                'batch_size': len(batch_results),
                'papers_processed': papers_processed,
                'total_papers': total_papers,
                'successful': sum(1 for r in batch_results if r['success']),
                'failed': sum(1 for r in batch_results if not r['success']),
                'conservative_mode': conservative_mode,
                'ontology_size': len(working_ontology)
            }
            save_batch_results(batch_num, batch_results, metadata=batch_metadata)
            
            # Save working ontology after each batch
            # Ensure directory exists
            os.makedirs(os.path.dirname(WORKING_ONTOLOGY_JSON), exist_ok=True)
            with open(WORKING_ONTOLOGY_JSON, 'w', encoding='utf-8') as f:
                json.dump({
                    'batch_number': batch_num,
                    'total_batches': len(paper_batches),
                    'papers_processed': papers_processed,
                    'new_theories_added': new_theories_count,
                    'ontology_size': len(working_ontology),
                    'timestamp': datetime.now().isoformat(),
                    'ontology': working_ontology
                }, f, indent=2, ensure_ascii=False)
            
            # Progress update
            elapsed = time.time() - start_time
            papers_per_sec = papers_processed / elapsed if elapsed > 0 else 0
            eta_seconds = (total_papers - papers_processed) / papers_per_sec if papers_per_sec > 0 else 0
            
            successful = sum(1 for r in results if r['success'])
            failed = len(results) - successful
            total_cost = sum(r['cost_usd'] for r in results)
            
            print(f"Batch {batch_num}/{len(paper_batches)} ({len(batch)} papers): {papers_processed}/{total_papers} total | "
                  f"Success: {successful} | Failed: {failed} | "
                  f"Ontology size: {len(working_ontology)} (+{new_theories_count} new) | "
                  f"Cost: ${total_cost:.4f} | "
                  f"Speed: {papers_per_sec:.2f} papers/sec | "
                  f"ETA: {eta_seconds/60:.1f} min | "
                  f"Saved: batch_{batch_num:03d}_results.json")
            
        except Exception as e:
            print(f"Error processing batch {batch_num}: {e}")
    
    print(f"\n✓ Discovered and added {new_theories_count} new theories to working ontology")
    
    # Retry failed papers with smaller batch size
    failed_papers = [r for r in results if r['success'] == 0]
    if failed_papers:
        print(f"\n{'='*80}")
        print(f"RETRY MECHANISM: Found {len(failed_papers)} failed papers")
        print(f"{'='*80}")
        print(f"Retrying failed papers in smaller batches (batch size: 10)...")
        
        # Extract paper info for failed ones
        failed_dois = {r['doi'] for r in failed_papers}
        retry_papers = [p for p in papers if p['doi'] in failed_dois]
        
        # Process in small batches
        retry_batch_size = 10
        retry_results = []
        
        for i in range(0, len(retry_papers), retry_batch_size):
            retry_batch = retry_papers[i:i + retry_batch_size]
            print(f"  Retrying batch {i//retry_batch_size + 1} ({len(retry_batch)} papers)...")
            
            batch_results = normalize_theory_batch(retry_batch, working_ontology, conservative_mode=conservative_mode)
            retry_results.extend(batch_results)
            
            # Update working ontology with any new theories from retry
            for result in batch_results:
                if result['success'] and result['norm_theories']:
                    for theory_match in result['norm_theories']:
                        theory_name = theory_match['theory']
                        # Skip if not a string (defensive check)
                        if not isinstance(theory_name, str):
                            continue
                        if theory_name.startswith('NEW_'):
                            clean_name = theory_name[4:]
                            existing = any(
                                t.get('Theory Name', '') == clean_name 
                                for t in working_ontology
                            )
                            if not existing:
                                keywords = result.get('new_theory_keywords', [])
                                if not keywords:
                                    keywords = [clean_name.lower()]
                                
                                # Create main concepts from keywords
                                main_concepts = f"Novel theory: {clean_name}. Key concepts: {', '.join(keywords[:10])}"
                                
                                new_theory_entry = {
                                    'Theory Name': clean_name,
                                    'Seed Keyword List': keywords,
                                    'Theory Category': 'Emerging/Novel',
                                    'Sub-Category': 'Discovered during retry',
                                    'Main Concepts': main_concepts
                                }
                                working_ontology.append(new_theory_entry)
                                new_theories_count += 1
        
        # Update results with retry data
        retry_doi_map = {r['doi']: r for r in retry_results}
        for i, result in enumerate(results):
            if result['doi'] in retry_doi_map:
                retry_data = retry_doi_map[result['doi']]
                retry_data['retry_attempt'] = 1  # Mark as retried
                results[i] = retry_data
        
        retry_successful = sum(1 for r in retry_results if r['success'])
        retry_failed = len(retry_results) - retry_successful
        
        print(f"\n✓ Retry complete:")
        print(f"  Retry successful: {retry_successful}/{len(retry_results)}")
        print(f"  Still failed: {retry_failed}")
    
    return results


def main(conservative_mode: bool = False):
    print("="*80)
    print("THEORY NORMALIZATION PIPELINE")
    if conservative_mode:
        print("MODE: CONSERVATIVE (seed ontology only)")
    print("="*80)
    
    # Load data
    print("\n1. Loading seed ontology...")
    ontology = load_seed_ontology()
    available_theories = extract_theory_names(ontology)
    print(f"   Found {len(available_theories)} standardized theories with concepts")
    
    print("\n2. Loading valid papers...")
    papers = load_valid_papers()
    
    if not papers:
        print("No valid papers to process!")
        return
    
    # Estimate cost
    print("\n3. Cost estimation (with batching)...")
    cost_estimate = estimate_total_cost(len(papers), BATCH_SIZE)
    print(f"   Papers to process: {cost_estimate['num_papers']}")
    print(f"   Batches: {cost_estimate['num_batches']} (up to {cost_estimate['batch_size']} papers per batch)")
    print(f"   Model: {cost_estimate['model']}")
    print(f"   Estimated cost per paper: ${cost_estimate['estimated_cost_per_paper']:.6f}")
    print(f"   Estimated total cost: ${cost_estimate['estimated_total_cost']:.4f}")
    print(f"   Estimated total tokens: {cost_estimate['estimated_total_tokens']:,}")
    print(f"   NOTE: Batching saves ~50-70% compared to individual processing!")
    
    # Confirm before proceeding
    response = input("\n   Proceed with normalization? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Aborted by user.")
        return
    
    # Process
    print("\n4. Normalizing theories...")
    start_time = time.time()
    
    results = normalize_theories_sequential(papers, ontology, conservative_mode=conservative_mode)
    elapsed_time = time.time() - start_time
    
    # Calculate statistics
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    total_cost = sum(r['cost_usd'] for r in results)
    total_tokens = sum(r['total_tokens'] for r in results)
    
    with_matches = sum(1 for r in results if r['norm_theories'] is not None)
    without_matches = successful - with_matches
    new_theories = sum(
        1 for r in results 
        if r['norm_theories'] and any('NEW_' in t['theory'] for t in r['norm_theories'])
    )
    
    # Save results
    print("\n5. Saving results...")
    output_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'model': OPENAI_MODEL,
            'total_papers': len(papers),
            'successful': successful,
            'failed': failed,
            'with_matches': with_matches,
            'without_matches': without_matches,
            'new_theories': new_theories,
            'total_tokens': total_tokens,
            'total_cost_usd': total_cost,
            'processing_time_seconds': elapsed_time
        },
        'results': results
    }
    
    # Add timestamp to output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.dirname(OUTPUT_JSON)
    output_base = os.path.basename(OUTPUT_JSON).replace('.json', '')
    timestamped_output = os.path.join(output_dir, f"{output_base}_{timestamp}.json")
    
    with open(timestamped_output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Also save to the default location (without timestamp) for easy access
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"   Saved to: {timestamped_output}")
    print(f"   Also saved to: {OUTPUT_JSON}")
    
    # Final summary
    print("\n" + "="*80)
    print("NORMALIZATION COMPLETE")
    print("="*80)
    print(f"Total papers processed: {len(papers)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Papers with theory matches: {with_matches}")
    print(f"Papers with no matches (null): {without_matches}")
    print(f"Papers with NEW_ theories: {new_theories}")
    print(f"Total tokens used: {total_tokens:,}")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"Processing time: {elapsed_time/60:.2f} minutes")
    print(f"Average time per paper: {elapsed_time/len(papers):.2f} seconds")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Normalize aging theories against seed ontology",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--test", action="store_true",
                        help="Test mode - process only 10 papers")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help=f"Batch size (default: {BATCH_SIZE})")
    parser.add_argument("--conservative", action="store_true",
                        help="Conservative mode - use only seed ontology, don't learn from NEW theories")
    
    args = parser.parse_args()
    
    if args.test:
        print("\n*** TEST MODE: Processing only 10 papers ***\n")
        # Temporarily override for testing
        ontology = load_seed_ontology()
        available_theories = extract_theory_names(ontology)
        papers = load_valid_papers()[:10]
        
        cost_estimate = estimate_total_cost(len(papers))
        print(f"Test cost estimate: ${cost_estimate['estimated_total_cost']:.4f}")
        
        if args.conservative:
            print("Running in CONSERVATIVE mode")
        
        results = normalize_theories_sequential(papers, ontology, conservative_mode=args.conservative)
        
        # Calculate test statistics
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        total_cost = sum(r['cost_usd'] for r in results)
        total_tokens = sum(r['total_tokens'] for r in results)
        
        with_matches = sum(1 for r in results if r['norm_theories'] is not None)
        without_matches = successful - with_matches
        new_theories = sum(
            1 for r in results 
            if r['norm_theories'] and any('NEW_' in t['theory'] for t in r['norm_theories'])
        )
        
        # Save test results
        test_output_file = OUTPUT_JSON.replace('.json', '_test.json')
        output_dir = os.path.dirname(test_output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        output_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'model': OPENAI_MODEL,
                'total_papers': len(papers),
                'successful': successful,
                'failed': failed,
                'with_matches': with_matches,
                'without_matches': without_matches,
                'new_theories': new_theories,
                'total_tokens': total_tokens,
                'total_cost_usd': total_cost,
                'mode': 'TEST'
            },
            'results': results
        }
        
        with open(test_output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Test results saved to: {test_output_file}")
        
        # Show sample results
        print("\n*** SAMPLE RESULTS ***")
        for r in results[:3]:
            print(f"\nDOI: {r['doi']}")
            print(f"Initial: {r['initial_theory']}")
            print(f"Normalized: {r['norm_theories']}")
            print(f"Reasoning: {r['mapping_reasoning']}")
            print(f"Cost: ${r['cost_usd']:.6f}")
    else:
        BATCH_SIZE = args.batch_size
        # Pass conservative mode to main
        main(conservative_mode=args.conservative)
