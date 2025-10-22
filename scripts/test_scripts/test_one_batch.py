#!/usr/bin/env python3
"""
Test one batch to investigate failures.
"""
import sys
sys.path.insert(0, '/home/diana.z/hack/llm_judge')

from normalize_theories import (
    load_seed_ontology, 
    load_valid_papers, 
    normalize_theory_batch,
    BATCH_SIZE
)

print("="*80)
print("SINGLE BATCH TEST - INVESTIGATING FAILURES")
print("="*80)

# Load data
print("\n1. Loading ontology...")
ontology = load_seed_ontology()
print(f"   Loaded {len(ontology)} theories")

print("\n2. Loading papers...")
papers = load_valid_papers()
print(f"   Found {len(papers)} valid papers")

# Take first batch
batch = papers[:BATCH_SIZE]
print(f"\n3. Testing with first batch ({len(batch)} papers)...")

# Process
results = normalize_theory_batch(batch, ontology)

# Analyze results
successful = [r for r in results if r['success'] == 1]
failed = [r for r in results if r['success'] == 0]

print("\n" + "="*80)
print("RESULTS ANALYSIS")
print("="*80)
print(f"Total papers in batch: {len(results)}")
print(f"Successful: {len(successful)}")
print(f"Failed: {len(failed)}")

if failed:
    print("\n" + "-"*80)
    print("FAILED PAPERS DETAILS")
    print("-"*80)
    for i, paper in enumerate(failed, 1):
        print(f"\n{i}. DOI: {paper['doi']}")
        print(f"   Initial theory: {paper['initial_theory']}")
        print(f"   Error: {paper['error_message']}")
        
    # Group by error type
    print("\n" + "-"*80)
    print("ERROR TYPES")
    print("-"*80)
    from collections import Counter
    error_types = Counter(f['error_message'] for f in failed if f['error_message'])
    for error, count in error_types.most_common():
        print(f"{count:3d} papers: {error[:100]}...")
else:
    print("\n✓ No failures! All papers processed successfully.")

# Show some successful mappings
if successful:
    print("\n" + "-"*80)
    print("SAMPLE SUCCESSFUL MAPPINGS (first 5)")
    print("-"*80)
    for i, paper in enumerate(successful[:5], 1):
        print(f"\n{i}. DOI: {paper['doi']}")
        print(f"   Initial: {paper['initial_theory']}")
        if paper['norm_theories']:
            for theory in paper['norm_theories']:
                print(f"   → {theory['theory']} (confidence: {theory['confidence']})")
        else:
            print(f"   → null (no mapping)")

# Cost summary
total_cost = sum(r['cost_usd'] for r in results)
total_tokens = sum(r['total_tokens'] for r in results)
print("\n" + "="*80)
print("COST SUMMARY")
print("="*80)
print(f"Total tokens: {total_tokens:,}")
print(f"Total cost: ${total_cost:.6f}")
print(f"Cost per paper: ${total_cost/len(results):.6f}")
print("="*80)
