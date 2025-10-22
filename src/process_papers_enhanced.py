"""
Process papers from the database using LLM judge with parallel processing.
Enhanced version with robust logging, checkpointing, and error handling for large-scale runs.
"""
import os
import sqlite3
import time
import json
import logging
import signal
import sys
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_judge import llm_judge

# ============================================================================
# CONFIGURATION - Load from environment variables with defaults
# ============================================================================

# Base directory and paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = Path(os.getenv('LOG_DIR', BASE_DIR / 'logs'))

# Database paths
PAPERS_DB_PATH = Path(os.getenv('PAPERS_DB_PATH', DATA_DIR / 'papers.db'))
RESULTS_DB_PATH = Path(os.getenv('RESULTS_DB_PATH', DATA_DIR / 'evaluations.db'))
LOG_FILE = LOG_DIR / 'processing.log'

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Pricing for Azure OpenAI (update with actual pricing)
COST_PER_1K_PROMPT_TOKENS = float(os.getenv('COST_PER_1K_PROMPT_TOKENS', '0.0004'))
COST_PER_1K_COMPLETION_TOKENS = float(os.getenv('COST_PER_1K_COMPLETION_TOKENS', '0.0016'))

# Processing config
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))
CHECKPOINT_INTERVAL = int(os.getenv('CHECKPOINT_INTERVAL', '50'))  # Save progress summary every N papers
PROGRESS_LOG_INTERVAL = int(os.getenv('PROGRESS_LOG_INTERVAL', '10'))  # Log progress every N papers

# Global flag for graceful shutdown
shutdown_requested = False

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Configure logging with both file and console output."""
    # Ensure log directory exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('paper_processor')
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers = []
    
    # File handler - detailed logs
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler - important info only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log configuration at startup
    logger.info(f"Starting paper processor with configuration:")
    logger.info(f"  Papers DB: {PAPERS_DB_PATH.absolute()}")
    logger.info(f"  Results DB: {RESULTS_DB_PATH.absolute()}")
    logger.info(f"  Log file: {LOG_FILE.absolute()}")
    logger.info(f"  Max workers: {MAX_WORKERS}")
    
    return logger

logger = setup_logging()

# ============================================================================
# SIGNAL HANDLERS FOR GRACEFUL SHUTDOWN
# ============================================================================

def signal_handler(signum, frame):
    """Handle interrupt signals for graceful shutdown."""
    global shutdown_requested
    logger.warning(f"Received signal {signum}. Initiating graceful shutdown...")
    logger.warning("Current tasks will complete, then the process will stop.")
    logger.warning("Press Ctrl+C again to force quit (not recommended).")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def validate_runtime() -> Tuple[bool, list]:
    """Validate required environment, files, and configuration."""
    errors = []
    try:
        if not PAPERS_DB_PATH.exists():
            errors.append(f"PAPERS_DB_PATH not found: {PAPERS_DB_PATH}")
        else:
            conn = sqlite3.connect(PAPERS_DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='papers'")
            if cur.fetchone() is None:
                errors.append("'papers' table not found in PAPERS_DB_PATH")
            else:
                cur.execute("PRAGMA table_info(papers)")
                cols = {r[1] for r in cur.fetchall()}
                required = {"doi", "pmid", "title", "abstract"}
                missing = required - cols
                if missing:
                    errors.append(f"'papers' table missing columns: {', '.join(sorted(missing))}")
            conn.close()
    except Exception as e:
        errors.append(f"Failed to inspect PAPERS_DB_PATH: {e}")

    use_module = os.getenv("USE_MODULE", "openai").lower()
    if use_module == "azure":
        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            errors.append("AZURE_OPENAI_ENDPOINT is not set")
        if not os.getenv("AZURE_OPENAI_API_KEY"):
            errors.append("AZURE_OPENAI_API_KEY is not set")
        if not os.getenv("AZURE_OPENAI_API_VERSION"):
            errors.append("AZURE_OPENAI_API_VERSION is not set")
    else:
        if not os.getenv("OPENAI_API_KEY"):
            errors.append("OPENAI_API_KEY is not set")

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        errors.append(f"Failed to create output directories: {e}")

    return (len(errors) == 0, errors)

def init_results_database():
    """Initialize the results database with necessary tables."""
    try:
        db_dir = Path(RESULTS_DB_PATH).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
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
                status TEXT,
                checkpoint_data TEXT
            )
        """)
        
        # Create indices for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_evaluations_doi ON paper_evaluations(doi)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_evaluations_success ON paper_evaluations(success)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_evaluations_result ON paper_evaluations(result)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Results database initialized: {RESULTS_DB_PATH}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


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
    try:
        papers_conn = sqlite3.connect(PAPERS_DB_PATH, timeout=30.0)
        papers_conn.row_factory = sqlite3.Row
        papers_cursor = papers_conn.cursor()
        
        results_conn = sqlite3.connect(RESULTS_DB_PATH, timeout=30.0)
        results_cursor = results_conn.cursor()
        
        # Get already processed DOIs
        logger.info("Checking for already processed papers...")
        results_cursor.execute("SELECT doi FROM paper_evaluations")
        processed_dois = {row[0] for row in results_cursor.fetchall()}
        logger.info(f"Found {len(processed_dois)} already processed papers")
        
        # Get papers with title and abstract
        query = """
            SELECT doi, pmid, title, abstract 
            FROM papers 
            WHERE doi IS NOT NULL 
            AND title IS NOT NULL 
            AND abstract IS NOT NULL
            AND abstract != ''
        """
        
        if limit:
            query += f" LIMIT {limit * 3}"  # Get extra in case some are already processed
        
        papers_cursor.execute(query)
        all_papers = papers_cursor.fetchall()
        logger.info(f"Retrieved {len(all_papers)} papers from database")
        
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
        
        logger.info(f"Found {len(unprocessed)} unprocessed papers")
        return unprocessed
        
    except Exception as e:
        logger.error(f"Error getting unprocessed papers: {e}")
        raise


