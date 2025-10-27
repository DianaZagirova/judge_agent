#!/usr/bin/env python3
"""
Real-time monitoring script for paper processing.
Shows current progress, stats, and estimates.
Run this in a separate terminal while process_papers.py is running.
"""

import sqlite3
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = "data/evaluations.db"
PAPERS_DB_PATH = "/home/diana.z/hack/download_papers_pubmed/paper_collection/data/papers.db"
REFRESH_INTERVAL = 5  # seconds

def clear_screen():
    """Clear terminal screen."""
    print("\033[H\033[J", end="")

def get_stats():
    """Get current processing statistics."""
    try:
        # Get results stats
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        # Total processed
        cursor.execute("SELECT COUNT(*) FROM paper_evaluations")
        total_processed = cursor.fetchone()[0]
        
        # Success/fail counts
        cursor.execute("SELECT COUNT(*) FROM paper_evaluations WHERE success = 1")
        successful = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM paper_evaluations WHERE success = 0")
        failed = cursor.fetchone()[0]
        
        # Result breakdown
        cursor.execute("""
            SELECT result, COUNT(*) 
            FROM paper_evaluations 
            WHERE success = 1 
            GROUP BY result
        """)
        result_breakdown = dict(cursor.fetchall())
        
        # Token and cost totals
        cursor.execute("""
            SELECT 
                SUM(total_tokens),
                SUM(cost_usd),
                AVG(processing_time_seconds),
                MIN(timestamp),
                MAX(timestamp)
            FROM paper_evaluations
        """)
        tokens, cost, avg_time, min_time, max_time = cursor.fetchone()
        
        # Current runs
        cursor.execute("""
            SELECT id, start_time, status, max_workers
            FROM processing_runs
            ORDER BY id DESC
            LIMIT 1
        """)
        run_info = cursor.fetchone()
        
        conn.close()
        
        # Get total papers available
        papers_conn = sqlite3.connect(PAPERS_DB_PATH, timeout=10.0)
        papers_cursor = papers_conn.cursor()
        papers_cursor.execute("""
            SELECT COUNT(*) FROM papers 
            WHERE doi IS NOT NULL AND abstract IS NOT NULL
        """)
        total_papers = papers_cursor.fetchone()[0]
        papers_conn.close()
        
        return {
            'total_processed': total_processed,
            'successful': successful,
            'failed': failed,
            'result_breakdown': result_breakdown,
            'total_tokens': tokens or 0,
            'total_cost': cost or 0,
            'avg_time': avg_time or 0,
            'min_time': min_time,
            'max_time': max_time,
            'run_info': run_info,
            'total_papers': total_papers,
            'remaining': total_papers - total_processed
        }
    except Exception as e:
        return {'error': str(e)}

def format_duration(seconds):
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def display_stats(stats, last_stats=None):
    """Display formatted statistics."""
    clear_screen()
    
    if 'error' in stats:
        print(f"Error: {stats['error']}")
        print("\nMake sure the processing script is running and the database exists.")
        return
    
    print("="*80)
    print(" PAPER PROCESSING - LIVE MONITOR".center(80))
    print("="*80)
    print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run info
    if stats['run_info']:
        run_id, start_time, status, workers = stats['run_info']
        print(f"Run #{run_id} | Status: {status.upper()} | Workers: {workers}")
        print(f"Started: {start_time}")
    
    print("\n" + "-"*80)
    print(" PROGRESS")
    print("-"*80)
    
    total = stats['total_papers']
    processed = stats['total_processed']
    remaining = stats['remaining']
    
    if total > 0:
        pct = 100 * processed / total
        bar_width = 50
        filled = int(bar_width * processed / total)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"\n[{bar}] {pct:.1f}%")
    
    print(f"\nTotal papers:     {total:,}")
    print(f"Processed:        {processed:,}")
    print(f"Remaining:        {remaining:,}")
    
    print("\n" + "-"*80)
    print(" RESULTS")
    print("-"*80)
    
    success = stats['successful']
    failed = stats['failed']
    
    if processed > 0:
        success_pct = 100 * success / processed
        fail_pct = 100 * failed / processed
        print(f"\nSuccessful:       {success:,} ({success_pct:.1f}%)")
        print(f"Failed:           {failed:,} ({fail_pct:.1f}%)")
    else:
        print(f"\nSuccessful:       {success:,}")
        print(f"Failed:           {failed:,}")
    
    # Result breakdown
    if stats['result_breakdown']:
        print("\nBreakdown:")
        for result, count in sorted(stats['result_breakdown'].items(), key=lambda x: x[1], reverse=True):
            if processed > 0:
                pct = 100 * count / processed
                print(f"  {result or 'null':15s} {count:6,} ({pct:.1f}%)")
    
    print("\n" + "-"*80)
    print(" PERFORMANCE")
    print("-"*80)
    
    # Calculate speed
    if stats['min_time'] and stats['max_time']:
        start = datetime.fromisoformat(stats['min_time'])
        end = datetime.fromisoformat(stats['max_time'])
        duration = (end - start).total_seconds()
        
        if duration > 0:
            speed = processed / duration
            print(f"\nDuration:         {format_duration(duration)}")
            print(f"Speed:            {speed:.2f} papers/second ({speed*60:.1f} papers/min)")
            print(f"Avg per paper:    {duration/processed:.2f} seconds")
            
            # ETA
            if remaining > 0:
                eta_seconds = remaining / speed
                eta_time = datetime.now() + timedelta(seconds=eta_seconds)
                print(f"\nEstimated ETA:    {format_duration(eta_seconds)}")
                print(f"Completion time:  {eta_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Delta since last check (if available)
    if last_stats and 'total_processed' in last_stats:
        delta_processed = processed - last_stats['total_processed']
        delta_time = REFRESH_INTERVAL
        if delta_processed > 0:
            current_speed = delta_processed / delta_time
            print(f"\nCurrent speed:    {current_speed:.2f} papers/second (last {REFRESH_INTERVAL}s)")
    
    print("\n" + "-"*80)
    print(" RESOURCES")
    print("-"*80)
    
    print(f"\nTokens used:      {stats['total_tokens']:,}")
    print(f"Total cost:       ${stats['total_cost']:.4f}")
    
    if processed > 0:
        avg_tokens = stats['total_tokens'] / processed
        avg_cost = stats['total_cost'] / processed
        print(f"Avg per paper:    {avg_tokens:.0f} tokens, ${avg_cost:.6f}")
    
    # Projected totals
    if remaining > 0 and processed > 0:
        projected_tokens = stats['total_tokens'] * (total / processed)
        projected_cost = stats['total_cost'] * (total / processed)
        print(f"\nProjected total:  {projected_tokens:,.0f} tokens, ${projected_cost:.2f}")
    
    print("\n" + "="*80)
    print(f"Refreshing every {REFRESH_INTERVAL} seconds... (Press Ctrl+C to exit)")
    print("="*80)

def main():
    """Main monitoring loop."""
    if not Path(DB_PATH).exists():
        print(f"Database not found: {DB_PATH}")
        print("Make sure process_papers.py has been started at least once.")
        sys.exit(1)
    
    print("Starting monitor... (Press Ctrl+C to exit)")
    time.sleep(1)
    
    last_stats = None
    
    try:
        while True:
            stats = get_stats()
            display_stats(stats, last_stats)
            last_stats = stats
            time.sleep(REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
