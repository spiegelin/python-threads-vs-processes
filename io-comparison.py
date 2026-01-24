import threading
import time
import requests
import multiprocessing

def fetch_url(url, results, kind="thread"):
    """
    Fetch a URL and add the status code to the results list
    """
    if kind == "thread":
        print(f"Thread {threading.current_thread().name} starting")
        
        # This is I/O - GIL is RELEASED here
        response = requests.get(url)  # Waiting for network...
        # While waiting, other threads can run
        
        print(f"Thread {threading.current_thread().name} done")
        results.append(response.status_code)

    elif kind == "process":
        print(f"Process {multiprocessing.current_process().name} starting")
        response = requests.get(url)
        print(f"Process {multiprocessing.current_process().name} done")
        results.append(response.status_code)
    else:
        raise ValueError(f"Invalid kind: {kind}")

# All 4 threads can make requests simultaneously
# Because GIL is released during network wait time
def main():
    url = "https://www.google.com/"
    results_thread = []
    results_single = []

    # # -------------- Multi Threaded --------------- #
    threads = []
    start = time.perf_counter()
    for _ in range(4):
        t = threading.Thread(target=fetch_url, args=(url, results_thread))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()   # wait for threads to finish, if we dont wait, the program might exit early, so we will not see results

    end = time.perf_counter()
    print("Time taken: ", end - start)

    # -------------- Single threaded --------------- #
    start = time.perf_counter()
    for _ in range(4):
        fetch_url(url, results_single)
    end = time.perf_counter()
    print("Time taken: ", end - start)

    # -------------- Multi Processing --------------- #
    manager = multiprocessing.Manager()
    results_process = manager.list()   # shared list between processes

    processes = []
    start = time.perf_counter()

    for _ in range(4):
        p = multiprocessing.Process(target=fetch_url, args=(url, results_process, "process"))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    end = time.perf_counter()
    print("Multiprocessing time:", end - start)

    print("\nResults (threads):", list(results_thread))
    print("Results (single):", results_single)
    print("Results (processes):", list(results_process))

if __name__ == "__main__":
    main()