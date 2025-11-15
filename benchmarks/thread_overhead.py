import time
import threading
import argparse
import sys
import concurrent.futures
import multiprocessing

def perf_timer(func):
    def wrapper(*args, **kwargs):
        # warmup
        _ = func(*args, **kwargs)

        times = []
        for _ in range(5):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)

        print(f"{func.__name__}: avg: {sum(times)/len(times):.6f}s")
        return result

    return wrapper

def _noop():
    # trivial worker
    x = 1
    x += 1

@perf_timer
def repeated_creation(num_threads: int, iterations: int):
    """
    Create and start thread immediately.
    """
    for _ in range(iterations):
        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=_noop)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
    return True

@perf_timer
def batched_creation(num_threads: int, iterations: int):
    """
    Create threads and start them in batch.
    """
    for _ in range(iterations):
        threads = [threading.Thread(target=_noop) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    return True


@perf_timer
def threadpool_creation_per_iteration(num_threads: int, iterations: int):
    """
    Create a ThreadPoolExecutor each iteration.
    """
    for _ in range(iterations):
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as ex:
            futures = [ex.submit(_noop) for _ in range(num_threads)]
            for f in futures:
                f.result()
    return True


@perf_timer
def threadpool_creation_reuse(num_threads: int, iterations: int):
    """
    Create one ThreadPoolExecutor and reuse it across iterations.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as ex:
        for _ in range(iterations):
            futures = [ex.submit(_noop) for _ in range(num_threads)]
            for f in futures:
                f.result()
    return True


@perf_timer
def process_creation(num_procs: int, iterations: int):
    """
    Create and start processes immediately.
    """
    ctx = multiprocessing.get_context()
    for _ in range(iterations):
        procs = []
        for _ in range(num_procs):
            p = ctx.Process(target=_noop)
            p.start()
            procs.append(p)
        for p in procs:
            p.join()
    return True


@perf_timer
def process_pool_per_iteration(num_procs: int, iterations: int):
    """
    Create a multiprocessing.Pool each iteration.
    """
    for _ in range(iterations):
        with multiprocessing.Pool(processes=num_procs) as pool:
            results = [pool.apply_async(_noop) for _ in range(num_procs)]
            for r in results:
                r.get()
    return True


@perf_timer
def process_pool_reuse(num_procs: int, iterations: int):
    """
    Create one multiprocessing.Pool and reuse it across iterations.
    """
    with multiprocessing.Pool(processes=num_procs) as pool:
        for _ in range(iterations):
            results = [pool.apply_async(_noop) for _ in range(num_procs)]
            for r in results:
                r.get()
    return True

def run_sweep(thread_counts, iterations):
    print(f"sys._is_gil_enabled: {getattr(sys, '_is_gil_enabled', lambda: True)()}")
    print(f"Iterations per case: {iterations}")
    for n in thread_counts:
        print("\n---")
        print(f"Threads: {n}")
        # Threads
        _ = repeated_creation(n, iterations)
        _ = batched_creation(n, iterations)
        _ = threadpool_creation_per_iteration(n, iterations)
        _ = threadpool_creation_reuse(n, iterations)
        # Processes
        if iterations <= 20 or n <= 16:
            _ = process_creation(n, iterations)
            _ = process_pool_per_iteration(n, iterations)
            _ = process_pool_reuse(n, iterations)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--threads", type=int, nargs="+", default=[1,2,4,8,16])
    p.add_argument("--iters", type=int, default=20, help="iterations per case")
    args = p.parse_args()

    run_sweep(args.threads, args.iters)

if __name__ == "__main__":
    main()

"""
sys._is_gil_enabled: False
Iterations per case: 20
---
Threads: 1
repeated_creation: avg: 0.006674s
batched_creation: avg: 0.006798s
threadpool_creation_per_iteration: avg: 0.005047s
threadpool_creation_reuse: avg: 0.000833s
process_creation: avg: 1.960757s
process_pool_per_iteration: avg: 1.848846s
process_pool_reuse: avg: 0.095201s

---
Threads: 2
repeated_creation: avg: 0.007451s
batched_creation: avg: 0.008065s
threadpool_creation_per_iteration: avg: 0.012073s
threadpool_creation_reuse: avg: 0.000873s
process_creation: avg: 1.991110s
process_pool_per_iteration: avg: 2.001669s
process_pool_reuse: avg: 0.102081s

---
Threads: 4
repeated_creation: avg: 0.011005s
batched_creation: avg: 0.012131s
threadpool_creation_per_iteration: avg: 0.008246s
threadpool_creation_reuse: avg: 0.001561s
process_creation: avg: 2.492631s
process_pool_per_iteration: avg: 2.302554s
process_pool_reuse: avg: 0.123228s

---
Threads: 8
repeated_creation: avg: 0.016081s
batched_creation: avg: 0.015093s
threadpool_creation_per_iteration: avg: 0.013352s
threadpool_creation_reuse: avg: 0.002466s
process_creation: avg: 3.558393s
process_pool_per_iteration: avg: 2.903618s
process_pool_reuse: avg: 0.156297s

---
Threads: 16
repeated_creation: avg: 0.026639s
batched_creation: avg: 0.025502s
threadpool_creation_per_iteration: avg: 0.015133s
threadpool_creation_reuse: avg: 0.004016s
process_creation: avg: 6.483938s
process_pool_per_iteration: avg: 4.033022s
process_pool_reuse: avg: 0.211894s
"""