"""
Utility script to view and analyze evaluation results.
"""
import sqlite3
import argparse
from datetime import datetime
import json

RESULTS_DB_PATH = "/home/diana.z/hack/llm_judge/data/evaluations.db"


def print_statistics():
    """Print overall statistics from evaluations."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("EVALUATION STATISTICS")
    print("="*80)
    
    # Overall counts
    cursor.execute("SELECT COUNT(*) FROM paper_evaluations")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM paper_evaluations WHERE success = 1")
    successful = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM paper_evaluations WHERE success = 0")
    failed = cursor.fetchone()[0]
    
    print(f"\nTotal Evaluations: {total}")
    print(f"Successful: {successful} ({successful/total*100:.1f}%)" if total > 0 else "Successful: 0")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)" if total > 0 else "Failed: 0")
    
    # Result distribution
    print("\n--- Result Distribution ---")
    cursor.execute("""
        SELECT result, COUNT(*) as count 
        FROM paper_evaluations 
        WHERE success = 1 
        GROUP BY result
    """)
    for row in cursor.fetchall():
        result_type, count = row
        print(f"{result_type}: {count} ({count/successful*100:.1f}%)" if successful > 0 else f"{result_type}: {count}")
    
    # Type distribution
    print("\n--- Paper Type Distribution ---")
    cursor.execute("""
        SELECT type, COUNT(*) as count 
        FROM paper_evaluations 
        WHERE success = 1 
        GROUP BY type
    """)
    for row in cursor.fetchall():
        paper_type, count = row
        print(f"{paper_type}: {count}")
    
    # Token and cost statistics
    print("\n--- Token & Cost Statistics ---")
    cursor.execute("""
        SELECT 
            SUM(total_tokens) as total_tokens,
            SUM(prompt_tokens) as prompt_tokens,
            SUM(completion_tokens) as completion_tokens,
            SUM(cost_usd) as total_cost,
            AVG(total_tokens) as avg_tokens,
            AVG(cost_usd) as avg_cost
        FROM paper_evaluations
        WHERE success = 1
    """)
    row = cursor.fetchone()
    if row and row[0]:
        print(f"Total Tokens: {row[0]:,}")
        print(f"  - Prompt: {row[1]:,}")
        print(f"  - Completion: {row[2]:,}")
        print(f"Total Cost: ${row[3]:.4f}")
        print(f"Average Tokens per Paper: {row[4]:.0f}")
        print(f"Average Cost per Paper: ${row[5]:.6f}")
    
    # Processing time statistics
    print("\n--- Processing Time Statistics ---")
    cursor.execute("""
        SELECT 
            SUM(processing_time_seconds) as total_time,
            AVG(processing_time_seconds) as avg_time,
            MIN(processing_time_seconds) as min_time,
            MAX(processing_time_seconds) as max_time
        FROM paper_evaluations
        WHERE success = 1
    """)
    row = cursor.fetchone()
    if row and row[0]:
        print(f"Total Processing Time: {row[0]/60:.2f} minutes")
        print(f"Average Time per Paper: {row[1]:.2f} seconds")
        print(f"Min Time: {row[2]:.2f} seconds")
        print(f"Max Time: {row[3]:.2f} seconds")
    
    # Confidence score distribution
    print("\n--- Confidence Score Distribution ---")
    cursor.execute("""
        SELECT confidence_score, COUNT(*) as count
        FROM paper_evaluations
        WHERE success = 1 AND confidence_score IS NOT NULL
        GROUP BY confidence_score
        ORDER BY confidence_score DESC
    """)
    for row in cursor.fetchall():
        score, count = row
        print(f"Score {score}: {count}")
    
    # Top aging theories
    print("\n--- Top Aging Theories (Top 10) ---")
    cursor.execute("""
        SELECT aging_theory, COUNT(*) as count
        FROM paper_evaluations
        WHERE success = 1 AND aging_theory IS NOT NULL
        GROUP BY aging_theory
        ORDER BY count DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        theory, count = row
        print(f"{theory}: {count}")
    
    # Processing runs
    print("\n--- Processing Runs ---")
    cursor.execute("""
        SELECT 
            id, start_time, end_time, total_papers, successful, failed,
            total_tokens, total_cost_usd, status
        FROM processing_runs
        ORDER BY id DESC
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        run_id, start, end, total, succ, fail, tokens, cost, status = row
        print(f"\nRun #{run_id} [{status}]")
        print(f"  Time: {start} to {end}")
        print(f"  Papers: {total} (Success: {succ}, Failed: {fail})")
        if tokens:
            print(f"  Tokens: {tokens:,}, Cost: ${cost:.4f}")
    
    conn.close()
    print("\n" + "="*80 + "\n")


def view_recent_evaluations(limit: int = 10):
    """View recent evaluations."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT doi, title, result, aging_theory, type, confidence_score, 
               total_tokens, cost_usd, success, error_message, timestamp
        FROM paper_evaluations
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    
    print(f"\n--- Recent {limit} Evaluations ---\n")
    
    for row in cursor.fetchall():
        print(f"DOI: {row['doi']}")
        print(f"Title: {row['title'][:80]}...")
        print(f"Result: {row['result']}")
        print(f"Theory: {row['aging_theory']}")
        print(f"Type: {row['type']}")
        print(f"Confidence: {row['confidence_score']}")
        print(f"Tokens: {row['total_tokens']}, Cost: ${row['cost_usd']:.6f}")
        print(f"Success: {bool(row['success'])}")
        if row['error_message']:
            print(f"Error: {row['error_message']}")
        print(f"Timestamp: {row['timestamp']}")
        print("-" * 80)
    
    conn.close()


def view_failed_evaluations():
    """View failed evaluations."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT doi, title, error_message, timestamp
        FROM paper_evaluations
        WHERE success = 0
        ORDER BY timestamp DESC
    """)
    
    rows = cursor.fetchall()
    
    print(f"\n--- Failed Evaluations ({len(rows)}) ---\n")
    
    for row in rows:
        print(f"DOI: {row['doi']}")
        print(f"Title: {row['title'][:80]}...")
        print(f"Error: {row['error_message']}")
        print(f"Timestamp: {row['timestamp']}")
        print("-" * 80)
    
    conn.close()


