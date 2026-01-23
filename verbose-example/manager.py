"""
Performance Comparison Manager

This script runs all execution methods (single-threaded, multithreading with GIL,
multithreading without GIL, and multiprocessing) and compares their performance.

It provides detailed metrics including:
- Execution time
- CPU usage
- Memory usage
- Process/Thread information
"""

import time
import sys
import os
import platform
import psutil
import re
from typing import Dict, List, Any, Optional
import json
import threading

# Import our execution methods
from single import run_single_threaded
from threads import run_multithreaded_gil, run_multithreaded_free_threading
from processes import run_multiprocessing


def get_system_info() -> Dict[str, Any]:
    """Collect system information for context."""
    # Check for free-threading (PEP 703)
    is_free_threaded = False
    
    # Method 1: Check sys._is_free_threaded attribute (PEP 703)
    if hasattr(sys, '_is_free_threaded'):
        is_free_threaded = sys._is_free_threaded
    
    # Method 2: Check Python version string for "t" suffix (free-threaded builds)
    # Free-threaded builds often have "t" in the version string (e.g., "3.14.2t")
    if not is_free_threaded:
        version_str = sys.version.lower()
        # Check for patterns like "3.14.2t" or "free-threaded"
        if re.search(r'\d+\.\d+\.\d+t', version_str) or 'free-threaded' in version_str:
            is_free_threaded = True
    
    # Method 3: Check executable name or path for free-threaded indicators
    if not is_free_threaded:
        executable = sys.executable.lower()
        # Check for "t" suffix in version numbers or "free-threaded" in path
        if re.search(r'3\.\d+\.\d+t', executable) or 'free-threaded' in executable:
            is_free_threaded = True
    
    return {
        'python_version': sys.version,
        'platform': platform.platform(),
        'cpu_count_physical': psutil.cpu_count(logical=False),
        'cpu_count_logical': psutil.cpu_count(logical=True),
        'memory_total_gb': psutil.virtual_memory().total / (1024**3),
        'is_free_threaded': is_free_threaded
    }


class ResourceMonitor:
    """Monitor CPU and memory usage during task execution."""
    
    def __init__(self, process_ids: Optional[List[int]] = None, interval: float = 0.1):
        """
        Initialize resource monitor.
        
        Args:
            process_ids: List of process IDs to monitor. If None, monitors current process.
            interval: Sampling interval in seconds
        """
        self.process_ids = process_ids or [os.getpid()]
        self.interval = interval
        self.monitoring = False
        self.samples = []
        self.monitor_thread = None
        
    def _monitor_loop(self):
        """Internal monitoring loop that runs in a separate thread."""
        # First pass: initialize CPU percent calculation (non-blocking)
        for pid in self.process_ids:
            try:
                proc = psutil.Process(pid)
                proc.cpu_percent()  # Initialize (returns 0.0)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Small delay to allow first measurement
        time.sleep(0.05)
        
        while self.monitoring:
            sample = {
                'timestamp': time.time(),
                'cpu_samples': [],
                'memory_samples': []
            }
            
            for pid in self.process_ids:
                try:
                    proc = psutil.Process(pid)
                    # Get CPU usage (non-blocking - returns since last call)
                    cpu_percent = proc.cpu_percent(interval=None)
                    memory_mb = proc.memory_info().rss / (1024**2)
                    sample['cpu_samples'].append(cpu_percent)
                    sample['memory_samples'].append(memory_mb)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process may have terminated
                    pass
            
            if sample['cpu_samples']:
                # Aggregate across all processes
                sample['cpu_total'] = sum(sample['cpu_samples'])
                sample['memory_total'] = sum(sample['memory_samples'])
                self.samples.append(sample)
            
            # Sleep for sampling interval
            time.sleep(self.interval)
    
    def start(self):
        """Start monitoring in a background thread."""
        self.monitoring = True
        self.samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self) -> Dict[str, Any]:
        """
        Stop monitoring and return aggregated statistics.
        
        Returns:
            Dictionary with resource usage statistics
        """
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        if not self.samples:
            return {
                'cpu_avg': 0.0,
                'cpu_max': 0.0,
                'memory_avg_mb': 0.0,
                'memory_max_mb': 0.0,
                'samples': 0
            }
        
        cpu_values = [s['cpu_total'] for s in self.samples]
        memory_values = [s['memory_total'] for s in self.samples]
        
        return {
            'cpu_avg': sum(cpu_values) / len(cpu_values) if cpu_values else 0.0,
            'cpu_max': max(cpu_values) if cpu_values else 0.0,
            'memory_avg_mb': sum(memory_values) / len(memory_values) if memory_values else 0.0,
            'memory_max_mb': max(memory_values) if memory_values else 0.0,
            'samples': len(self.samples)
        }


