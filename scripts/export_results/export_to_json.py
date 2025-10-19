#!/usr/bin/env python3
"""
Export evaluation results from SQLite database to JSON format.
"""
import sqlite3
import json
import argparse
from pathlib import Path

RESULTS_DB_PATH = "/home/diana.z/hack/llm_judge/data/evaluations.db"


def export_evaluations_to_json(output_file: str, pretty: bool = True):
    """Export all paper evaluations to JSON file."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT doi, pmid, title, result, aging_theory, type, reasoning,
               confidence_score, prompt_tokens, completion_tokens, total_tokens,
               cost_usd, processing_time_seconds, success, error_message, 
               timestamp, model_used
        FROM paper_evaluations
        ORDER BY timestamp DESC
    """)
    
    rows = cursor.fetchall()
    
    # Convert to list of dictionaries
    data = [dict(row) for row in rows]
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)
    
    conn.close()
    print(f"✓ Exported {len(data)} evaluations to {output_file}")
    return data


def export_successful_only(output_file: str):
    """Export only successful evaluations to JSON."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT doi, pmid, title, result, aging_theory, type, reasoning,
               confidence_score, total_tokens, cost_usd, timestamp
        FROM paper_evaluations
        WHERE success = 1
        ORDER BY timestamp DESC
    """)
    
    rows = cursor.fetchall()
    data = [dict(row) for row in rows]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    conn.close()
    print(f"✓ Exported {len(data)} successful evaluations to {output_file}")
    return data


def export_by_result(result_type: str, output_file: str):
    """Export evaluations filtered by result type (e.g., 'relevant', 'not_relevant')."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT doi, pmid, title, result, aging_theory, type, reasoning,
               confidence_score, timestamp
        FROM paper_evaluations
        WHERE success = 1 AND result = ?
        ORDER BY confidence_score DESC, timestamp DESC
    """, (result_type,))
    
    rows = cursor.fetchall()
    data = [dict(row) for row in rows]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    conn.close()
    print(f"✓ Exported {len(data)} '{result_type}' evaluations to {output_file}")
    return data


def export_processing_runs(output_file: str):
    """Export processing run statistics to JSON."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, start_time, end_time, total_papers, successful, failed,
               total_tokens, total_cost_usd, total_processing_time_seconds,
               max_workers, status
        FROM processing_runs
        ORDER BY id DESC
    """)
    
    rows = cursor.fetchall()
    data = [dict(row) for row in rows]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    conn.close()
    print(f"✓ Exported {len(data)} processing runs to {output_file}")
    return data


def load_json_to_memory(json_file: str = None):
    """Load JSON file into memory and return as Python object."""
    if not json_file:
        # Query directly from database
        conn = sqlite3.connect(RESULTS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM paper_evaluations")
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        conn.close()
        
        return data
    else:
        # Load from JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export evaluation results to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all evaluations
  python export_to_json.py -o all_results.json
  
  # Export only successful evaluations
  python export_to_json.py --successful -o successful.json
  
  # Export only relevant papers
  python export_to_json.py --result relevant -o relevant_papers.json
  
  # Export processing runs
  python export_to_json.py --runs -o processing_runs.json
        """
    )
    
    parser.add_argument("-o", "--output", type=str, required=True,
                        help="Output JSON file path")
    parser.add_argument("--successful", action="store_true",
                        help="Export only successful evaluations")
    parser.add_argument("--result", type=str,
                        help="Filter by result type (e.g., 'relevant', 'not_relevant')")
    parser.add_argument("--runs", action="store_true",
                        help="Export processing runs instead of evaluations")
    parser.add_argument("--compact", action="store_true",
                        help="Compact JSON output (no indentation)")
    
    args = parser.parse_args()
    
    # Execute appropriate export
    if args.runs:
        export_processing_runs(args.output)
    elif args.successful:
        export_successful_only(args.output)
    elif args.result:
        export_by_result(args.result, args.output)
    else:
        export_evaluations_to_json(args.output, pretty=not args.compact)
