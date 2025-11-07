import hashlib
import http.server
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

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


def write_files(base_dir, num_files=10, size_mb=64):
    """Create num_files files of size size_mb in base_dir and return their names."""
    names = []
    chunk = b"A" * 1024 * 1024
    for i in range(num_files):
        name = f"file_{i}.bin"
        path = os.path.join(base_dir, name)
        with open(path, "wb") as f:
            for _ in range(size_mb):
                f.write(chunk)
        names.append(name)
    return names


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def fetch_url(url, timeout=20):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        data = r.read()
    return sha256_bytes(data)

@perf_timer
def serial_fetch(urls):
    return [fetch_url(u) for u in urls]


@perf_timer
def threaded_fetch(urls, num_threads=4):
    results = [None] * len(urls)

    def worker(idx):
        for i in range(idx, len(urls), num_threads):
            results[i] = fetch_url(urls[i])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


@perf_timer
def executor_fetch(urls, num_workers=4):
    with ThreadPoolExecutor(max_workers=num_workers) as ex:
        return list(ex.map(fetch_url, urls))


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

class ThreadingHTTPServerWithQueue(http.server.ThreadingHTTPServer):
    request_queue_size = 128

def start_server(directory, port, backlog=None):
    handler_class = _SilentHandler

    os.chdir(directory)

    if backlog is not None:
        class _CustomQueueServer(http.server.ThreadingHTTPServer):
            request_queue_size = int(backlog)

        server_cls = _CustomQueueServer
    else:
        server_cls = ThreadingHTTPServerWithQueue

    server = server_cls(("127.0.0.1", port), handler_class)

    # Run server in background thread
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    return server, thread


if __name__ == "__main__":

    print("GIL is enabled: " + str(sys._is_gil_enabled()))

    NUM_FILES = 12
    SIZE_MB = 16
    THREADS = 8

    tmpdir = tempfile.mkdtemp(prefix="web_bench_")
    names = write_files(tmpdir, num_files=NUM_FILES, size_mb=SIZE_MB)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    _, port = s.getsockname()
    s.close()

    server, thread = start_server(tmpdir, port)
    urls = [f"http://127.0.0.1:{port}/{name}" for name in names]
    print(f"Started local server on port {port}, serving {len(names)} files from {tmpdir}")

    try:
        s = serial_fetch(urls)
        t = threaded_fetch(urls, num_threads=THREADS)
        e = executor_fetch(urls, num_workers=THREADS)

        ok = s == t == e
        print(f"Checksums match across methods: {ok}")
    finally:
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            pass
        for name in names:
            try:
                os.remove(os.path.join(tmpdir, name))
            except Exception:
                pass
        try:
            os.rmdir(tmpdir)
        except Exception:
            pass


    # Results
    # NUM_FILES = 12
    # SIZE_MB = 16
    # THREADS = 4
    # Python 3.13t (GIL Disabled)
    # serial:     avg  0.5666 s
    # threaded:   avg  0.2294 s
    # executor:   avg  0.2374 s
    # Python 3.13 (GIL Enabled)
    # serial:     avg  0.5862 s
    # threaded:   avg  0.2701 s
    # executor:   avg  0.2693 s

    # NUM_FILES = 12
    # SIZE_MB = 16
    # THREADS = 2
    # Python 3.13t (GIL Disabled)
    # serial:     avg  0.5855 s
    # threaded:   avg  0.3464 s
    # executor:   avg  0.3661 s
    # Python 3.13 (GIL Enabled)
    # serial:     avg  0.6007 s
    # threaded:   avg  0.3810 s
    # executor:   avg  0.3712 s

    # NUM_FILES = 12
    # SIZE_MB = 16
    # THREADS = 8
    # Python 3.13t (GIL Disabled)
    # serial:     avg  0.5890 s
    # threaded:   avg  0.2037 s
    # executor:   avg  0.2178 s
    # Python 3.13 (GIL Enabled)
    # serial:     avg  0.5690 s
    # threaded:   avg  0.2276 s
    # executor:   avg  0.2238 s