def get_resource_snapshot() -> Dict[str, Any]:
    """
    Get a snapshot of current CPU and memory usage.
    DEPRECATED: Use ResourceMonitor for accurate monitoring during execution.
    
    Returns:
        Dictionary with resource usage statistics
    """
    process = psutil.Process(os.getpid())
    # Get CPU usage (non-blocking, returns immediately)
    cpu_percent = process.cpu_percent(interval=None)
    memory_mb = process.memory_info().rss / (1024**2)
    
    return {
        'cpu_avg': cpu_percent,
        'cpu_max': cpu_percent,
        'memory_avg_mb': memory_mb,
        'memory_max_mb': memory_mb,
        'samples': 1
    }


def run_comparison(num_tasks: int = 4, iterations: int = 10_000_000) -> Dict[str, Any]:
    """
    Run all execution methods and compare their performance.
    
    Args:
        num_tasks: Number of tasks to execute
        iterations: Number of iterations per task
    
    Returns:
        Dictionary with comparison results
    """
    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON: Single-threaded vs Multithreading vs Multiprocessing")
    print("="*80)
    
    system_info = get_system_info()
    print(f"\nSystem Information:")
    print(f"  Python Version: {system_info['python_version']}")
    print(f"  Platform: {system_info['platform']}")
    print(f"  Physical CPU Cores: {system_info['cpu_count_physical']}")
    print(f"  Logical CPU Cores: {system_info['cpu_count_logical']}")
    print(f"  Total Memory: {system_info['memory_total_gb']:.2f} GB")
    print(f"  Free-threaded Build: {system_info.get('is_free_threaded', 'Unknown')}")
    
    results = {}
    
    # 1. Single-threaded
    print("\n" + "="*80)
    print("1. SINGLE-THREADED EXECUTION")
    print("="*80)
    monitor = ResourceMonitor()
    monitor.start()
    single_result = run_single_threaded(num_tasks, iterations)
    single_resources = monitor.stop()
    results['single_threaded'] = {
        **single_result,
        'resources': single_resources
    }

    
    # 2. Multithreading without GIL (free-threading) - if available
    print("\n" + "="*80)
    print("3. MULTITHREADING")
    print("="*80)
    try:
        monitor = ResourceMonitor()
        monitor.start()
        threads_free_result = run_multithreaded_free_threading(num_tasks, iterations)
        threads_free_resources = monitor.stop()
        results['multithreading_free_threading'] = {
            **threads_free_result,
            'resources': threads_free_resources
        }
    except Exception as e:
        print(f"⚠️  Free-threading test failed: {e}")
        print("   This is expected if you're not using Python 3.14+ with free-threading enabled.")
        results['multithreading_free_threading'] = None
    
    # 3. Multiprocessing
    print("\n" + "="*80)
    print("4. MULTIPROCESSING")
    print("="*80)
    # Set multiprocessing start method for compatibility (especially on WSL)
    # WSL sometimes has issues with forkserver, so we try 'fork' first
    try:
        import multiprocessing
        current_method = multiprocessing.get_start_method(allow_none=True)
        if current_method is None or current_method == 'forkserver':
            try:
                multiprocessing.set_start_method('fork', force=True)
            except (RuntimeError, ValueError):
                # 'fork' not available - try 'spawn' as fallback
                try:
                    multiprocessing.set_start_method('spawn', force=True)
                except (RuntimeError, ValueError):
                    pass  # Use default
    except Exception:
        pass  # Continue with default
    
    # For multiprocessing, monitor the main process during execution
    # Note: Child processes run independently, so main process CPU will be lower
    # but we can still see that work is happening
    monitor = ResourceMonitor()
    monitor.start()
    processes_result = run_multiprocessing(num_tasks, iterations)
    processes_resources = monitor.stop()
    results['multiprocessing'] = {
        **processes_result,
        'resources': processes_resources
    }
    
    return results


