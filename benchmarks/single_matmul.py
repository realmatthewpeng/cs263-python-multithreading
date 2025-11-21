import argparse
import time
import threading
import multiprocessing
from multiprocessing import shared_memory
import random
import math
import numpy as np


def perf_timer(func):
    def wrapper(*args, **kwargs):
        # warmup
        _ = func(*args, **kwargs)

        times = []
        for _ in range(3):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)

        print(f"{func.__name__}: runs: {times}, avg: {sum(times)/len(times):.4f}s")
        return result

    return wrapper


@perf_timer
def single_thread_matmul(A, B):
    return np.dot(A, B)


@perf_timer
def single_thread_matmul_pure(A, B):
    n = len(A)
    m = len(B[0])
    p = len(B)

    R = [[0.0] * m for _ in range(n)]

    for i in range(n):
        ai = A[i]
        ri = R[i]
        for k in range(p):
            aik = ai[k]
            bk = B[k]
            for j in range(m):
                ri[j] += aik * bk[j]

    return R


# The multithreaded worker computes R[start:end, :] = A[start:end, :] @ B
@perf_timer
def multithread_matmul(A, B, num_threads=4):
    n_rows = A.shape[0]
    R = np.empty((n_rows, B.shape[1]), dtype=A.dtype)

    def worker(start, end):
        R[start:end, :] = A[start:end, :].dot(B)

    chunk_size = (n_rows + num_threads - 1) // num_threads
    threads = []
    for i in range(num_threads):
        start = i * chunk_size
        if start >= n_rows:
            break
        end = min((i + 1) * chunk_size, n_rows)
        t = threading.Thread(target=worker, args=(start, end))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return R


# The multithreaded worker computes R[start:end, :] = A[start:end, :] @ B
@perf_timer
def multithread_matmul_pure(A, B, num_threads=4):
    #  A and B are lists of lists.
    n = len(A)
    m = len(B[0])
    p = len(B)

    R = [[0.0] * m for _ in range(n)]

    def worker(start, end):
        for i in range(start, end):
            ai = A[i]
            ri = R[i]
            for k in range(p):
                aik = ai[k]
                bk = B[k]
                for j in range(m):
                    ri[j] += aik * bk[j]

    chunk_size = (n + num_threads - 1) // num_threads
    threads = []
    for t_idx in range(num_threads):
        start = t_idx * chunk_size
        if start >= n:
            break
        end = min((t_idx + 1) * chunk_size, n)
        t = threading.Thread(target=worker, args=(start, end))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return R


def _proc_np_worker(a_slice, B, start):
    return (start, a_slice.dot(B))


def _proc_pure_worker(a_rows, B, start):
    m = len(B[0])
    p = len(B)
    result_rows = [[0.0] * m for _ in range(len(a_rows))]
    for ri, ai in enumerate(a_rows):
        for k in range(p):
            aik = ai[k]
            bk = B[k]
            row_out = result_rows[ri]
            for j in range(m):
                row_out[j] += aik * bk[j]
    return (start, result_rows)


@perf_timer
def multiprocess_matmul(A, B, num_processes=4):
    n_rows = A.shape[0]
    R = np.empty((n_rows, B.shape[1]), dtype=A.dtype)

    chunk_size = (n_rows + num_processes - 1) // num_processes
    tasks = []
    for i in range(num_processes):
        start = i * chunk_size
        if start >= n_rows:
            break
        end = min((i + 1) * chunk_size, n_rows)
        tasks.append((A[start:end, :], B, start))

    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(_proc_np_worker, tasks)

    for start, chunk in results:
        R[start:start + chunk.shape[0], :] = chunk

    return R


@perf_timer
def multiprocess_matmul_pure(A, B, num_processes=4):
    n = len(A)
    R = [[0.0] * len(B[0]) for _ in range(n)]

    chunk_size = (n + num_processes - 1) // num_processes
    tasks = []
    for i in range(num_processes):
        start = i * chunk_size
        if start >= n:
            break
        end = min((i + 1) * chunk_size, n)
        tasks.append((A[start:end], B, start))

    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(_proc_pure_worker, tasks)

    for start, chunk_rows in results:
        for i, row in enumerate(chunk_rows):
            R[start + i] = row

    return R


# Shared-memory NumPy multiprocess implementation to avoid copying large A/B
GLOBAL_A = None
GLOBAL_B = None
# Shared memory handles need to be global so they don't get GC'd
# https://stackoverflow.com/questions/79787708/python-multiprocessing-shared-memory-seems-to-hang-or-crash-when-interacting-wit
shm_a = None
shm_b = None


def _init_shared_shm(name_a, shape_a, name_b, shape_b, dtype):
    global GLOBAL_A, GLOBAL_B, shm_a, shm_b
    shm_a = shared_memory.SharedMemory(name=name_a)
    shm_b = shared_memory.SharedMemory(name=name_b)
    GLOBAL_A = np.ndarray(shape_a, dtype=dtype, buffer=shm_a.buf)
    GLOBAL_B = np.ndarray(shape_b, dtype=dtype, buffer=shm_b.buf)


def _shared_np_worker_range(args):
    start, end = args
    chunk = GLOBAL_A[start:end, :].dot(GLOBAL_B)
    return (start, chunk)


