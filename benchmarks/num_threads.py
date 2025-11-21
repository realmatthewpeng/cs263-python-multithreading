import threading
import multiprocessing
import sys
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

    # Check GIL status
    try:
        if hasattr(sys, '_is_gil_enabled'):
            gil_status = "DISABLED" if not sys._is_gil_enabled() else "ENABLED"
        else:
            gil_status = "ENABLED"
    except:
        gil_status = "ENABLED"

    print(f"GIL: {gil_status}")

    warmup()

    vals = [26,27,28,29,30,31,32,33,34,35]

    #res, runtime = single_threaded(vals)
    #print(f"Single-threaded results: {res} (runtime: {runtime:.6f} seconds)")

    num_threads = 10
    res, runtime = multi_threaded(vals, num_threads)    
    print(f"{num_threads}-threaded results: {res} (runtime: {runtime:.6f} seconds)")

    res, runtime = multi_processed(vals, num_threads)    
    print(f"{num_threads}-processed results: {res} (runtime: {runtime:.6f} seconds)")

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