def print_comparison_table(results: Dict[str, Any]):
    """Print a formatted comparison table of all results."""
    print("\n" + "="*80)
    print("COMPREHENSIVE COMPARISON TABLE")
    print("="*80)
    
    # Table header
    print(f"\n{'Method':<35} {'Total Time (s)':<18} {'CPU Avg %':<12} {'Memory Avg (MB)':<18}")
    print("-" * 80)
    
    # Single-threaded
    if 'single_threaded' in results:
        st = results['single_threaded']
        print(f"{'Single-threaded':<35} {st['total_time']:<18.4f} "
              f"{st['resources']['cpu_avg']:<12.1f} {st['resources']['memory_avg_mb']:<18.2f}")
    
    # Multithreading with GIL
    if 'multithreading_gil' in results:
        mt_gil = results['multithreading_gil']
        print(f"{'Multithreading (with GIL)':<35} {mt_gil['total_time']:<18.4f} "
              f"{mt_gil['resources']['cpu_avg']:<12.1f} {mt_gil['resources']['memory_avg_mb']:<18.2f}")
    
    # Multithreading without GIL
    if 'multithreading_free_threading' in results and results['multithreading_free_threading']:
        mt_free = results['multithreading_free_threading']
        print(f"{'Multithreading (free-threading)':<35} {mt_free['total_time']:<18.4f} "
              f"{mt_free['resources']['cpu_avg']:<12.1f} {mt_free['resources']['memory_avg_mb']:<18.2f}")
    
    # Multiprocessing
    if 'multiprocessing' in results:
        mp = results['multiprocessing']
        print(f"{'Multiprocessing':<35} {mp['total_time']:<18.4f} "
              f"{mp['resources']['cpu_avg']:<12.1f} {mp['resources']['memory_avg_mb']:<18.2f}")
    
    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)
    
    if 'single_threaded' in results and 'multithreading_gil' in results:
        st_time = results['single_threaded']['total_time']
        mt_gil_time = results['multithreading_gil']['total_time']
        speedup_gil = st_time / mt_gil_time if mt_gil_time > 0 else 0
        print(f"\n1. Single-threaded vs Multithreading (with GIL):")
        print(f"   Speedup: {speedup_gil:.2f}x")
        if speedup_gil < 1.2:
            print(f"   ⚠️  GIL prevents parallel execution - similar performance to single-threaded")
        else:
            print(f"   ✓ Some benefit, but limited by GIL")
    
    if 'single_threaded' in results and 'multiprocessing' in results:
        st_time = results['single_threaded']['total_time']
        mp_time = results['multiprocessing']['total_time']
        speedup_mp = st_time / mp_time if mp_time > 0 else 0
        print(f"\n2. Single-threaded vs Multiprocessing:")
        print(f"   Speedup: {speedup_mp:.2f}x")
        if speedup_mp > 1.5:
            print(f"   ✓ Significant speedup! Multiprocessing utilizes multiple CPU cores")
        else:
            print(f"   ⚠️  Limited speedup - may be due to overhead or limited CPU cores")
    
    if 'multithreading_free_threading' in results and results['multithreading_free_threading']:
        mt_free_time = results['multithreading_free_threading']['total_time']
        if 'single_threaded' in results:
            st_time = results['single_threaded']['total_time']
            speedup_free = st_time / mt_free_time if mt_free_time > 0 else 0
            print(f"\n3. Single-threaded vs Multithreading:")
            print(f"   Speedup: {speedup_free:.2f}x")
            if speedup_free > 1.5:
                print(f"   ✓ Free-threading enables true parallel execution!")
            elif speedup_free < 1.0:
                print(f"   ⚠️  SLOWER than single-threaded! This indicates GIL is present.")
                print(f"      GIL overhead (context switching, lock acquisition) makes it worse.")
                print(f"      This is why multiprocessing is better for CPU-bound tasks with GIL.")
            else:
                print(f"   ⚠️  Limited speedup - may need optimization or free-threading not enabled")
    
    print(f"\n{'='*80}")
    print("EXPLANATION OF RESULTS")
    print("="*80)
    print("""
TIMING EXPLANATION:
   - Individual task times: Time each task takes to complete (measured inside the task)
   - Total time: Wall-clock time from start to finish
   - Single-threaded: Total time = sum of individual times (tasks run sequentially)
   - Multithreading/Multiprocessing: Total time ≈ longest task time (tasks run in parallel)

1. SINGLE-THREADED:
   - Tasks run one after another (sequentially)
   - Total time = sum of all individual task times
   - Example: 4 tasks × 0.47s each = ~1.88s total
   - Uses one CPU core
   - Simple, predictable, but slow for CPU-bound tasks

2. MULTITHREADING (WITH GIL):
   - GIL prevents true parallel execution for CPU-bound tasks
   - Threads take turns executing (time-slicing)
   - Similar performance to single-threaded for CPU-bound work
   - Good for I/O-bound tasks (waiting releases GIL)

3. MULTITHREADING:
   - If free-threading (GIL removed): threads can run in parallel, significant speedup
   - If GIL present: threads CANNOT run in parallel, may be SLOWER due to overhead
   - GIL overhead includes: context switching, lock acquisition/release, thread management
   - This is why multithreading with GIL is often WORSE than single-threaded for CPU-bound tasks
   - Requires Python 3.14+ with free-threading enabled for true parallelism

4. MULTIPROCESSING:
   - Each process has its own Python interpreter (own GIL)
   - Processes run in parallel on multiple CPU cores
   - Total time ≈ longest task time (tasks run simultaneously)
   - Best option for CPU-bound tasks in traditional Python
   - More overhead than threads, but true parallelism

CPU USAGE NOTES:
   - CPU usage is measured during task execution
   - Single-threaded: Should show ~100% on one core (or ~4% on 24-core system)
   - Multithreading/Multiprocessing: Should show higher CPU usage across multiple cores
   - If showing 0%, monitoring may have occurred after tasks completed
    """)