def process_single_paper(paper_data: Tuple[str, str, str, str]) -> Dict:
    """
    Process a single paper with LLM judge.
    Returns dict with results and metadata.
    Includes retry logic and detailed error handling.
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
        
        # Call LLM judge (has built-in retries)
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
        error_msg = str(e)
        result['error_message'] = error_msg
        result['success'] = 0
        logger.debug(f"Error processing DOI {doi}: {error_msg}")
    
    finally:
        result['processing_time_seconds'] = time.time() - start_time
    
    return result


def save_result(result: Dict, retries: int = 3):
    """Save a single result to the database with retry logic."""
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(RESULTS_DB_PATH, timeout=30.0)
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
                'gpt-4.1-mini'  # Azure OpenAI deployment name
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.OperationalError as e:
            if attempt < retries - 1:
                logger.warning(f"Database locked, retry {attempt + 1}/{retries}")
                time.sleep(0.5 * (attempt + 1))
            else:
                logger.error(f"Failed to save result after {retries} attempts: {e}")
                return False
        except Exception as e:
            logger.error(f"Error saving result: {e}")
            return False


def create_processing_run(max_workers: int) -> int:
    """Create a new processing run record and return its ID."""
    try:
        conn = sqlite3.connect(RESULTS_DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO processing_runs (
                start_time, max_workers, status
            ) VALUES (?, ?, ?)
        """, (datetime.now().isoformat(), max_workers, 'running'))
        
        run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Created processing run #{run_id}")
        return run_id
        
    except Exception as e:
        logger.error(f"Error creating processing run: {e}")
        return -1


