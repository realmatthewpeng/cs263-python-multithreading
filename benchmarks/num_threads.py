import argparse
import multiprocessing
import sys
import threading
import time

def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)
    
def warmup():
    res = fibonacci(25)
    print("Warmup = " + str(res))

def single_threaded(vals):
    results = []

    start = time.perf_counter()
    for v in vals:
        results.append(fibonacci(v))
    end = time.perf_counter()
    execution_time = end - start

    return results, execution_time

def multi_threaded(vals, num_threads):
    results = [None] * len(vals)

    start = time.perf_counter()
    def worker(idx):
        for i in range(idx, len(results), num_threads):
            results[i] = fibonacci(vals[i])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()
    end = time.perf_counter()
    execution_time = end - start

    return results, execution_time

def multi_processed(vals, num_procs):
    start = time.perf_counter()
    with multiprocessing.Pool(processes=num_procs) as pool:
        results = pool.map(fibonacci, vals)

    end = time.perf_counter()
    execution_time = end - start

    return results, execution_time
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fibonacci benchmark comparing single-threaded, multi-threaded, and multi-process execution")
    parser.add_argument("--vals", type=int, nargs="+", default=[26, 27, 28, 29, 30, 31, 32, 33, 34, 35],
                        help="List of Fibonacci values to compute (default: 26-35)")
    parser.add_argument("--threads", type=int, default=10, help="Number of threads/processes (default: 10)")
    parser.add_argument("--mode", type=str, choices=["single", "threaded", "processed", "all"], default="all",
                        help="Execution mode (default: all)")
    parser.add_argument("--no-warmup", action="store_true", help="Skip warmup")
    args = parser.parse_args()

    # Check GIL status
    try:
        if hasattr(sys, '_is_gil_enabled'):
            gil_status = "DISABLED" if not sys._is_gil_enabled() else "ENABLED"
        else:
            gil_status = "ENABLED"
    except:
        gil_status = "ENABLED"

    print(f"GIL: {gil_status}")

    if not args.no_warmup:
        warmup()

    if args.mode in ("single", "all"):
        res, runtime = single_threaded(args.vals)
        print(f"Single-threaded results: {res} (runtime: {runtime:.6f} seconds)")

    if args.mode in ("threaded", "all"):
        res, runtime = multi_threaded(args.vals, args.threads)
        print(f"{args.threads}-threaded results: {res} (runtime: {runtime:.6f} seconds)")

    if args.mode in ("processed", "all"):
        res, runtime = multi_processed(args.vals, args.threads)
        print(f"{args.threads}-processed results: {res} (runtime: {runtime:.6f} seconds)")

    # Results: 
    # vals = [26,27,28,29,30,31,32,33,34,35]
    # Python 3.13t (GIL Disabled)
    # No threads: 10.98 s
    # 1 thread:   10.49 s
    # 2 thread:   6.63  s
    # 3 thread:   5.43  s
    # 4 thread:   5.42  s
    # 5 thread:   4.40  s
    # 10 thread:  4.22  s
    # Python 3.13 (GIL Enabled)
    # No threads: 6.54  s
    # 1 thread:   6.55  s
    # 2 thread:   6.61  s
    # 3 thread:   6.64  s
    # 4 thread:   6.61  s
    # 5 thread:   6.62  s
    # 10 thread:  6.64  s