def save_results(results: Dict[str, Any], filename: str = "comparison_results.json"):
    """Save results to a JSON file for later analysis."""
    # Convert results to JSON-serializable format
    json_results = {}
    for key, value in results.items():
        if value is None:
            json_results[key] = None
        else:
            json_results[key] = {
                'method': value.get('method'),
                'num_tasks': value.get('num_tasks'),
                'total_time': value.get('total_time'),
                'individual_times': value.get('individual_times'),
                'resources': value.get('resources')
            }
    
    with open(filename, 'w') as f:
        json.dump(json_results, f, indent=2)
    print(f"\n✓ Results saved to {filename}")


if __name__ == "__main__":
    # Check if psutil is available
    try:
        import psutil
    except ImportError:
        print("ERROR: psutil is required for resource monitoring.")
        print("Install it with: pip install psutil")
        sys.exit(1)
    
    # Run comparison
    # Adjust these parameters to test with different workloads
    NUM_TASKS = 4
    ITERATIONS = 10_000_000  # Adjust based on your CPU speed (lower = faster test)
    
    print(f"\nConfiguration:")
    print(f"  Number of tasks: {NUM_TASKS}")
    print(f"  Iterations per task: {ITERATIONS:,}")
    print(f"\nStarting comparison...")
    
    comparison_results = run_comparison(num_tasks=NUM_TASKS, iterations=ITERATIONS)
    
    # Print comparison table
    print_comparison_table(comparison_results)
    
    # Save results
    save_results(comparison_results)
    
    print("\n" + "="*80)
    print("Comparison complete!")
    print("="*80)
