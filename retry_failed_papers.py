#!/usr/bin/env python3
"""
Retry failed papers from a previous normalization run.
"""
import json
import sys
sys.path.insert(0, '/home/diana.z/hack/llm_judge')

from normalize_theories import (
    load_seed_ontology,
    normalize_theory_batch,
    OUTPUT_JSON
)

print("="*80)
print("RETRY FAILED PAPERS")
print("="*80)

# Load previous results
try:
    with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"\n✗ Error: {OUTPUT_JSON} not found")
    print("  Run the main normalization first: python normalize_theories.py")
    sys.exit(1)

results = data['results']
metadata = data['metadata']

# Identify failed papers
failed_papers = [r for r in results if r['success'] == 0]

if not failed_papers:
    print("\n✓ No failed papers found! All papers processed successfully.")
    sys.exit(0)

print(f"\nFound {len(failed_papers)} failed papers")
print(f"Total papers: {len(results)}")
print(f"Failure rate: {len(failed_papers)/len(results)*100:.1f}%")

# Show error summary
from collections import Counter
error_types = Counter(r['error_message'] for r in failed_papers if r['error_message'])
print("\nError types:")
for error, count in error_types.most_common(5):
    print(f"  {count:3d} papers: {error[:80]}...")

# Ask for confirmation
response = input(f"\nRetry {len(failed_papers)} failed papers? (yes/no): ").strip().lower()
if response not in ['yes', 'y']:
    print("Aborted.")
    sys.exit(0)

# Load ontology
print("\nLoading ontology...")
ontology = load_seed_ontology()
print(f"Loaded {len(ontology)} theories")

# Reconstruct paper info for failed papers
print("\nPreparing papers for retry...")
retry_papers = []
for r in failed_papers:
    retry_papers.append({
        'doi': r['doi'],
        'aging_theory': r['initial_theory'],
        'title': '',
        'reasoning': ''
    })

# Retry in small batches
print(f"\nRetrying in batches of 10...")
retry_batch_size = 10
retry_results = []

for i in range(0, len(retry_papers), retry_batch_size):
    retry_batch = retry_papers[i:i + retry_batch_size]
    batch_num = i // retry_batch_size + 1
    total_batches = (len(retry_papers) + retry_batch_size - 1) // retry_batch_size
    
    print(f"  Batch {batch_num}/{total_batches} ({len(retry_batch)} papers)...", end=' ')
    
    batch_results = normalize_theory_batch(retry_batch, ontology)
    retry_results.extend(batch_results)
    
    successful = sum(1 for r in batch_results if r['success'])
    print(f"{successful}/{len(retry_batch)} succeeded")

# Update original results
print("\nUpdating results...")
retry_doi_map = {r['doi']: r for r in retry_results}

for i, result in enumerate(results):
    if result['doi'] in retry_doi_map:
        retry_data = retry_doi_map[result['doi']]
        retry_data['retry_attempt'] = (result.get('retry_attempt', 0)) + 1
        results[i] = retry_data

# Calculate new statistics
successful = sum(1 for r in results if r['success'])
failed = len(results) - successful
total_cost = sum(r['cost_usd'] for r in results)
total_tokens = sum(r['total_tokens'] for r in results)

with_matches = sum(1 for r in results if r['norm_theories'] is not None and r['success'])
without_matches = successful - with_matches
new_theories = sum(
    1 for r in results 
    if r['norm_theories'] and any('NEW_' in t['theory'] for t in r['norm_theories'])
)

# Update metadata
metadata['successful'] = successful
metadata['failed'] = failed
metadata['with_matches'] = with_matches
metadata['without_matches'] = without_matches
metadata['new_theories'] = new_theories
metadata['total_tokens'] = total_tokens
metadata['total_cost_usd'] = total_cost
metadata['retry_run'] = True
metadata['retried_papers'] = len(retry_papers)

# Save updated results
print(f"\nSaving updated results to {OUTPUT_JSON}...")
output_data = {
    'metadata': metadata,
    'results': results
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)

# Summary
retry_successful = sum(1 for r in retry_results if r['success'])
retry_failed = len(retry_results) - retry_successful
retry_cost = sum(r['cost_usd'] for r in retry_results)

print("\n" + "="*80)
print("RETRY SUMMARY")
print("="*80)
print(f"Papers retried: {len(retry_papers)}")
print(f"  Successful: {retry_successful}")
print(f"  Still failed: {retry_failed}")
print(f"  Retry cost: ${retry_cost:.6f}")
print(f"\nOverall Statistics:")
print(f"  Total papers: {len(results)}")
print(f"  Total successful: {successful} ({successful/len(results)*100:.1f}%)")
print(f"  Total failed: {failed} ({failed/len(results)*100:.1f}%)")
print(f"  Total cost: ${total_cost:.4f}")
print("="*80)

if failed > 0:
    print(f"\n⚠ {failed} papers still failed. You can run this script again to retry.")
else:
    print(f"\n✓ All papers processed successfully!")
