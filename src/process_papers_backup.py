"""
Process papers from the database using LLM judge with parallel processing.
Tracks tokens, cost, time, results, and errors for each paper.
"""
import sqlite3
import time
import json
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Optional, Tuple
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_judge import llm_judge

# Database paths
PAPERS_DB_PATH = "/home/diana.z/hack/download_papers_pubmed/paper_collection/data/papers.db"
RESULTS_DB_PATH = "/home/diana.z/hack/llm_judge/data/evaluations.db"

# Pricing for gpt-4.1-nano (adjust if needed)
# These are placeholder values - update with actual pricing
COST_PER_1K_PROMPT_TOKENS = 0.0001  # $0.0001 per 1K prompt tokens
COST_PER_1K_COMPLETION_TOKENS = 0.0002  # $0.0002 per 1K completion tokens

# Parallel processing config
MAX_WORKERS = 10  # Adjust based on your system and API rate limits


def init_results_database():
    """Initialize the results database with necessary tables."""
    os.makedirs(os.path.dirname(RESULTS_DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(RESULTS_DB_PATH)
    cursor = conn.cursor()
    
    # Table for evaluation results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_evaluations (
            doi TEXT PRIMARY KEY,
            pmid TEXT,
            title TEXT,
            result TEXT,
            aging_theory TEXT,
            type TEXT,
            reasoning TEXT,
            confidence_score INTEGER,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            cost_usd REAL,
            processing_time_seconds REAL,
            success INTEGER,
            error_message TEXT,
            timestamp TEXT,
            model_used TEXT
        )
    """)
    
    # Table for processing runs/batches
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            end_time TEXT,
            total_papers INTEGER,
            successful INTEGER,
            failed INTEGER,
            total_tokens INTEGER,
            total_cost_usd REAL,
            total_processing_time_seconds REAL,
            max_workers INTEGER,
            status TEXT
        )
    """)
    
    # Create index for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_evaluations_doi ON paper_evaluations(doi)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_evaluations_success ON paper_evaluations(success)
    """)
    
    conn.commit()
    conn.close()
    print(f"Results database initialized at: {RESULTS_DB_PATH}")


def calculate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost in USD based on token usage."""
    prompt_cost = (prompt_tokens / 1000) * COST_PER_1K_PROMPT_TOKENS
    completion_cost = (completion_tokens / 1000) * COST_PER_1K_COMPLETION_TOKENS
    return prompt_cost + completion_cost


def get_unprocessed_papers(limit: Optional[int] = None) -> list:
    """
    Get papers that haven't been evaluated yet.
    Returns list of (doi, pmid, title, abstract) tuples.
    """
    papers_conn = sqlite3.connect(PAPERS_DB_PATH)
    papers_conn.row_factory = sqlite3.Row
    papers_cursor = papers_conn.cursor()
    
    results_conn = sqlite3.connect(RESULTS_DB_PATH)
    results_cursor = results_conn.cursor()
    
    # Get already processed DOIs
    results_cursor.execute("SELECT doi FROM paper_evaluations")
    processed_dois = {row[0] for row in results_cursor.fetchall()}
    
    # Get papers with title and abstract that haven't been processed
    query = """
        SELECT doi, pmid, title, abstract 
        FROM papers 
        WHERE doi IS NOT NULL 
        AND title IS NOT NULL 
        AND abstract IS NOT NULL
        AND abstract != ''
    """
    if limit:
        query += f" LIMIT {limit * 2}"  # Get extra in case some are already processed
    
    papers_cursor.execute(query)
    all_papers = papers_cursor.fetchall()
    
    # Filter out already processed papers
    unprocessed = [
        (row['doi'], row['pmid'], row['title'], row['abstract']) 
        for row in all_papers 
        if row['doi'] not in processed_dois
    ]
    
    if limit:
        unprocessed = unprocessed[:limit]
    
    papers_conn.close()
    results_conn.close()
    
    return unprocessed


def process_single_paper(paper_data: Tuple[str, str, str, str]) -> Dict:
    """
    Process a single paper with LLM judge.
    Returns dict with results and metadata.
    """
    doi, pmid, title, abstract = paper_data
    
    start_time = time.time()
    result = {
        'doi': doi,
        'pmid': pmid,
        'title': title,
        'success': 0,
        'error_message': None,
        'processing_time_seconds': 0,
        'result': None,
        'aging_theory': None,
        'type': None,
        'reasoning': None,
        'confidence_score': None,
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'total_tokens': 0,
        'cost_usd': 0.0
    }
    
    try:
        # Create joint text
        jointtext = f"{title}: {abstract}"
        
        # Call LLM judge
        llm_result = llm_judge(jointtext)
        
        # Extract evaluation results
        result['result'] = llm_result.get('result')
        result['aging_theory'] = llm_result.get('aging_theory')
        result['type'] = llm_result.get('type')
        result['reasoning'] = llm_result.get('reasoning')
        result['confidence_score'] = llm_result.get('confidence_score')
        
        # Extract token usage
        if '_tokens' in llm_result:
            tokens = llm_result['_tokens']
            result['prompt_tokens'] = tokens.get('prompt_tokens', 0)
            result['completion_tokens'] = tokens.get('completion_tokens', 0)
            result['total_tokens'] = tokens.get('total_tokens', 0)
            result['cost_usd'] = calculate_cost(result['prompt_tokens'], result['completion_tokens'])
        
        result['success'] = 1
        
    except Exception as e:
        result['error_message'] = str(e)
        result['success'] = 0
        print(f"Error processing DOI {doi}: {e}")
    
    finally:
        result['processing_time_seconds'] = time.time() - start_time
    
    return result


