#!/usr/bin/env python3
"""
Pre-flight check script to verify system readiness before processing 60k papers.
Checks: database access, API connection, disk space, configuration, etc.
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.llm_judge import llm_judge

# Configuration
PAPERS_DB_PATH = "/home/diana.z/hack/download_papers_pubmed/paper_collection/data/papers.db"
RESULTS_DB_PATH = "/home/diana.z/hack/llm_judge/data/evaluations.db"
LOG_DIR = "/home/diana.z/hack/llm_judge/logs"
MIN_DISK_SPACE_GB = 5  # Minimum free disk space required

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BLUE}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*80}{Colors.RESET}\n")

def check_pass(text):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {text}")
    return True

def check_fail(text):
    print(f"  {Colors.RED}✗{Colors.RESET} {text}")
    return False

def check_warn(text):
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {text}")

def check_env_variables():
    """Check if required environment variables are set."""
    print("Checking environment variables...")
    
    required_vars = [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_API_VERSION'
    ]
    
    all_set = True
    for var in required_vars:
        if os.getenv(var):
            check_pass(f"{var} is set")
        else:
            check_fail(f"{var} is NOT set")
            all_set = False
    
    return all_set

def check_database_access():
    """Check if databases are accessible."""
    print("\nChecking database access...")
    
    success = True
    
    # Check papers database
    if Path(PAPERS_DB_PATH).exists():
        try:
            conn = sqlite3.connect(PAPERS_DB_PATH, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM papers WHERE doi IS NOT NULL AND abstract IS NOT NULL")
            count = cursor.fetchone()[0]
            conn.close()
            check_pass(f"Papers database accessible: {count:,} papers with DOI and abstract")
        except Exception as e:
            check_fail(f"Papers database error: {e}")
            success = False
    else:
        check_fail(f"Papers database not found at: {PAPERS_DB_PATH}")
        success = False
    
    # Check results database
    results_dir = Path(RESULTS_DB_PATH).parent
    if not results_dir.exists():
        check_warn(f"Results directory does not exist, will be created: {results_dir}")
    else:
        check_pass(f"Results directory exists: {results_dir}")
    
    return success

def check_disk_space():
    """Check available disk space."""
    print("\nChecking disk space...")
    
    result_dir = Path(RESULTS_DB_PATH).parent
    result_dir.mkdir(parents=True, exist_ok=True)
    
    stat = shutil.disk_usage(result_dir)
    free_gb = stat.free / (1024**3)
    total_gb = stat.total / (1024**3)
    used_gb = stat.used / (1024**3)
    
    print(f"  Disk space on {result_dir}:")
    print(f"    Total: {total_gb:.1f} GB")
    print(f"    Used:  {used_gb:.1f} GB ({100*stat.used/stat.total:.1f}%)")
    print(f"    Free:  {free_gb:.1f} GB ({100*stat.free/stat.total:.1f}%)")
    
    if free_gb >= MIN_DISK_SPACE_GB:
        check_pass(f"Sufficient disk space available ({free_gb:.1f} GB free)")
        return True
    else:
        check_fail(f"Low disk space! Only {free_gb:.1f} GB free (need at least {MIN_DISK_SPACE_GB} GB)")
        return False

def check_log_directory():
    """Check if log directory exists and is writable."""
    print("\nChecking log directory...")
    
    log_path = Path(LOG_DIR)
    
    try:
        log_path.mkdir(parents=True, exist_ok=True)
        test_file = log_path / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
        check_pass(f"Log directory is writable: {LOG_DIR}")
        return True
    except Exception as e:
        check_fail(f"Log directory not writable: {e}")
        return False

def check_api_connection():
    """Test API connection with a simple query."""
    print("\nTesting Azure OpenAI API connection...")
    
    test_text = "Aging is a complex biological process: This is a test abstract to verify API connectivity."
    
    try:
        result = llm_judge(test_text)
        if result and 'result' in result:
            check_pass(f"API connection successful (result: {result.get('result')})")
            if '_tokens' in result:
                tokens = result['_tokens']
                print(f"    Tokens used: {tokens.get('total_tokens', 0)} (prompt: {tokens.get('prompt_tokens', 0)}, completion: {tokens.get('completion_tokens', 0)})")
            return True
        else:
            check_fail("API returned unexpected response")
            return False
    except Exception as e:
        check_fail(f"API connection failed: {e}")
        return False

def estimate_processing():
    """Estimate processing time and cost."""
    print("\nEstimating processing requirements...")
    
    try:
        conn = sqlite3.connect(PAPERS_DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        # Get total papers with abstract
        cursor.execute("SELECT COUNT(*) FROM papers WHERE doi IS NOT NULL AND abstract IS NOT NULL")
        total_papers = cursor.fetchone()[0]
        
        # Get already processed count
        if Path(RESULTS_DB_PATH).exists():
            results_conn = sqlite3.connect(RESULTS_DB_PATH, timeout=10.0)
            results_cursor = results_conn.cursor()
            results_cursor.execute("SELECT COUNT(*) FROM paper_evaluations")
            processed = results_cursor.fetchone()[0]
            results_conn.close()
        else:
            processed = 0
        
        conn.close()
        
        remaining = total_papers - processed
        
        print(f"  Total papers in database: {total_papers:,}")
        print(f"  Already processed: {processed:,}")
        print(f"  Remaining to process: {remaining:,}")
        
        if remaining > 0:
            # Estimate based on 2000 tokens per paper, 10 workers, 2 papers/sec
            avg_tokens_per_paper = 2000
            papers_per_sec = 2.0
            cost_per_paper = (avg_tokens_per_paper / 1000) * 0.0003  # rough estimate
            
            estimated_time_seconds = remaining / papers_per_sec
            estimated_cost = remaining * cost_per_paper
            
            print(f"\n  Estimated (with 10 workers):")
            print(f"    Processing time: {estimated_time_seconds/3600:.1f} hours ({estimated_time_seconds/60:.0f} minutes)")
            print(f"    Total cost: ${estimated_cost:.2f}")
            print(f"    Tokens: ~{remaining * avg_tokens_per_paper:,}")
            
            check_warn("These are rough estimates. Actual values may vary.")
        
        return True
        
    except Exception as e:
        check_fail(f"Error estimating: {e}")
        return False

def check_dependencies():
    """Check if required Python packages are installed."""
    print("\nChecking Python dependencies...")
    
    required_packages = [
        ('openai', 'OpenAI Python SDK'),
        ('sqlite3', 'SQLite3'),
    ]
    
    all_ok = True
    for module_name, description in required_packages:
        try:
            __import__(module_name)
            check_pass(f"{description} installed")
        except ImportError:
            check_fail(f"{description} NOT installed")
            all_ok = False
    
    return all_ok

def main():
    """Run all pre-flight checks."""
    print_header("PRE-FLIGHT CHECK FOR LARGE-SCALE PAPER PROCESSING")
    
    checks = []
    
    # Run all checks
    checks.append(("Dependencies", check_dependencies()))
    checks.append(("Environment Variables", check_env_variables()))
    checks.append(("Database Access", check_database_access()))
    checks.append(("Disk Space", check_disk_space()))
    checks.append(("Log Directory", check_log_directory()))
    checks.append(("API Connection", check_api_connection()))
    checks.append(("Processing Estimates", estimate_processing()))
    
    # Summary
    print_header("SUMMARY")
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for check_name, result in checks:
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {check_name:.<40} {status}")
    
    print(f"\n  Total: {passed}/{total} checks passed")
    
    if passed == total:
        print(f"\n  {Colors.GREEN}✓ System is ready for processing!{Colors.RESET}")
        print(f"\n  To start processing all papers with 10 workers, run:")
        print(f"    {Colors.BLUE}python src/process_papers.py --workers 10{Colors.RESET}")
        return 0
    else:
        print(f"\n  {Colors.RED}✗ Some checks failed. Please fix issues before proceeding.{Colors.RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
