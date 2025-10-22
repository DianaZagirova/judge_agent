#!/usr/bin/env python3
"""
🧬 Aging Theory Paper Filter - Interactive Demo Script

This script demonstrates the AI-powered aging theory paper classification system
using a test database of sample papers. It showcases the system's ability to:

1. Load papers from a test database
2. Process them through the LLM classification system
3. Display results with confidence scores and reasoning
4. Show performance metrics and cost analysis

Usage:
    python demo_aging_filter.py [--limit N] [--verbose]

Requirements:
    - Virtual environment activated
    - OpenAI API key configured
    - Test database available at specified path
"""

import os
import sys
import sqlite3
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from demo_llm_judge import demo_llm_judge as llm_judge
from load_env import load_env

# Load environment variables
load_env()

# Configuration
TEST_DB_PATH = Path("/home/diana.z/hack/download_papers_pubmed/paper_collection_test/data/papers.db")
DEFAULT_LIMIT = 5
DEFAULT_VERBOSE = True

def print_header():
    """Print a nice header for the demo."""
    print("=" * 80)
    print("🧬 AGING THEORY PAPER FILTER - INTERACTIVE DEMO")
    print("=" * 80)
    print("🤖 AI-Powered Scientific Literature Classification System")
    print("📊 Demonstrating high-throughput paper filtering capabilities")
    print("=" * 80)
    print()

def print_section(title: str):
    """Print a section header."""
    print(f"\n🔹 {title}")
    print("-" * 60)

def validate_environment() -> bool:
    """Validate that the environment is properly configured."""
    print_section("Environment Validation")
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment may not be activated")
        print("   Consider running: source venv/bin/activate")
    
    # Check OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("   Please set your OpenAI API key in the .env file")
        return False
    else:
        print("✅ OpenAI API key configured")
    
    # Check test database
    if not TEST_DB_PATH.exists():
        print(f"❌ Error: Test database not found at {TEST_DB_PATH}")
        return False
    else:
        print(f"✅ Test database found: {TEST_DB_PATH}")
    
    # Check database content
    try:
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM papers")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            print("❌ Error: Test database is empty")
            return False
        else:
            print(f"✅ Test database contains {count} papers")
    
    except Exception as e:
        print(f"❌ Error accessing test database: {e}")
        return False
    
    print("✅ Environment validation passed!")
    return True

def load_sample_papers(limit: int) -> List[Dict]:
    """Load sample papers from the test database."""
    print_section(f"Loading Sample Papers (Limit: {limit})")
    
    try:
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get papers with title and abstract
        query = """
            SELECT doi, pmid, title, abstract 
            FROM papers 
            WHERE title IS NOT NULL 
            AND abstract IS NOT NULL 
            AND abstract != ''
            ORDER BY RANDOM()
            LIMIT ?
        """
        
        cursor.execute(query, (limit,))
        papers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        print(f"✅ Loaded {len(papers)} papers from test database")
        
        # Display paper previews
        for i, paper in enumerate(papers, 1):
            title_preview = paper['title'][:80] + "..." if len(paper['title']) > 80 else paper['title']
            abstract_preview = paper['abstract'][:150] + "..." if len(paper['abstract']) > 150 else paper['abstract']
            print(f"\n📄 Paper {i}:")
            print(f"   Title: {title_preview}")
            print(f"   Abstract: {abstract_preview}")
            print(f"   DOI: {paper['doi']}")
        
        return papers
    
    except Exception as e:
        print(f"❌ Error loading papers: {e}")
        return []

