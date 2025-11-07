import os
import sys
import tempfile
import threading
import time
import hashlib

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

def write_temp_files(base_dir, num_files=8, size_mb=5):
    """Create num_files files of size size_mb in base_dir. Return list of paths."""
    paths = []
    chunk = b"0" * 1024 * 1024  # 1 MB chunk
    for i in range(num_files):
        p = os.path.join(base_dir, f"io_test_{i}.bin")
        with open(p, "wb") as f:
            for _ in range(size_mb):
                f.write(chunk)
        paths.append(p)
    return paths

def checksum_file(path):
    """Read file and compute SHA256 checksum."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(1024 * 1024)
            if not data:
                break
            h.update(data)
    return h.hexdigest()

@perf_timer
def serial_read(paths):
    checks = []
    for p in paths:
        checks.append(checksum_file(p))
    return checks

@perf_timer
def threaded_read(paths, num_threads=4):
    checks = [None] * len(paths)

    def worker(idx):
        for i in range(idx, len(paths), num_threads):
            checks[i] = checksum_file(paths[i])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return checks

def cleanup(paths, base_dir):
    for p in paths:
        try:
            os.remove(p)
        except Exception:
            pass
    try:
        os.rmdir(base_dir)
    except Exception:
        pass

if __name__ == "__main__":

    print("GIL is enabled: " + str(sys._is_gil_enabled()))

    tmpdir = tempfile.mkdtemp(prefix="io_bench_")
    print(f"Temp dir: {tmpdir}")

    NUM_FILES = 12
    SIZE_MB = 16
    THREADS = 8

    print(f"Creating {NUM_FILES} files of {SIZE_MB} MB each (total ~{NUM_FILES*SIZE_MB} MB)...")
    paths = write_temp_files(tmpdir, num_files=NUM_FILES, size_mb=SIZE_MB)

    serial = serial_read(paths)
    threaded = threaded_read(paths, num_threads=THREADS)

    ok = serial == threaded
    print(f"Checksums match across methods: {ok}")

    cleanup(paths, tmpdir)

    # Results
    # NUM_FILES = 12
    # SIZE_MB = 16
    # THREADS = 4
    # Python 3.13t (GIL Disabled)
    # serial_read:   avg   0.4331 s
    # threaded_read: avg   0.1096 s
    # Python 3.13 (GIL Enabled)
    # serial_read:   avg   0.4041 s
    # threaded_read: avg   0.1228 s

    # NUM_FILES = 12
    # SIZE_MB = 16
    # THREADS = 2
    # Python 3.13t (GIL Disabled)
    # serial_read:   avg   0.4315 s
    # threaded_read: avg   0.2301 s
    # Python 3.13 (GIL Enabled)
    # serial_read:   avg   0.4462 s
    # threaded_read: avg   0.2098 s

    # NUM_FILES = 12
    # SIZE_MB = 16
    # THREADS = 8
    # Python 3.13t (GIL Disabled)
    # serial_read:   avg   0.4433 s
    # threaded_read: avg   0.0814 s
    # Python 3.13 (GIL Enabled)
    # serial_read:   avg   0.4292 s
    # threaded_read: avg   0.0815 s