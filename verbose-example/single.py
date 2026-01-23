"""
Single-threaded execution example.

This runs tasks sequentially in a single thread, one after another.
No parallelism - each task must complete before the next starts.
"""

import time
import os


def cpu_intensive_task(task_id: int, iterations: int = 10_000_000) -> dict:
    """
    Simulates a CPU-intensive task (like number crunching, calculations).
    
    Args:
        task_id: Identifier for this task
        iterations: Number of iterations to perform (controls workload)
    
    Returns:
        Dictionary with task results and metadata
    """
    start_time = time.perf_counter()
    result = 0
    
    # CPU-intensive loop: performing calculations
    for i in range(iterations):
        result += i * i  # Square each number and sum
    
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    
    return {
        'task_id': task_id,
        'result': result,
        'elapsed_time': elapsed,
        'thread_id': os.getpid(),  # Process ID (same for all in single-threaded)
        'iterations': iterations
    }


def run_single_threaded(num_tasks: int = 4, iterations: int = 10_000_000) -> dict:
    """
    Execute multiple CPU-intensive tasks sequentially in a single thread.
    
    Args:
        num_tasks: Number of tasks to execute
        iterations: Number of iterations per task
    
    Returns:
        Dictionary with execution results and timing
    """
    print(f"\n{'='*60}")
    print(f"SINGLE-THREADED EXECUTION")
    print(f"{'='*60}")
    print(f"Running {num_tasks} tasks sequentially in one thread...")
    print(f"Each task performs {iterations:,} iterations")
    
    overall_start = time.perf_counter()
    results = []
    
    # Execute tasks one by one
    for task_id in range(num_tasks):
        print(f"  Starting task {task_id + 1}/{num_tasks}...")
        result = cpu_intensive_task(task_id, iterations)
        results.append(result)
        print(f"    Task {task_id + 1} completed in {result['elapsed_time']:.4f}s")
            
    overall_end = time.perf_counter()
    total_time = overall_end - overall_start
    
    return {
        'method': 'single-threaded',
        'num_tasks': num_tasks,
        'total_time': total_time,
        'individual_times': [r['elapsed_time'] for r in results],
        'results': results,
        'process_id': os.getpid()
    }


if __name__ == "__main__":
    # Run example
    result = run_single_threaded(num_tasks=4, iterations=10_000_000)
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total execution time: {result['total_time']:.4f} seconds")
    print(f"Average time per task: {sum(result['individual_times']) / len(result['individual_times']):.4f} seconds")
    print(f"Process ID: {result['process_id']}")
