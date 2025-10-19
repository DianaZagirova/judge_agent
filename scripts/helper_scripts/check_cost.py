#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/diana.z/hack/llm_judge')
from normalize_theories import estimate_total_cost, BATCH_SIZE

# Estimate for 20,000 papers
estimate = estimate_total_cost(20000, BATCH_SIZE)

print(f"Cost Estimate for 20,000 Papers")
print(f"="*50)
print(f"Number of papers: {estimate['num_papers']:,}")
print(f"Number of batches: {estimate['num_batches']:,}")
print(f"Batch size: {estimate['batch_size']}")
print(f"Model: {estimate['model']}")
print(f"\nEstimated tokens:")
print(f"  Total tokens: {estimate['estimated_total_tokens']:,}")
print(f"\nEstimated costs:")
print(f"  Cost per paper: ${estimate['estimated_cost_per_paper']:.6f}")
print(f"  TOTAL COST: ${estimate['estimated_total_cost']:.2f}")
print(f"\nNote: With batching (50 papers per call), saves ~50-70% vs individual calls")

# Also show breakdown
print(f"\n" + "="*50)
print(f"Cost Breakdown:")
print(f"  Prompt tokens per batch: ~4,000")
print(f"  Completion tokens per batch: ~5,000")
print(f"  Total API calls needed: {estimate['num_batches']:,}")
print(f"  Processing time estimate: ~{estimate['num_batches'] * 5 / 60:.1f} minutes")
