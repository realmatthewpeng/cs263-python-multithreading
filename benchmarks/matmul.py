import threading
import multiprocessing
import numpy as np
import sys
import time

# Using Python 3.13

def perf_timer(func):
    def wrapper(*args, **kwargs):

        # Warm up runs
        # Not sure if neccessary
        for _ in range(0,2):
            _ = func(*args, **kwargs)

        times = []

        for _ in range(0,5):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            times.append(execution_time)

        print(times)
        print(f"Function {func.__name__!r} took average {sum(times)/len(times):.4f} seconds to execute.")
        return result
    
    return wrapper

@perf_timer
def threaded_np_matmul(matrices, num_threads):
    results = [None] * (len(matrices)//2)

    def worker(idx):
        for i in range(idx, len(results), num_threads):
            results[i] = np.dot(matrices[i*2], matrices[i*2+1])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return results

@perf_timer
def threaded_matmul(matrices, num_threads):
    results = [None] * (len(matrices)//2)

    def worker(idx):
        for i in range(idx, len(results), num_threads):
            # print(f"Thread {idx} processing index {i}")
            results[i] = no_np_matmul(matrices[i*2], matrices[i*2+1])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return results

@perf_timer
def serial_np_matmul(matrices):
    results = []

    for i in range(0,len(matrices),2):
        results.append(np.dot(matrices[i], matrices[i+1]))

    return results

@perf_timer
def serial_matmul(matrices):
    results = []

    for i in range(0,len(matrices),2):
        results.append(no_np_matmul(matrices[i], matrices[i+1]))

    return results

@perf_timer
def process_pool_np_matmul(matrices, num_procs):
    pairs = [(matrices[i], matrices[i+1]) for i in range(0, len(matrices), 2)]
    with multiprocessing.Pool(processes=num_procs) as pool:
        results = pool.starmap(np.dot, pairs)
    return results

@perf_timer
def process_pool_matmul(matrices, num_procs):
    pairs = [(matrices[i], matrices[i+1]) for i in range(0, len(matrices), 2)]
    with multiprocessing.Pool(processes=num_procs) as pool:
        results = pool.starmap(no_np_matmul, pairs)
    return results

def no_np_matmul(A, B):

    # Assume square matrices of same size
    rows = len(A)
    cols = len(A[0])

    result = [[0 for _ in range(cols)] for _ in range(rows)]

    for i in range(rows):
        for j in range(cols):
            for k in range(cols):
                result[i][j] += A[i][k] * B[k][j]

    return result

def check_res(res, matrices):

    for i in range(0,len(matrices),2):
        expected = np.dot(matrices[i], matrices[i+1])
        if not np.all(np.isclose(expected, res[i//2])):
            return False

    return True


if __name__ == "__main__":
    np.random.seed(42)

    print("GIL is enabled: " + str(sys._is_gil_enabled()))

    size = 100
    num_threads = 5

    matrices = []
    for _ in range(20):
        matrices.append(np.random.rand(size, size))

    res = threaded_np_matmul(matrices, num_threads)
    # res = threaded_matmul(matrices, num_threads)

    # res = serial_np_matmul(matrices)
    # res = serial_matmul(matrices)

    # res = process_pool_np_matmul(matrices, num_threads)
    # res = process_pool_matmul(matrices, num_threads)

    print(f"Check Res returned {check_res(res, matrices)}")

    # Results
    # 10 random 100x100 matmul
    # Python 3.13t (GIL Disabled)
    # threaded_np_matmul, 5 threads: 0.0013 s
    # threaded_matmul, 5 threads:    2.3115 s
    # process_np_matmul, 5 processes: 0.2317 s
    # process_matmul, 5 processes:    1.6699 s
    # serial_np_matmul:              0.0009 s
    # serial_matmul:                 9.6155 s
    # Python 3.13 (GIL Enabled)
    # threaded_np_matmul, 5 threads: 0.0012 s
    # threaded_matmul, 5 threads:    8.0204 s
    # serial_np_matmul:              0.0009 s
    # serial_matmul:                 8.0039 s
    # process_np_matmul, 5 processes: 0.1454 s
    # process_matmul, 5 processes:    1.2957 s
