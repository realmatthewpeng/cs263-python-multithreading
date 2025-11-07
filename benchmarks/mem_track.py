import psutil
import os
import tracemalloc
import threading
import time
import sys


class MemTracker:
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.samples = []

    def get_curr_mem(self):
        """Get current memory stats"""
        mem = self.process.memory_info()
        return {
            "rss_mb": mem.rss / 1024**2,
            "vss_mb": mem.vms / 1024**2,
            "timestamp": time.time(),
        }

    def track(self, duration, interval=0.1):
        """Track memory over time"""
        start = time.time()
        while time.time() - start < duration:
            self.samples.append(self.get_curr_mem())
            time.sleep(interval)
        return self.samples


def test_thread_local_mem(num_threads):
    """Each thread allocates its own large data structure"""
    """
    Hypothesis: 

    When multiple threads allocate local memory, GIL handles memory
    management efficiently as allocations are packed tightly (with no mem overhead)
    With GIL turned OFF, there is higher overhead per thread. To avoid lock contention,
    Python creates memory arenas for each thread, leading to memory overhead.

    Results:
    GIL: DISABLED
    Number of threads: 8
    {'baseline_mb': 17.890625, 'peak_mb': 99.65625, 'overhead_mb': 81.765625, 'per_thread_mb': 10.220703125}

    GIL: ENABLED
    Number of threads: 8
    {'baseline_mb': 18.046875, 'peak_mb': 99.5625, 'overhead_mb': 81.515625, 'per_thread_mb': 10.189453125}

    Virtually the same...

    TODO: Explain the results
    """

    def allocate_local(barrier):
        # Each thread gets its own 10MB of data
        local_data = [0] * (10 * 1024 * 1024 // 8)
        # Hold the memory
        time.sleep(2)

    tracker = MemTracker()
    baseline = tracker.get_curr_mem()["rss_mb"]

    barrier = threading.Barrier(num_threads)

    threads = [
        threading.Thread(target=allocate_local, args=(barrier,))
        for _ in range(num_threads)
    ]

    for t in threads:
        t.start()

    time.sleep(2)
    peak = tracker.get_curr_mem()["rss_mb"]

    for t in threads:
        t.join()

    return {
        "baseline_mb": baseline,
        "peak_mb": peak,
        "overhead_mb": peak - baseline,
        "per_thread_mb": (peak - baseline) / num_threads,
    }


def test_shared_mem(num_threads):
    """All threads share one large data structure"""

    """
    Hypothesis:

    With GIL ON or OFF, the memory overhead difference should be small.
    The only memory difference is caused by thread bookkeeping/stack memory
    for each thread.
    """

    # Single shared 50MB array
    shared_data = [0] * (50 * 1024 * 1024 // 8)

    def access_shared():
        for i in range(1000000):
            _ = shared_data[i % len(shared_data)]

    tracker = MemTracker()
    baseline = tracker.get_curr_mem()["rss_mb"]

    threads = [threading.Thread(target=access_shared) for _ in range(num_threads)]

    for t in threads:
        t.start()

    time.sleep(0.5)
    peak = tracker.get_curr_mem()["rss_mb"]

    for t in threads:
        t.join()

    return {"baseline_mb": baseline, "peak_mb": peak, "overhead_mb": peak - baseline}


def test_fragmentation(num_threads, duration=10):
    """
    Track memory patterns to detect fragmentation
    Threads continuously allocate and deallocate memory over a certain duration of time.

    TODO: Finish displaying metrics
    """

    def allocate_and_free():
        while not stop_flag:
            data = [list(range(1000)) for _ in range(100)]
            del data
            time.sleep(0.01)

    stop_flag = False
    tracker = MemTracker()

    # Start tracking in background
    track_thread = threading.Thread(target=lambda: tracker.track(duration))
    track_thread.start()

    # Start worker threads
    threads = [threading.Thread(target=allocate_and_free) for _ in range(num_threads)]
    for t in threads:
        t.start()

    time.sleep(duration)
    stop_flag = True

    for t in threads:
        t.join()
    track_thread.join()

    return tracker.samples


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--test", type=int)
    args = parser.parse_args()

    try:
        if hasattr(sys, "_is_gil_enabled"):
            gil_status = "DISABLED" if not sys._is_gil_enabled() else "ENABLED"
        else:
            gil_status = "ENABLED"
    except:
        gil_status = "ENABLED"

    print(f"GIL: {gil_status}")

    NUM_THREADS = 8
    print(f"Number of threads: {NUM_THREADS}")

    if args.test == 1:
        res = test_thread_local_mem(NUM_THREADS)
        print(res)
    if args.test == 2:
        res = test_shared_mem(NUM_THREADS)
        print(res)
    if args.test == 3:
        res = test_fragmentation(NUM_THREADS)
        print(res)


if __name__ == "__main__":
    main()