def process_papers(papers: List[Dict], verbose: bool = True) -> List[Dict]:
    """Process papers through the LLM classification system."""
    print_section("AI Processing Pipeline")
    
    results = []
    total_tokens = 0
    total_cost = 0.0
    start_time = time.time()
    
    print("🤖 Starting AI classification process...")
    print("⚡ Using GPT-4 Mini for efficient processing")
    print("🧠 Chain-of-thought reasoning enabled")
    print("⏳ Processing may take a moment due to API rate limits...")
    print()
    
    for i, paper in enumerate(papers, 1):
        print(f"Processing paper {i}/{len(papers)}...", end=" ", flush=True)
        
        try:
            # Create input text
            jointtext = f"{paper['title']}: {paper['abstract']}"
            
            # Call LLM judge
            llm_result = llm_judge(jointtext)
            
            # Extract results
            result = {
                'paper_info': paper,
                'classification': llm_result.get('result'),
                'aging_theory': llm_result.get('aging_theory'),
                'type': llm_result.get('type'),
                'reasoning': llm_result.get('reasoning'),
                'confidence_score': llm_result.get('confidence_score'),
                'tokens': llm_result.get('_tokens', {}),
                'success': True
            }
            
            # Calculate cost (approximate)
            tokens = result['tokens']
            if tokens:
                prompt_tokens = tokens.get('prompt_tokens', 0)
                completion_tokens = tokens.get('completion_tokens', 0)
                total_tokens += tokens.get('total_tokens', 0)
                
                # Approximate cost calculation
                cost = (prompt_tokens / 1000) * 0.0004 + (completion_tokens / 1000) * 0.0016
                total_cost += cost
                result['cost'] = cost
            
            results.append(result)
            
            # Status indicator
            status_emoji = "✅" if result['classification'] == 'valid' else "⚠️" if result['classification'] == 'doubted' else "❌"
            print(f"{status_emoji} {result['classification'].upper()}")
            
            # Add a small delay to make the output more readable
            time.sleep(0.1)
            
            if verbose:
                print(f"   🎯 Classification: {result['classification']}")
                print(f"   🧠 Theory: {result['aging_theory'] or 'N/A'}")
                print(f"   📊 Confidence: {result['confidence_score']}/10")
                print(f"   💰 Cost: ${result.get('cost', 0):.4f}")
                if result['reasoning']:
                    reasoning_preview = result['reasoning'][:100] + "..." if len(result['reasoning']) > 100 else result['reasoning']
                    print(f"   💭 Reasoning: {reasoning_preview}")
                print()
        
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'paper_info': paper,
                'success': False,
                'error': str(e)
            })
    
    processing_time = time.time() - start_time
    
    print(f"\n⚡ Processing completed in {processing_time:.2f} seconds")
    print(f"📊 Total tokens used: {total_tokens:,}")
    print(f"💰 Total cost: ${total_cost:.4f}")
    print(f"🚀 Average speed: {len(papers)/processing_time:.2f} papers/second")
    
    return results

def analyze_results(results: List[Dict]) -> Dict:
    """Analyze and summarize the classification results."""
    print_section("Results Analysis")
    
    # Count classifications
    classifications = {}
    confidence_scores = []
    successful_results = [r for r in results if r.get('success', False)]
    
    for result in successful_results:
        classification = result.get('classification', 'unknown')
        classifications[classification] = classifications.get(classification, 0) + 1
        
        if result.get('confidence_score'):
            confidence_scores.append(result['confidence_score'])
    
    # Calculate statistics
    total_processed = len(successful_results)
    valid_count = classifications.get('valid', 0)
    doubted_count = classifications.get('doubted', 0)
    not_valid_count = classifications.get('not_valid', 0)
    
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    
    print("📈 Classification Summary:")
    print(f"   ✅ Valid aging-theory papers: {valid_count} ({100*valid_count/total_processed:.1f}%)")
    print(f"   ⚠️  Doubted papers: {doubted_count} ({100*doubted_count/total_processed:.1f}%)")
    print(f"   ❌ Not valid papers: {not_valid_count} ({100*not_valid_count/total_processed:.1f}%)")
    print(f"   📊 Average confidence: {avg_confidence:.1f}/10")
    
    # Show examples of each category
    print("\n🔍 Example Classifications:")
    
    for category in ['valid', 'doubted', 'not_valid']:
        examples = [r for r in successful_results if r.get('classification') == category]
        if examples:
            example = examples[0]
            title_preview = example['paper_info']['title'][:60] + "..." if len(example['paper_info']['title']) > 60 else example['paper_info']['title']
            print(f"\n   {category.upper()}:")
            print(f"   📄 {title_preview}")
            print(f"   🧠 Theory: {example.get('aging_theory', 'N/A')}")
            print(f"   📊 Confidence: {example.get('confidence_score', 'N/A')}/10")
            if example.get('reasoning'):
                reasoning_preview = example['reasoning'][:80] + "..." if len(example['reasoning']) > 80 else example['reasoning']
                print(f"   💭 Reasoning: {reasoning_preview}")
    
    return {
        'total_processed': total_processed,
        'classifications': classifications,
        'avg_confidence': avg_confidence,
        'success_rate': len(successful_results) / len(results) if results else 0
    }

