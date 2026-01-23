"""
Multithreading example (with GIL - traditional Python).

IMPORTANT: In Python with GIL (default builds), threads cannot truly run in parallel
for CPU-bound tasks. The GIL (Global Interpreter Lock) ensures only one thread
executes Python bytecode at a time, even on multi-core CPUs.

This means:
- I/O-bound tasks benefit from threading (waiting for I/O releases the GIL)
- CPU-bound tasks do NOT benefit from threading (GIL prevents parallel execution)
- Threads share the same memory space (easier data sharing, but requires synchronization)

For CPU-bound tasks, multiprocessing is better than threading in GIL Python.
"""

import threading
import time
import os
import re
from typing import List


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
        'thread_id': threading.get_ident(),  # Thread ID
        'process_id': os.getpid(),  # Process ID (same for all threads)
        'iterations': iterations
    }


def run_multithreaded_gil(num_tasks: int = 4, iterations: int = 10_000_000) -> dict:
    """
    Execute multiple CPU-intensive tasks using threads (with GIL).
    
    WARNING: Due to GIL, these threads will NOT run in parallel for CPU-bound tasks.
    They will execute sequentially, taking similar time to single-threaded execution.
    
    Args:
        num_tasks: Number of tasks to execute
        iterations: Number of iterations per task
    
    Returns:
        Dictionary with execution results and timing
    """
    print(f"\n{'='*60}")
    print(f"MULTITHREADING (WITH GIL - Traditional Python)")
    print(f"{'='*60}")
    print(f"Running {num_tasks} tasks using threads...")
    print(f"Each task performs {iterations:,} iterations")
    print(f"⚠️  NOTE: GIL prevents true parallel execution for CPU-bound tasks!")
    
    overall_start = time.perf_counter()
    results: List[dict] = []
    threads: List[threading.Thread] = []
    results_lock = threading.Lock()  # Lock for thread-safe result collection
    
    def task_wrapper(task_id: int):
        """Wrapper function to run task and collect results safely."""
        result = cpu_intensive_task(task_id, iterations)
        with results_lock:
            results.append(result)
        print(f"    Task {task_id + 1} completed in {result['elapsed_time']:.4f}s "
              f"(Thread ID: {result['thread_id']})")
    
    # Create and start all threads
    for task_id in range(num_tasks):
        print(f"  Starting task {task_id + 1}/{num_tasks} in thread...")
        thread = threading.Thread(target=task_wrapper, args=(task_id,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    overall_end = time.perf_counter()
    total_time = overall_end - overall_start
    
    return {
        'method': 'multithreading-gil',
        'num_tasks': num_tasks,
        'total_time': total_time,
        'individual_times': [r['elapsed_time'] for r in results],
        'results': results,
        'process_id': os.getpid(),
        'thread_ids': [r['thread_id'] for r in results]
    }


def run_multithreaded_free_threading(num_tasks: int = 4, iterations: int = 10_000_000) -> dict:
    """
    Execute multiple CPU-intensive tasks using threads (FREE-THREADING - No GIL).
    
    This function demonstrates how multithreading would work in Python 3.14+
    with free-threading (GIL removed). In free-threaded builds, threads CAN run
    in parallel on multiple CPU cores for CPU-bound tasks.
    
    NOTE: This requires Python 3.14+ with free-threading enabled.
    To check: python --version and ensure you're using a free-threaded build.
    
    Args:
        num_tasks: Number of tasks to execute
        iterations: Number of iterations per task
    
    Returns:
        Dictionary with execution results and timing
    """
    print(f"\n{'='*60}")
    print(f"MULTITHREADING")
    print(f"{'='*60}")
    print(f"Running {num_tasks} tasks using threads...")
    print(f"Each task performs {iterations:,} iterations")
    
    overall_start = time.perf_counter()
    results: List[dict] = []
    threads: List[threading.Thread] = []
    results_lock = threading.Lock()
    print_lock = threading.Lock()  # Separate lock for printing to reduce contention
    
    def task_wrapper(task_id: int):
        """Wrapper function to run task and collect results safely."""
        result = cpu_intensive_task(task_id, iterations)
        # Collect result (minimal lock time)
        with results_lock:
            results.append(result)
        # Print outside the main lock to reduce contention
        with print_lock:
            print(f"    Task {task_id + 1} completed in {result['elapsed_time']:.4f}s "
                  f"(Thread ID: {result['thread_id']})")
    
    # Create and start all threads
    for task_id in range(num_tasks):
        print(f"  Starting task {task_id + 1}/{num_tasks} in thread...")
        thread = threading.Thread(target=task_wrapper, args=(task_id,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    overall_end = time.perf_counter()
    total_time = overall_end - overall_start
    
    return {
        'method': 'multithreading-free-threading',
        'num_tasks': num_tasks,
        'total_time': total_time,
        'individual_times': [r['elapsed_time'] for r in results],
        'results': results,
        'process_id': os.getpid(),
        'thread_ids': [r['thread_id'] for r in results]
    }


if __name__ == "__main__":
    # Run example with GIL (traditional)
    print("\n" + "="*60)
    print("Testing multithreading with GIL (traditional Python)")
    print("="*60)
    result_gil = run_multithreaded_gil(num_tasks=4, iterations=10_000_000)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY (WITH GIL)")
    print(f"{'='*60}")
    print(f"Total execution time: {result_gil['total_time']:.4f} seconds")
    print(f"Average time per task: {sum(result_gil['individual_times']) / len(result_gil['individual_times']):.4f} seconds")
    print(f"Process ID: {result_gil['process_id']}")
    print(f"Thread IDs: {result_gil['thread_ids']}")
    print(f"\n⚠️  Notice: Total time is similar to single-threaded due to GIL!")