def save_result(result: Dict):
    """Save a single result to the database."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO paper_evaluations (
            doi, pmid, title, result, aging_theory, type, reasoning, 
            confidence_score, prompt_tokens, completion_tokens, total_tokens,
            cost_usd, processing_time_seconds, success, error_message,
            timestamp, model_used
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result['doi'],
        result['pmid'],
        result['title'],
        result['result'],
        result['aging_theory'],
        result['type'],
        result['reasoning'],
        result['confidence_score'],
        result['prompt_tokens'],
        result['completion_tokens'],
        result['total_tokens'],
        result['cost_usd'],
        result['processing_time_seconds'],
        result['success'],
        result['error_message'],
        datetime.now().isoformat(),
        'gpt-4.1-nano'
    ))
    
    conn.commit()
    conn.close()


def create_processing_run() -> int:
    """Create a new processing run record and return its ID."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO processing_runs (
            start_time, max_workers, status
        ) VALUES (?, ?, ?)
    """, (datetime.now().isoformat(), MAX_WORKERS, 'running'))
    
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return run_id


def update_processing_run(run_id: int, stats: Dict):
    """Update processing run with final statistics."""
    conn = sqlite3.connect(RESULTS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE processing_runs
        SET end_time = ?,
            total_papers = ?,
            successful = ?,
            failed = ?,
            total_tokens = ?,
            total_cost_usd = ?,
            total_processing_time_seconds = ?,
            status = ?
        WHERE id = ?
    """, (
        datetime.now().isoformat(),
        stats['total_papers'],
        stats['successful'],
        stats['failed'],
        stats['total_tokens'],
        stats['total_cost_usd'],
        stats['total_processing_time_seconds'],
        'completed',
        run_id
    ))
    
    conn.commit()
    conn.close()


def process_papers_parallel(limit: Optional[int] = None, max_workers: int = MAX_WORKERS):
    """
    Process papers in parallel using ProcessPoolExecutor.
    
    Args:
        limit: Maximum number of papers to process (None for all)
        max_workers: Number of parallel workers
    """
    print("Initializing results database...")
    init_results_database()
    
    print("Fetching unprocessed papers...")
    papers = get_unprocessed_papers(limit=limit)
    
    if not papers:
        print("No unprocessed papers found!")
        return
    
    print(f"Found {len(papers)} unprocessed papers")
    print(f"Starting parallel processing with {max_workers} workers...")
    
    run_id = create_processing_run()
    
    # Statistics
    stats = {
        'total_papers': len(papers),
        'successful': 0,
        'failed': 0,
        'total_tokens': 0,
        'total_cost_usd': 0.0,
        'total_processing_time_seconds': 0.0
    }
    
    overall_start = time.time()
    
    # Process in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_paper = {
            executor.submit(process_single_paper, paper): paper 
            for paper in papers
        }
        
        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_paper), 1):
            try:
                result = future.result()
                
                # Save result
                save_result(result)
                
                # Update statistics
                if result['success']:
                    stats['successful'] += 1
                else:
                    stats['failed'] += 1
                
                stats['total_tokens'] += result['total_tokens']
                stats['total_cost_usd'] += result['cost_usd']
                stats['total_processing_time_seconds'] += result['processing_time_seconds']
                
                # Progress update
                if i % 10 == 0 or i == len(papers):
                    elapsed = time.time() - overall_start
                    papers_per_sec = i / elapsed if elapsed > 0 else 0
                    eta_seconds = (len(papers) - i) / papers_per_sec if papers_per_sec > 0 else 0
                    
                    print(f"Progress: {i}/{len(papers)} | "
                          f"Success: {stats['successful']} | "
                          f"Failed: {stats['failed']} | "
                          f"Tokens: {stats['total_tokens']} | "
                          f"Cost: ${stats['total_cost_usd']:.4f} | "
                          f"Speed: {papers_per_sec:.2f} papers/sec | "
                          f"ETA: {eta_seconds/60:.1f} min")
                
            except Exception as e:
                print(f"Error processing future: {e}")
                stats['failed'] += 1
    
    # Final statistics
    total_time = time.time() - overall_start
    stats['total_processing_time_seconds'] = total_time
    
    update_processing_run(run_id, stats)
    
    print("\n" + "="*80)
    print("PROCESSING COMPLETE")
    print("="*80)
    print(f"Total papers: {stats['total_papers']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total tokens: {stats['total_tokens']}")
    print(f"Total cost: ${stats['total_cost_usd']:.4f}")
    print(f"Total time: {total_time/60:.2f} minutes")
    print(f"Average time per paper: {total_time/len(papers):.2f} seconds")
    print(f"Results saved to: {RESULTS_DB_PATH}")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process papers with LLM judge")
    parser.add_argument("--limit", type=int, default=None, 
                        help="Limit number of papers to process (default: all)")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS,
                        help=f"Number of parallel workers (default: {MAX_WORKERS})")
    parser.add_argument("--test", action="store_true",
                        help="Test mode - process only 5 papers")
    
    args = parser.parse_args()
    
    if args.test:
        print("TEST MODE: Processing 5 papers only")
        process_papers_parallel(limit=5, max_workers=2)
    else:
        process_papers_parallel(limit=args.limit, max_workers=args.workers)