def print_performance_metrics(results: List[Dict]):
    """Print performance and cost metrics."""
    print_section("Performance Metrics")
    
    successful_results = [r for r in results if r.get('success', False)]
    
    if not successful_results:
        print("❌ No successful results to analyze")
        return
    
    # Calculate metrics
    total_tokens = sum(r.get('tokens', {}).get('total_tokens', 0) for r in successful_results)
    total_cost = sum(r.get('cost', 0) for r in successful_results)
    
    print("⚡ Processing Efficiency:")
    print(f"   📊 Total papers processed: {len(successful_results)}")
    print(f"   🔤 Total tokens used: {total_tokens:,}")
    print(f"   💰 Total cost: ${total_cost:.4f}")
    print(f"   📈 Average cost per paper: ${total_cost/len(successful_results):.4f}")
    print(f"   🎯 Success rate: {len(successful_results)/len(results)*100:.1f}%")
    
    print("\n🚀 Scalability Projections:")
    cost_per_1k = (total_cost / len(successful_results)) * 1000
    print(f"   💰 Cost for 1,000 papers: ~${cost_per_1k:.2f}")
    print(f"   💰 Cost for 10,000 papers: ~${cost_per_1k * 10:.2f}")
    print(f"   💰 Cost for 100,000 papers: ~${cost_per_1k * 100:.2f}")

def save_demo_results(results: List[Dict], output_file: str = "demo_results.json"):
    """Save demo results to a JSON file."""
    print_section("Saving Results")
    
    try:
        # Prepare results for JSON serialization
        json_results = []
        for result in results:
            json_result = {
                'timestamp': datetime.now().isoformat(),
                'paper_info': result['paper_info'],
                'classification': result.get('classification'),
                'aging_theory': result.get('aging_theory'),
                'type': result.get('type'),
                'reasoning': result.get('reasoning'),
                'confidence_score': result.get('confidence_score'),
                'tokens': result.get('tokens'),
                'cost': result.get('cost'),
                'success': result.get('success', False),
                'error': result.get('error')
            }
            json_results.append(json_result)
        
        with open(output_file, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        print(f"✅ Demo results saved to: {output_file}")
        print(f"📊 {len(json_results)} results saved")
    
    except Exception as e:
        print(f"❌ Error saving results: {e}")

def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(
        description="🧬 Aging Theory Paper Filter - Interactive Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_aging_filter.py                    # Run with default settings (5 papers)
  python demo_aging_filter.py --limit 10         # Process 10 papers
  python demo_aging_filter.py --limit 3 --quiet # Process 3 papers quietly
        """
    )
    
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"Number of papers to process (default: {DEFAULT_LIMIT})")
    parser.add_argument("--verbose", action="store_true", default=DEFAULT_VERBOSE,
                        help="Show detailed processing information")
    parser.add_argument("--quiet", action="store_true",
                        help="Run in quiet mode (overrides --verbose)")
    parser.add_argument("--save-results", action="store_true",
                        help="Save results to JSON file")
    
    args = parser.parse_args()
    
    # Override verbose if quiet is specified
    if args.quiet:
        args.verbose = False
    
    # Print header
    print_header()
    
    # Validate environment
    if not validate_environment():
        print("\n❌ Environment validation failed. Please fix the issues above.")
        sys.exit(1)
    
    # Load sample papers
    papers = load_sample_papers(args.limit)
    if not papers:
        print("\n❌ Failed to load sample papers.")
        sys.exit(1)
    
    # Process papers
    results = process_papers(papers, verbose=args.verbose)
    
    # Analyze results
    analysis = analyze_results(results)
    
    # Show performance metrics
    print_performance_metrics(results)
    
    # Save results if requested
    if args.save_results:
        save_demo_results(results)
    
    # Final summary
    print_section("Demo Complete")
    print("🎉 Aging Theory Paper Filter demo completed successfully!")
    print("🚀 The system demonstrated efficient AI-powered paper classification")
    print("📊 Results show the system's capability to process papers at scale")
    print("💡 This technology can be applied to large literature collections")
    
    print("\n" + "=" * 80)
    print("Thank you for trying the Aging Theory Paper Filter! 🧬")
    print("=" * 80)

if __name__ == "__main__":
    main()
