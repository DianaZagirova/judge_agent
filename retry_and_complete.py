#!/usr/bin/env python3
"""
Retry failed evaluations and process remaining unprocessed papers.
This script will NOT override existing successful evaluations.
"""
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.process_papers import process_papers_parallel

# Database paths
RESULTS_DB_PATH = "/home/diana.z/hack/llm_judge/data/evaluations.db"

def get_failed_papers_count():
    """Get count of failed evaluations."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM paper_evaluations WHERE success = 0")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def delete_failed_evaluations():
    """
    Delete failed evaluations so they can be retried.
    Only deletes entries where success = 0.
    """
    conn = sqlite3.connect(RESULTS_DB_PATH)
    cursor = conn.cursor()
    
    # Get failed papers info
    cursor.execute("SELECT doi, error_message FROM paper_evaluations WHERE success = 0")
    failed_papers = cursor.fetchall()
    
    if not failed_papers:
        print("No failed evaluations found.")
        conn.close()
        return 0
    
    print(f"\nFound {len(failed_papers)} failed evaluations:")
    for doi, error in failed_papers:
        print(f"  - {doi}: {error[:100] if error else 'No error message'}...")
    
    # Ask for confirmation
    response = input(f"\nDelete these {len(failed_papers)} failed evaluations to retry them? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted. No changes made.")
        conn.close()
        return 0
    
    # Delete failed evaluations
    cursor.execute("DELETE FROM paper_evaluations WHERE success = 0")
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✓ Deleted {deleted_count} failed evaluations. They will be retried in the next run.")
    return deleted_count

def main():
    """Main function to retry failed and process remaining papers."""
    print("=" * 80)
    print("RETRY FAILED & COMPLETE REMAINING EVALUATIONS")
    print("=" * 80)
    print()
    print("This script will:")
    print("  1. Delete failed evaluations (so they can be retried)")
    print("  2. Process all unprocessed papers (including retried failures)")
    print("  3. NOT override existing successful evaluations")
    print()
    print("=" * 80)
    
    # Check for failed papers
    failed_count = get_failed_papers_count()
    
    if failed_count > 0:
        print(f"\n⚠ Found {failed_count} failed evaluations")
        deleted = delete_failed_evaluations()
        if deleted == 0:
            print("\nNo failed evaluations were deleted. Continuing with unprocessed papers only...")
    else:
        print("\n✓ No failed evaluations found")
    
    print("\n" + "=" * 80)
    print("STARTING EVALUATION RUN")
    print("=" * 80)
    print()
    print("The script will now:")
    print("  - Find all unprocessed papers (including any deleted failures)")
    print("  - Process them using parallel workers")
    print("  - Save results to the existing database")
    print("  - Skip any papers that already have successful evaluations")
    print()
    
    response = input("Continue with evaluation? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    print("\n" + "=" * 80)
    print("RUNNING EVALUATION...")
    print("=" * 80)
    print()
    
    # Run the evaluation
    # This will automatically:
    # - Skip already processed papers
    # - Process unprocessed papers
    # - Use INSERT OR REPLACE to update any existing entries
    process_papers_parallel(limit=None, max_workers=10)
    
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
