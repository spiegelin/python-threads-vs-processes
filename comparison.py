"""
Performance Comparison: Single-threaded, Multithreading, and Multiprocessing

TIMING EXPLANATION:
- time.perf_counter(): High-resolution timer, best for measuring elapsed time
- Total Time: Wall-clock time from start to finish (includes overhead)
- Avg Task Time: Average time each individual task took to complete
- In parallel execution: Total time ≈ longest task + overhead
- In sequential execution: Total time = sum of all task times
"""

import time
import os
import threading
import multiprocessing
import psutil
from typing import List, Dict, Any


def cpu_intensive_task(task_id: int, iterations: int) -> dict:
    """CPU-intensive task: sum of squares."""
    start = time.perf_counter()
    result = sum(i * i for i in range(iterations))
    elapsed = time.perf_counter() - start
    print(f"Task {task_id} completed")
    return {
        'task_id': task_id,
        'elapsed_time': elapsed,
        'result': result
    }


def run_single_threaded(num_tasks: int, iterations: int) -> Dict[str, Any]:
    """Run tasks sequentially."""
    print(f"\n{'─' * 60}\nSINGLE-THREADED\n{'─' * 60}")
    # Total time: wall-clock time from start to finish (all tasks run sequentially)
    start = time.perf_counter()
    results = [cpu_intensive_task(i, iterations) for i in range(num_tasks)]
    total_time = time.perf_counter() - start
    return {
        'method': 'Single-threaded',
        'total_time': total_time,  # Sum of all individual task times
        'individual_times': [r['elapsed_time'] for r in results]  # Time each task took
    }


def run_multithreaded(num_tasks: int, iterations: int) -> Dict[str, Any]:
    """Run tasks using threads."""
    print(f"\n{'─' * 60}\nMULTITHREADING\n{'─' * 60}")
    # Total time: wall-clock time (tasks run in parallel, so ≈ longest task time)
    start = time.perf_counter()
    results = []
    lock = threading.Lock()
    
    def task_wrapper(task_id: int):
        result = cpu_intensive_task(task_id, iterations)
        with lock:
            results.append(result)
    
    threads = [threading.Thread(target=task_wrapper, args=(i,)) for i in range(num_tasks)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    return {
        'method': 'Multithreading',
        'total_time': time.perf_counter() - start,  # ≈ longest task (parallel execution)
        'individual_times': [r['elapsed_time'] for r in results]  # Time each task took
    }


def _task_wrapper(task_id: int, iterations: int, queue: multiprocessing.Queue):
    """Wrapper for multiprocessing."""
    result = cpu_intensive_task(task_id, iterations)
    queue.put(result)


def run_multiprocessing(num_tasks: int, iterations: int) -> Dict[str, Any]:
    """Run tasks using separate processes."""
    print(f"\n{'─' * 60}\nMULTIPROCESSING\n{'─' * 60}")
    
    # Set start method
    try:
        multiprocessing.set_start_method('fork', force=True)
    except (RuntimeError, ValueError):
        try:
            multiprocessing.set_start_method('spawn', force=True)
        except (RuntimeError, ValueError):
            pass
    
    # Total time: includes process creation overhead + longest task time
    start = time.perf_counter()
    queue = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(target=_task_wrapper, args=(i, iterations, queue))
        for i in range(num_tasks)
    ]
    
    for p in processes:
        p.start()
    for p in processes:
        p.join()
    
    results = []
    while not queue.empty():
        results.append(queue.get())
    results.sort(key=lambda x: x['task_id'])
    
    return {
        'method': 'Multiprocessing',
        'total_time': time.perf_counter() - start,  # Process overhead + longest task
        'individual_times': [r['elapsed_time'] for r in results]  # Time each task took
    }


def print_comparison_table(results: List[Dict[str, Any]]):
    """
    Print comparison table.
    
    Why multiprocessing can have lower avg task time but higher total time:
    - Avg Task Time: Each task runs in parallel, so individual task time is similar
    - Total Time: Includes process creation overhead (spawning processes, IPC setup)
      This overhead makes total time slightly higher than multithreading
    - Multithreading has less overhead (threads are lighter than processes)
    """
    print(f"\n{'─' * 80}")
    #print(f"{'Method':<20} {'Total Time (s)':<18} {'Avg Task Time (s)':<20} {'Speedup':<10}")
    print(f"{'Method':<20} {'Total Time (s)':<18} {'Speedup':<10}")
    print(f"{'─' * 80}")
    
    baseline = results[0]['total_time'] if results else 1.0
    
    for r in results:
        avg_task = sum(r['individual_times']) / len(r['individual_times'])
        speedup = baseline / r['total_time'] if r['total_time'] > 0 else 0
        #print(f"{r['method']:<20} {r['total_time']:<18.4f} {avg_task:<20.4f} {speedup:<10.2f}")
        print(f"{r['method']:<20} {r['total_time']:<18.4f} {speedup:<10.2f}")

    print(f"{'─' * 80}\n")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    NUM_TASKS = 4
    ITERATIONS = 10_000_000
    
    print(f"Configuration: {NUM_TASKS} tasks, {ITERATIONS:,} iterations each")
    
    results = [
        run_single_threaded(NUM_TASKS, ITERATIONS),
        run_multithreaded(NUM_TASKS, ITERATIONS),
        run_multiprocessing(NUM_TASKS, ITERATIONS)
    ]
    
    print_comparison_table(results)