def update_processing_run(run_id: int, stats: Dict, status: str = 'completed'):
    """Update processing run with statistics."""
    try:
        conn = sqlite3.connect(RESULTS_DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        
        checkpoint_data = json.dumps({
            'last_update': datetime.now().isoformat(),
            'stats': stats
        })
        
        cursor.execute("""
            UPDATE processing_runs
            SET end_time = ?,
                total_papers = ?,
                successful = ?,
                failed = ?,
                total_tokens = ?,
                total_cost_usd = ?,
                total_processing_time_seconds = ?,
                status = ?,
                checkpoint_data = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            stats['total_papers'],
            stats['successful'],
            stats['failed'],
            stats['total_tokens'],
            stats['total_cost_usd'],
            stats['total_processing_time_seconds'],
            status,
            checkpoint_data,
            run_id
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error updating processing run: {e}")
        return False


def save_checkpoint(run_id: int, stats: Dict, processed_count: int, total_count: int):
    """Save a checkpoint of current progress."""
    try:
        logger.info(f"=== CHECKPOINT [{processed_count}/{total_count}] ===")
        logger.info(f"Success: {stats['successful']} | Failed: {stats['failed']}")
        logger.info(f"Tokens: {stats['total_tokens']:,} | Cost: ${stats['total_cost_usd']:.4f}")
        
        update_processing_run(run_id, stats, status='running')
        
        # Also save to a JSON checkpoint file
        checkpoint_file = Path(RESULTS_DB_PATH).parent / f"checkpoint_run_{run_id}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump({
                'run_id': run_id,
                'processed': processed_count,
                'total': total_count,
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        logger.info(f"Checkpoint saved")
        
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")


# ============================================================================
# MAIN PROCESSING FUNCTION
# ============================================================================

def process_papers_parallel(limit: Optional[int] = None, max_workers: int = MAX_WORKERS):
    """
    Process papers in parallel using ProcessPoolExecutor.
    
    Args:
        limit: Maximum number of papers to process (None for all)
        max_workers: Number of parallel workers
    """
    global shutdown_requested
    
    logger.info("="*80)
    logger.info("PAPER PROCESSING - ENHANCED VERSION")
    logger.info("="*80)
    logger.info(f"Max workers: {max_workers}")
    logger.info(f"Limit: {limit if limit else 'ALL PAPERS'}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info(f"Results DB: {RESULTS_DB_PATH}")

    # Validate runtime environment before proceeding
    ok, errs = validate_runtime()
    if not ok:
        logger.error("Runtime validation failed. Please fix the following issues:")
        for e in errs:
            logger.error(f" - {e}")
        return
    
    # Initialize database
    if not init_results_database():
        logger.error("Failed to initialize database. Aborting.")
        return
    
    # Fetch papers
    logger.info("Fetching unprocessed papers...")
    try:
        papers = get_unprocessed_papers(limit=limit)
    except Exception as e:
        logger.error(f"Failed to fetch papers: {e}")
        return
    
    if not papers:
        logger.warning("No unprocessed papers found!")
        return
    
    logger.info(f"Starting processing of {len(papers)} papers...")
    logger.info("="*80)
    
    # Create processing run
    run_id = create_processing_run(max_workers)
    if run_id == -1:
        logger.error("Failed to create processing run. Aborting.")
        return
    
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
    processed_count = 0
    
    try:
        # Process in parallel
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_paper = {
                executor.submit(process_single_paper, paper): paper 
                for paper in papers
            }
            
            # Process results as they complete
            for future in as_completed(future_to_paper):
                # Check for shutdown signal
                if shutdown_requested:
                    logger.warning("Shutdown requested. Stopping submission of new tasks...")
                    executor.shutdown(wait=True, cancel_futures=True)
                    break
                
                try:
                    result = future.result(timeout=300)  # 5 minute timeout per paper
                    
                    # Save result
                    save_result(result)
                    
                    # Update statistics
                    processed_count += 1
                    if result['success']:
                        stats['successful'] += 1
                    else:
                        stats['failed'] += 1
                    
                    stats['total_tokens'] += result['total_tokens']
                    stats['total_cost_usd'] += result['cost_usd']
                    stats['total_processing_time_seconds'] += result['processing_time_seconds']
                    
                    # Progress logging
                    if processed_count % PROGRESS_LOG_INTERVAL == 0 or processed_count == len(papers):
                        elapsed = time.time() - overall_start
                        papers_per_sec = processed_count / elapsed if elapsed > 0 else 0
                        eta_seconds = (len(papers) - processed_count) / papers_per_sec if papers_per_sec > 0 else 0
                        
                        logger.info(
                            f"Progress: {processed_count}/{len(papers)} ({100*processed_count/len(papers):.1f}%) | "
                            f"Success: {stats['successful']} | Failed: {stats['failed']} | "
                            f"Speed: {papers_per_sec:.2f} p/s | ETA: {eta_seconds/60:.1f} min | "
                            f"Tokens: {stats['total_tokens']:,} | Cost: ${stats['total_cost_usd']:.4f}"
                        )
                    
                    # Checkpoint
                    if processed_count % CHECKPOINT_INTERVAL == 0:
                        save_checkpoint(run_id, stats, processed_count, len(papers))
                    
                except Exception as e:
                    logger.error(f"Error processing future: {e}")
                    stats['failed'] += 1
                    processed_count += 1
        
    except KeyboardInterrupt:
        logger.warning("Keyboard interrupt received!")
        shutdown_requested = True
    except Exception as e:
        logger.error(f"Unexpected error during processing: {e}")
    
    # Final statistics
    total_time = time.time() - overall_start
    stats['total_processing_time_seconds'] = total_time
    
    # Update run status
    final_status = 'interrupted' if shutdown_requested else 'completed'
    update_processing_run(run_id, stats, status=final_status)
    
    # Print final report
    logger.info("")
    logger.info("="*80)
    logger.info(f"PROCESSING {final_status.upper()}")
    logger.info("="*80)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Total papers: {stats['total_papers']}")
    logger.info(f"Processed: {processed_count}")
    logger.info(f"Successful: {stats['successful']} ({100*stats['successful']/processed_count:.1f}%)" if processed_count > 0 else "Successful: 0")
    logger.info(f"Failed: {stats['failed']} ({100*stats['failed']/processed_count:.1f}%)" if processed_count > 0 else "Failed: 0")
    logger.info(f"Total tokens: {stats['total_tokens']:,}")
    logger.info(f"Total cost: ${stats['total_cost_usd']:.4f}")
    logger.info(f"Total time: {total_time/60:.2f} minutes ({total_time/3600:.2f} hours)")
    if processed_count > 0:
        logger.info(f"Average time per paper: {total_time/processed_count:.2f} seconds")
        logger.info(f"Average speed: {processed_count/total_time*60:.1f} papers/minute")
    logger.info(f"Results saved to: {RESULTS_DB_PATH}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("="*80)
    
    if shutdown_requested:
        logger.warning("Process was interrupted. You can re-run to continue from where you left off.")
        logger.warning("Already processed papers are stored in the database and will be skipped.")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process papers with LLM judge (Enhanced Version)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all unprocessed papers with 10 workers
  python src/process_papers_enhanced.py --workers 10
  
  # Process 1000 papers with 5 workers
  python src/process_papers_enhanced.py --limit 1000 --workers 5
  
  # Test mode - process 5 papers
  python src/process_papers_enhanced.py --test
        """
    )
    
    parser.add_argument("--limit", type=int, default=None, 
                        help="Limit number of papers to process (default: all unprocessed)")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS,
                        help=f"Number of parallel workers (default: {MAX_WORKERS})")
    parser.add_argument("--test", action="store_true",
                        help="Test mode - process only 5 papers with 2 workers")
    
    args = parser.parse_args()
    
    if args.test:
        logger.info("TEST MODE: Processing 5 papers only")
        process_papers_parallel(limit=5, max_workers=2)
    else:
        process_papers_parallel(limit=args.limit, max_workers=args.workers)
