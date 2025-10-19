#!/usr/bin/env python3
"""
Debug batch processing to see what the LLM actually returns.
"""
import sys
sys.path.insert(0, '/home/diana.z/hack/llm_judge')

import json
import openai
import os
from src.load_env import load_env
from normalize_theories import (
    load_seed_ontology, 
    load_valid_papers, 
    create_normalization_prompt_batch,
    OPENAI_MODEL
)

# Load environment
load_env()
openai.api_key = os.getenv("OPENAI_API_KEY")

print("="*80)
print("DEBUG BATCH - CHECK LLM RESPONSE")
print("="*80)

# Load data
ontology = load_seed_ontology()
papers = load_valid_papers()

# Take a full batch for debugging
batch_size = 80
batch = papers[:batch_size]

print(f"\nTesting with {batch_size} papers...")
print(f"Ontology size: {len(ontology)} theories")

# Create prompt
prompt = create_normalization_prompt_batch(batch, ontology)

print(f"\nPrompt length: {len(prompt)} chars")
print(f"Estimated tokens: ~{len(prompt)//4}")

# Make API call
print("\nCalling OpenAI API...")
resp = openai.chat.completions.create(
    model=OPENAI_MODEL,
    messages=[
        {"role": "system", "content": "You are an expert in aging biology. Respond with JSON only."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.2
)

response_text = resp.choices[0].message.content.strip()

print(f"\nAPI Response length: {len(response_text)} chars")
print(f"Tokens used: {resp.usage.total_tokens}")
print(f"  Prompt: {resp.usage.prompt_tokens}")
print(f"  Completion: {resp.usage.completion_tokens}")

# Clean markdown if present
if response_text.startswith("```"):
    response_text = response_text.strip("```json\n").strip("```\n")
    print("\n✓ Cleaned markdown wrapper")

# Parse JSON
try:
    result = json.loads(response_text)
    print("\n✓ Valid JSON received")
    
    # Check structure
    if 'results' in result:
        results_list = result['results']
        print(f"\n✓ Found 'results' key with {len(results_list)} entries")
        print(f"   Expected: {batch_size}")
        
        if len(results_list) != batch_size:
            print(f"\n⚠ MISMATCH: Expected {batch_size} results, got {len(results_list)}")
            print(f"   Missing: {batch_size - len(results_list)} papers")
        
        # Check each result
        print("\nResults breakdown:")
        for i, r in enumerate(results_list, 1):
            theory_name = r.get('initial_theory_name', 'MISSING')
            mapped = r.get('mapped_names', 'MISSING')
            conf = r.get('confidence', 'MISSING')
            keywords = r.get('keywords', [])
            
            if mapped is None:
                status = "null"
            elif isinstance(mapped, list) and len(mapped) > 0 and mapped[0].startswith('NEW_'):
                status = f"NEW ({len(keywords)} keywords)"
            elif isinstance(mapped, list):
                status = f"mapped to {len(mapped)} theories"
            else:
                status = "UNKNOWN"
            
            print(f"  {i}. {theory_name[:50]}: {status}")
    else:
        print("\n✗ No 'results' key in response!")
        print(f"\nKeys found: {list(result.keys())}")
    
    # Show raw response (first 500 chars)
    print("\n" + "-"*80)
    print("RAW RESPONSE (first 1000 chars):")
    print("-"*80)
    print(response_text[:1000])
    print("...")
    
except json.JSONDecodeError as e:
    print(f"\n✗ JSON Parse Error: {e}")
    print("\nRaw response (first 500 chars):")
    print(response_text[:500])

print("\n" + "="*80)
