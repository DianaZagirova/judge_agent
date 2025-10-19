#!/usr/bin/env python3
"""
Calculate how many papers have "valid" or "doubted" or ("not_valid" with confidence_score <= 7)
"""
import sqlite3
from pathlib import Path

# Database path
RESULTS_DB_PATH = "/home/diana.z/hack/llm_judge/data/evaluations.db"

def calculate_paper_stats():
    """Calculate statistics for evaluated papers."""
    
    # Check if database exists
    if not Path(RESULTS_DB_PATH).exists():
        print(f"ERROR: Database not found at {RESULTS_DB_PATH}")
        return
    
    conn = sqlite3.connect(RESULTS_DB_PATH)
    cursor = conn.cursor()
    
    # Get total count of all evaluated papers
    cursor.execute("SELECT COUNT(*) FROM paper_evaluations WHERE success = 1")
    total_papers = cursor.fetchone()[0]
    
    # Get count of papers matching criteria:
    # 1. result = "valid" OR
    # 2. result = "doubted" OR
    # 3. result = "not_valid" AND confidence_score <= 7
    query = """
        SELECT COUNT(*) 
        FROM paper_evaluations 
        WHERE success = 1 
        AND (
            result = 'valid' 
            OR result = 'doubted' 
            OR (result = 'not_valid' AND confidence_score <= 7)
        )
    """
    cursor.execute(query)
    matching_papers = cursor.fetchone()[0]
    
    # Get breakdown by category
    cursor.execute("SELECT COUNT(*) FROM paper_evaluations WHERE success = 1 AND result = 'valid'")
    valid_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM paper_evaluations WHERE success = 1 AND result = 'doubted'")
    doubted_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM paper_evaluations WHERE success = 1 AND result = 'not_valid' AND confidence_score <= 7")
    not_valid_low_confidence_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM paper_evaluations WHERE success = 1 AND result = 'not_valid' AND confidence_score > 7")
    not_valid_high_confidence_count = cursor.fetchone()[0]
    
    conn.close()
    
    # Print results
    print("=" * 80)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 80)
    print(f"\nTotal successfully evaluated papers: {total_papers:,}")
    print(f"\nPapers matching criteria (valid OR doubted OR not_valid with confidence ≤7): {matching_papers:,}")
    print(f"Percentage: {100 * matching_papers / total_papers:.2f}%")
    
    print(f"\n{'─' * 80}")
    print("BREAKDOWN BY CATEGORY:")
    print(f"{'─' * 80}")
    print(f"  Valid papers:                           {valid_count:,} ({100 * valid_count / total_papers:.2f}%)")
    print(f"  Doubted papers:                         {doubted_count:,} ({100 * doubted_count / total_papers:.2f}%)")
    print(f"  Not valid (confidence ≤7):              {not_valid_low_confidence_count:,} ({100 * not_valid_low_confidence_count / total_papers:.2f}%)")
    print(f"  Not valid (confidence >7):              {not_valid_high_confidence_count:,} ({100 * not_valid_high_confidence_count / total_papers:.2f}%)")
    
    print(f"\n{'─' * 80}")
    print(f"Papers NOT matching criteria (excluded): {total_papers - matching_papers:,} ({100 * (total_papers - matching_papers) / total_papers:.2f}%)")
    print(f"  (These are 'not_valid' with confidence >7)")
    print("=" * 80)

if __name__ == "__main__":
    calculate_paper_stats()
