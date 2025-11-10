import argparse
import time
import threading
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

        R_multi = multithread_matmul(A, B, num_threads=args.threads)

        equal = np.allclose(R_single, R_multi, rtol=1e-5, atol=1e-8)
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
        R_multi = multithread_matmul_pure(A, B, num_threads=args.threads)

        def approx_equal(L1, L2, rel=1e-6, abs_tol=1e-8):
            for i in range(len(L1)):
                row1 = L1[i]
                row2 = L2[i]
                for j in range(len(row1)):
                    if not math.isclose(row1[j], row2[j], rel_tol=rel, abs_tol=abs_tol):
                        return False
            return True

        equal = approx_equal(R_single, R_multi)
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