def export_to_csv(output_file: str):
    """Export results to CSV file."""
    import csv
    
    conn = sqlite3.connect(RESULTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT doi, pmid, title, result, aging_theory, type, reasoning,
               confidence_score, prompt_tokens, completion_tokens, total_tokens,
               cost_usd, processing_time_seconds, success, error_message, timestamp
        FROM paper_evaluations
        ORDER BY timestamp DESC
    """)
    
    rows = cursor.fetchall()
    
    if not rows:
        print("No data to export!")
        return
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    
    print(f"Exported {len(rows)} records to {output_file}")
    conn.close()


def search_by_theory(theory_name: str):
    """Search evaluations by aging theory."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT doi, title, result, aging_theory, confidence_score
        FROM paper_evaluations
        WHERE aging_theory LIKE ? AND success = 1
        ORDER BY confidence_score DESC
    """, (f"%{theory_name}%",))
    
    rows = cursor.fetchall()
    
    print(f"\n--- Papers with theory matching '{theory_name}' ({len(rows)}) ---\n")
    
    for row in rows:
        print(f"DOI: {row['doi']}")
        print(f"Title: {row['title'][:80]}...")
        print(f"Theory: {row['aging_theory']}")
        print(f"Result: {row['result']}, Confidence: {row['confidence_score']}")
        print("-" * 80)
    
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View evaluation results")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--recent", type=int, metavar="N", help="Show N recent evaluations")
    parser.add_argument("--failed", action="store_true", help="Show failed evaluations")
    parser.add_argument("--export", type=str, metavar="FILE", help="Export to CSV file")
    parser.add_argument("--theory", type=str, help="Search by theory name")
    
    args = parser.parse_args()
    
    if args.stats:
        print_statistics()
    elif args.recent:
        view_recent_evaluations(args.recent)
    elif args.failed:
        view_failed_evaluations()
    elif args.export:
        export_to_csv(args.export)
    elif args.theory:
        search_by_theory(args.theory)
    else:
        # Default: show stats
        print_statistics()