@perf_timer
def multiprocess_matmul_shared(A, B, num_processes=4):
    n_rows = A.shape[0]
    R = np.empty((n_rows, B.shape[1]), dtype=A.dtype)

    global shm_a, shm_b
    # create shared memory blocks and copy A, B into them
    shm_a = shared_memory.SharedMemory(create=True, size=A.nbytes)
    shm_b = shared_memory.SharedMemory(create=True, size=B.nbytes)

    a_shm_arr = np.ndarray(A.shape, dtype=A.dtype, buffer=shm_a.buf)
    b_shm_arr = np.ndarray(B.shape, dtype=B.dtype, buffer=shm_b.buf)

    a_shm_arr[:] = A[:]
    b_shm_arr[:] = B[:]

    chunk_size = (n_rows + num_processes - 1) // num_processes
    tasks = []
    for i in range(num_processes):
        start = i * chunk_size
        if start >= n_rows:
            break
        end = min((i + 1) * chunk_size, n_rows)
        tasks.append((start, end))

    init_args = (shm_a.name, A.shape, shm_b.name, B.shape, A.dtype)
    with multiprocessing.Pool(processes=num_processes, initializer=_init_shared_shm, initargs=init_args) as pool:
        results = pool.map(_shared_np_worker_range, tasks)

    for start, chunk in results:
        R[start:start + chunk.shape[0], :] = chunk

    shm_a.close()
    shm_a.unlink()
    shm_b.close()
    shm_b.unlink()

    return R


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--size", type=int, default=5000, help="matrix size (n for n x n)")
    p.add_argument("--threads", type=int, default=5, help="number of worker threads")
    p.add_argument("--impl", choices=["numpy", "pure"], default="numpy", help="which implementation to run")
    args = p.parse_args()

    n = args.size

    if args.impl == "numpy":
        print(f"Creating two {n}x{n} matrices")
        np.random.seed(42)
        A = np.random.rand(n, n).astype(np.float64)
        B = np.random.rand(n, n).astype(np.float64)

        R_single = single_thread_matmul(A, B)

        #R_multi = multithread_matmul(A, B, num_threads=args.threads)
        #equal = np.allclose(R_single, R_multi, rtol=1e-5, atol=1e-8)

        #R_multi_process = multiprocess_matmul(A, B, num_processes=args.threads)
        #equal = np.allclose(R_single, R_multi_process, rtol=1e-5, atol=1e-8)

        R_multi_process_shared = multiprocess_matmul_shared(A, B, num_processes=args.threads)
        equal = np.allclose(R_single, R_multi_process_shared, rtol=1e-5, atol=1e-8)

        print(f"Results equal: {equal}")
    else:
        if n > 500:
            print("Array size too large for pure-Python implementation; skipping.")
            return

        print(f"Creating two {n}x{n} Python matrices (lists of lists)")
        random.seed(42)
        A = [[random.random() for _ in range(n)] for _ in range(n)]
        B = [[random.random() for _ in range(n)] for _ in range(n)]

        R_single = single_thread_matmul_pure(A, B)

        def approx_equal(L1, L2, rel=1e-6, abs_tol=1e-8):
            for i in range(len(L1)):
                row1 = L1[i]
                row2 = L2[i]
                for j in range(len(row1)):
                    if not math.isclose(row1[j], row2[j], rel_tol=rel, abs_tol=abs_tol):
                        return False
            return True

        #R_multi = multithread_matmul_pure(A, B, num_threads=args.threads)
        #equal = approx_equal(R_single, R_multi)

        R_multi_process = multiprocess_matmul_pure(A, B, num_processes=args.threads)
        equal = approx_equal(R_single, R_multi_process)

        print(f"Results equal: {equal}")


if __name__ == "__main__":
    main()

    # Results

    # Random 300x300 matmul
    # Python 3.13t (GIL Disabled)
    # single_np_matmul:               0.0008 s
    # multi_np_matmul, 5 threads:     0.0013 s
    # single_pure_matmul:             2.4738 s
    # multi_pure_matmul, 5 threads:   0.7267 s
    # Python 3.13 (GIL Enabled)
    # single_np_matmul:               0.0006 s
    # multi_np_matmul, 5 threads:     0.0017 s
    # single_pure_matmul:             1.1675 s
    # multi_pure_matmul, 5 threads:   1.3053 s

    # Random 500x500 matmul
    # Python 3.13t (GIL Disabled)
    # single_pure_matmul:             12.1794 s
    # multi_pure_matmul, 5 threads:   3.8861 s
    # Python 3.13 (GIL Enabled)
    # single_pure_matmul:             6.1270 s
    # multi_pure_matmul, 5 threads:   6.6667 s

    # Random 1000x1000 matmul
    # Python 3.13t (GIL Disabled)
    # single_np_matmul:               0.0132 s
    # multi_np_matmul, 5 threads:     0.0133 s
    # Python 3.13 (GIL Enabled)
    # single_np_matmul:               0.0110 s
    # multi_np_matmul, 5 threads:     0.0122 s

    # Random 5000x5000 matmul
    # Python 3.13t (GIL Disabled)
    # single_np_matmul:               1.2108 s
    # multi_np_matmul, 5 threads:     1.3288 s
    # Python 3.13 (GIL Enabled)
    # single_np_matmul:               1.1373 s
    # multi_np_matmul, 5 threads:     1.3270 s