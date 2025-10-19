#!/usr/bin/env python3
"""
View and analyze normalized theory results.
"""
import json
import argparse
from collections import Counter, defaultdict


NORMALIZED_JSON = "/home/diana.z/hack/llm_judge/normalized_theories.json"


def load_results():
    """Load normalized results."""
    with open(NORMALIZED_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def print_summary():
    """Print summary statistics."""
    data = load_results()
    metadata = data['metadata']
    results = data['results']
    
    print("\n" + "="*80)
    print("NORMALIZED THEORIES SUMMARY")
    print("="*80)
    
    print(f"\nProcessing Metadata:")
    print(f"  Timestamp: {metadata['timestamp']}")
    print(f"  Model: {metadata['model']}")
    print(f"  Total papers: {metadata['total_papers']}")
    print(f"  Successful: {metadata['successful']}")
    print(f"  Failed: {metadata['failed']}")
    print(f"  With matches: {metadata['with_matches']}")
    print(f"  Without matches (null): {metadata['without_matches']}")
    print(f"  New theories: {metadata['new_theories']}")
    print(f"  Total tokens: {metadata['total_tokens']:,}")
    print(f"  Total cost: ${metadata['total_cost_usd']:.4f}")
    print(f"  Processing time: {metadata['processing_time_seconds']/60:.2f} minutes")
    
    # Theory distribution
    print("\n" + "-"*80)
    print("THEORY DISTRIBUTION (Top 20)")
    print("-"*80)
    
    theory_counts = Counter()
    theory_confidences = defaultdict(list)
    
    for r in results:
        if r['norm_theories']:
            for theory_match in r['norm_theories']:
                theory = theory_match['theory']
                confidence = theory_match['confidence']
                theory_counts[theory] += 1
                theory_confidences[theory].append(confidence)
    
    for theory, count in theory_counts.most_common(20):
        avg_conf = sum(theory_confidences[theory]) / len(theory_confidences[theory])
        print(f"{count:4d}  [{avg_conf:.1f}] {theory}")
    
    # NEW theories
    print("\n" + "-"*80)
    print("NEW THEORIES (not in seed ontology)")
    print("-"*80)
    
    new_theories = set()
    for r in results:
        if r['norm_theories']:
            for theory_match in r['norm_theories']:
                if theory_match['theory'].startswith('NEW_'):
                    new_theories.add(theory_match['theory'])
    
    if new_theories:
        for theory in sorted(new_theories):
            count = sum(
                1 for r in results 
                if r['norm_theories'] and any(t['theory'] == theory for t in r['norm_theories'])
            )
            print(f"{count:4d}  {theory}")
    else:
        print("  None")
    
    # Confidence distribution
    print("\n" + "-"*80)
    print("CONFIDENCE SCORE DISTRIBUTION")
    print("-"*80)
    
    all_confidences = []
    for r in results:
        if r['norm_theories']:
            for theory_match in r['norm_theories']:
                all_confidences.append(theory_match['confidence'])
    
    if all_confidences:
        conf_dist = Counter(all_confidences)
        for score in sorted(conf_dist.keys(), reverse=True):
            count = conf_dist[score]
            bar = "█" * (count // 2)
            print(f"  {score:2d}: {count:4d} {bar}")
        
        print(f"\n  Average confidence: {sum(all_confidences)/len(all_confidences):.2f}")
        print(f"  Min confidence: {min(all_confidences)}")
        print(f"  Max confidence: {max(all_confidences)}")
    
    print("\n" + "="*80 + "\n")


def search_by_theory(theory_name: str):
    """Search papers by normalized theory."""
    data = load_results()
    results = data['results']
    
    matches = []
    for r in results:
        if r['norm_theories']:
            for theory_match in r['norm_theories']:
                if theory_name.lower() in theory_match['theory'].lower():
                    matches.append({
                        'doi': r['doi'],
                        'initial_theory': r['initial_theory'],
                        'theory': theory_match['theory'],
                        'confidence': theory_match['confidence'],
                        'reasoning': r['mapping_reasoning']
                    })
    
    print(f"\n--- Papers with theory matching '{theory_name}' ({len(matches)}) ---\n")
    
    for m in matches:
        print(f"DOI: {m['doi']}")
        print(f"  Initial: {m['initial_theory']}")
        print(f"  Normalized: {m['theory']} (confidence: {m['confidence']})")
        print(f"  Reasoning: {m['reasoning']}")
        print("-" * 80)


def show_failed():
    """Show failed normalizations."""
    data = load_results()
    results = data['results']
    
    failed = [r for r in results if not r['success']]
    
    print(f"\n--- Failed Normalizations ({len(failed)}) ---\n")
    
    for r in failed:
        print(f"DOI: {r['doi']}")
        print(f"  Initial theory: {r['initial_theory']}")
        print(f"  Error: {r['error_message']}")
        print("-" * 80)


def show_no_matches():
    """Show papers with no theory matches (null)."""
    data = load_results()
    results = data['results']
    
    no_matches = [r for r in results if r['success'] and r['norm_theories'] is None]
    
    print(f"\n--- Papers with No Matches ({len(no_matches)}) ---\n")
    
    for r in no_matches:
        print(f"DOI: {r['doi']}")
        print(f"  Initial theory: {r['initial_theory']}")
        print(f"  Reasoning: {r['mapping_reasoning']}")
        print("-" * 80)


def export_mapping_csv(output_file: str):
    """Export DOI -> theory mappings to CSV."""
    import csv
    
    data = load_results()
    results = data['results']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['doi', 'initial_theory', 'normalized_theory', 'confidence', 'reasoning'])
        
        for r in results:
            if r['norm_theories']:
                for theory_match in r['norm_theories']:
                    writer.writerow([
                        r['doi'],
                        r['initial_theory'],
                        theory_match['theory'],
                        theory_match['confidence'],
                        r['mapping_reasoning']
                    ])
            else:
                writer.writerow([
                    r['doi'],
                    r['initial_theory'],
                    'NULL',
                    '',
                    r['mapping_reasoning']
                ])
    
    print(f"Exported to {output_file}")


def show_multi_theory_papers():
    """Show papers mapped to multiple theories."""
    data = load_results()
    results = data['results']
    
    multi = [r for r in results if r['norm_theories'] and len(r['norm_theories']) > 1]
    
    print(f"\n--- Papers Mapped to Multiple Theories ({len(multi)}) ---\n")
    
    for r in multi:
        print(f"DOI: {r['doi']}")
        print(f"  Initial: {r['initial_theory']}")
        print(f"  Normalized to {len(r['norm_theories'])} theories:")
        for tm in r['norm_theories']:
            print(f"    - {tm['theory']} (confidence: {tm['confidence']})")
        print(f"  Reasoning: {r['mapping_reasoning']}")
        print("-" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View normalized theory results")
    parser.add_argument("--summary", action="store_true", help="Show summary statistics")
    parser.add_argument("--theory", type=str, help="Search by theory name")
    parser.add_argument("--failed", action="store_true", help="Show failed normalizations")
    parser.add_argument("--no-matches", action="store_true", help="Show papers with no matches")
    parser.add_argument("--multi", action="store_true", help="Show papers with multiple theories")
    parser.add_argument("--export-csv", type=str, metavar="FILE", help="Export to CSV")
    
    args = parser.parse_args()
    
    if args.summary:
        print_summary()
    elif args.theory:
        search_by_theory(args.theory)
    elif args.failed:
        show_failed()
    elif args.no_matches:
        show_no_matches()
    elif args.multi:
        show_multi_theory_papers()
    elif args.export_csv:
        export_mapping_csv(args.export_csv)
    else:
        # Default: show summary
        print_summary()
