"""
Multiprocessing example.

Multiprocessing creates separate Python processes, each with its own Python interpreter
and memory space. This bypasses the GIL completely because each process has its own GIL.

Key differences from threading:
- Each process has its own memory space (no shared memory by default)
- Processes can run in parallel on multiple CPU cores
- Communication between processes requires special mechanisms (queues, pipes, shared memory)
- More overhead than threads (process creation is heavier)
- Best for CPU-bound tasks in Python (with GIL)

Use multiprocessing when:
- You have CPU-bound tasks that need parallel execution
- You want to utilize multiple CPU cores
- Tasks are independent or can be easily parallelized
"""

import multiprocessing
import time
import os
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
        'process_id': os.getpid(),  # Each process has its own PID
        'iterations': iterations
    }


def _task_wrapper(task_id: int, iterations: int, queue: multiprocessing.Queue):
    """
    Wrapper function to run task and put result in queue.
    Must be at module level for multiprocessing pickling.
    """
    result = cpu_intensive_task(task_id, iterations)
    queue.put(result)
    print(f"    Task {task_id + 1} completed in {result['elapsed_time']:.4f}s "
          f"(Process ID: {result['process_id']})")


def run_multiprocessing(num_tasks: int = 4, iterations: int = 10_000_000) -> dict:
    """
    Execute multiple CPU-intensive tasks using separate processes.
    
    Each process runs independently and can utilize a separate CPU core.
    This bypasses the GIL because each process has its own Python interpreter.
    
    Args:
        num_tasks: Number of tasks to execute
        iterations: Number of iterations per task
    
    Returns:
        Dictionary with execution results and timing
    """
    # Set start method for compatibility (especially on WSL)
    # WSL sometimes has issues with forkserver, so we try 'fork' first, then 'spawn'
    current_method = multiprocessing.get_start_method(allow_none=True)
    if current_method is None or current_method == 'forkserver':
        try:
            multiprocessing.set_start_method('fork', force=True)
        except (RuntimeError, ValueError):
            # 'fork' not available (e.g., on Windows) - try 'spawn'
            try:
                multiprocessing.set_start_method('spawn', force=True)
            except (RuntimeError, ValueError):
                pass  # Use default
    
    print(f"\n{'='*60}")
    print(f"MULTIPROCESSING")
    print(f"{'='*60}")
    print(f"Running {num_tasks} tasks using separate processes...")
    print(f"Each task performs {iterations:,} iterations")
    print(f"✓  Each process can run on a separate CPU core!")
    print(f"✓  GIL is bypassed (each process has its own interpreter)")
    
    overall_start = time.perf_counter()
    processes: List[multiprocessing.Process] = []
    result_queue = multiprocessing.Queue()  # Queue for collecting results from processes
    
    # Create and start all processes
    for task_id in range(num_tasks):
        print(f"  Starting task {task_id + 1}/{num_tasks} in process...")
        process = multiprocessing.Process(
            target=_task_wrapper,
            args=(task_id, iterations, result_queue)
        )
        processes.append(process)
        process.start()
    
    # Wait for all processes to complete
    for process in processes:
        process.join()
    
    # Collect results from queue
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())
    
    # Sort results by task_id for consistency
    results.sort(key=lambda x: x['task_id'])
    
    overall_end = time.perf_counter()
    total_time = overall_end - overall_start
    
    return {
        'method': 'multiprocessing',
        'num_tasks': num_tasks,
        'total_time': total_time,
        'individual_times': [r['elapsed_time'] for r in results],
        'results': results,
        'main_process_id': os.getpid(),
        'process_ids': [r['process_id'] for r in results]
    }


if __name__ == "__main__":
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()
    
    # Set start method for compatibility (especially on WSL)
    # 'fork' is default on Linux, but explicit setting helps with WSL issues
    try:
        multiprocessing.set_start_method('fork', force=True)
    except RuntimeError:
        # Already set, or not available - try 'spawn' as fallback
        try:
            multiprocessing.set_start_method('spawn', force=True)
        except RuntimeError:
            pass  # Use default
    
    # Run example
    result = run_multiprocessing(num_tasks=4, iterations=10_000_000)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total execution time: {result['total_time']:.4f} seconds")
    print(f"Average time per task: {sum(result['individual_times']) / len(result['individual_times']):.4f} seconds")
    print(f"Main Process ID: {result['main_process_id']}")
    print(f"Worker Process IDs: {result['process_ids']}")
    print(f"\n✓  Notice: Total time should be much less than single-threaded!")
    print(f"   (Assuming you have multiple CPU cores available)")
