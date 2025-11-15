import time
import threading
import argparse
import sys
import tracemalloc
import concurrent.futures
import multiprocessing

MEM_TRACK = False

def perf_timer(func):
    def wrapper(*args, **kwargs):
        # warmup
        _ = func(*args, **kwargs)

        def fmt_bytes(n):
            for unit in ("B", "KiB", "MiB"):
                if abs(n) < 1024.0:
                    return f"{n:3.1f}{unit}"
                n /= 1024.0
            return f"{n:.1f}GiB"

        times = []
        tracemalloc_peaks = []

        for _ in range(5):
            if MEM_TRACK:
                tracemalloc.start()

            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()

            if MEM_TRACK:
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc_peaks.append(peak)
                tracemalloc.stop()

            times.append(end - start)

        avg_time = sum(times) / len(times)
        if MEM_TRACK:
            avg_peak = sum(tracemalloc_peaks) / len(tracemalloc_peaks)
            print(f"{func.__name__}: avg time: {avg_time:.6f}s, avg tracemalloc peak: {fmt_bytes(avg_peak)}")
        else:
            print(f"{func.__name__}: avg time: {avg_time:.6f}s")

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

def run_sweep(thread_counts, iterations, selected):
    print(f"sys._is_gil_enabled: {getattr(sys, '_is_gil_enabled', lambda: True)()}")
    print(f"Iterations per case: {iterations}")
    for n in thread_counts:
        print("\n---")
        print(f"Threads: {n}")
        if selected == -1:
            # Threads
            _ = repeated_creation(n, iterations)
            _ = batched_creation(n, iterations)
            _ = threadpool_creation_per_iteration(n, iterations)
            _ = threadpool_creation_reuse(n, iterations)
            # Processes
            if iterations <= 20 and n <= 16:
                _ = process_creation(n, iterations)
                _ = process_pool_per_iteration(n, iterations)
                _ = process_pool_reuse(n, iterations)
        else:
            if selected == 0:
                _ = repeated_creation(n, iterations)
            elif selected == 1:
                _ = batched_creation(n, iterations)
            elif selected == 2:
                _ = threadpool_creation_per_iteration(n, iterations)
            elif selected == 3:
                _ = threadpool_creation_reuse(n, iterations)
            elif selected == 4:
                if iterations <= 20 and n <= 16:
                    _ = process_creation(n, iterations)
            elif selected == 5:
                if iterations <= 20 and n <= 16:
                    _ = process_pool_per_iteration(n, iterations)
            elif selected == 6:
                if iterations <= 20 and n <= 16:
                    _ = process_pool_reuse(n, iterations)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--threads", type=int, nargs="+", default=[1,2,4,8,16])
    p.add_argument("--iters", type=int, default=20, help="iterations per case")
    p.add_argument("--mem", action="store_true", help="enable tracemalloc memory tracking")
    p.add_argument("--selected", type=int, default=-1, help="select test to run")
    args = p.parse_args()

    global MEM_TRACK
    MEM_TRACK = bool(args.mem)

    run_sweep(args.threads, args.iters, args.selected)

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
"""
sys._is_gil_enabled: False
Iterations per case: 20

---
Threads: 1
repeated_creation: avg time: 0.008348s, avg tracemalloc peak: 30.7KiB
batched_creation: avg time: 0.007777s, avg tracemalloc peak: 30.6KiB
threadpool_creation_per_iteration: avg time: 0.009667s, avg tracemalloc peak: 37.1KiB
threadpool_creation_reuse: avg time: 0.003069s, avg tracemalloc peak: 28.3KiB
process_creation: avg time: 1.844444s, avg tracemalloc peak: 22.3KiB
process_pool_per_iteration: avg time: 2.046322s, avg tracemalloc peak: 106.2KiB
process_pool_reuse: avg time: 0.133541s, avg tracemalloc peak: 94.7KiB

---
Threads: 2
repeated_creation: avg time: 0.011297s, avg tracemalloc peak: 50.1KiB
batched_creation: avg time: 0.011192s, avg tracemalloc peak: 50.1KiB
threadpool_creation_per_iteration: avg time: 0.018725s, avg tracemalloc peak: 60.5KiB
threadpool_creation_reuse: avg time: 0.007848s, avg tracemalloc peak: 54.8KiB
process_creation: avg time: 1.984419s, avg tracemalloc peak: 21.8KiB
process_pool_per_iteration: avg time: 2.075423s, avg tracemalloc peak: 107.4KiB
process_pool_reuse: avg time: 0.146437s, avg tracemalloc peak: 99.5KiB

---
Threads: 4
repeated_creation: avg time: 0.018406s, avg tracemalloc peak: 58.0KiB
batched_creation: avg time: 0.018221s, avg tracemalloc peak: 71.6KiB
threadpool_creation_per_iteration: avg time: 0.023741s, avg tracemalloc peak: 67.6KiB
threadpool_creation_reuse: avg time: 0.013771s, avg tracemalloc peak: 59.9KiB
process_creation: avg time: 2.554339s, avg tracemalloc peak: 24.5KiB
process_pool_per_iteration: avg time: 2.435790s, avg tracemalloc peak: 115.8KiB
process_pool_reuse: avg time: 0.205671s, avg tracemalloc peak: 107.4KiB

---
Threads: 8
repeated_creation: avg time: 0.033498s, avg tracemalloc peak: 65.8KiB
batched_creation: avg time: 0.026970s, avg tracemalloc peak: 81.1KiB
threadpool_creation_per_iteration: avg time: 0.035963s, avg tracemalloc peak: 89.4KiB
threadpool_creation_reuse: avg time: 0.026635s, avg tracemalloc peak: 87.2KiB
process_creation: avg time: 3.592431s, avg tracemalloc peak: 30.1KiB
process_pool_per_iteration: avg time: 2.984038s, avg tracemalloc peak: 134.8KiB
process_pool_reuse: avg time: 0.312884s, avg tracemalloc peak: 127.3KiB

---
Threads: 16
repeated_creation: avg time: 0.060181s, avg tracemalloc peak: 81.6KiB
batched_creation: avg time: 0.051786s, avg tracemalloc peak: 97.0KiB
threadpool_creation_per_iteration: avg time: 0.060377s, avg tracemalloc peak: 112.6KiB
threadpool_creation_reuse: avg time: 0.051786s, avg tracemalloc peak: 110.6KiB
process_creation: avg time: 6.321749s, avg tracemalloc peak: 41.5KiB
process_pool_per_iteration: avg time: 3.958548s, avg tracemalloc peak: 171.7KiB
process_pool_reuse: avg time: 0.574221s, avg tracemalloc peak: 165.1KiB
"""