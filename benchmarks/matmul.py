import threading
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
def threaded_np_matmul(matrices):
    results = [None] * 5

    def worker(idx):
        results[idx] = np.dot(matrices[idx*2], matrices[idx*2+1])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return results

@perf_timer
def threaded_matmul(matrices):
    results = [None] * 5

    def worker(idx):
        results[idx] = no_np_matmul(matrices[idx*2], matrices[idx*2+1])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return results

@perf_timer
def serial_np_matmul(matrices):
    results = []

    for i in range(0,5,2):
        results.append(np.dot(matrices[i], matrices[i+1]))

    return results

@perf_timer
def serial_matmul(matrices):
    results = []

    for i in range(0,5,2):
        results.append(no_np_matmul(matrices[i], matrices[i+1]))

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

np.random.seed(42)

print("GIL is enabled: " + str(sys._is_gil_enabled()))

size = 100

matrices = []
for _ in range(10):
    matrices.append(np.random.rand(size, size))

threaded_np_matmul(matrices)
threaded_matmul(matrices)

serial_np_matmul(matrices)
serial_matmul(matrices)