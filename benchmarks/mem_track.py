import psutil
import os
import threading
import time
import sys
import json


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
    Contrary to the prediction of memory overhead from per-thread areans (GIL OFF), testing shows that Python 3.13's free-threaded implementation maintains nearly identical memory usage with GIL OFF.
    """

    """
    barrier = threading.Barrier(num_threads)

    def allocate_local(barrier):
        local_data = []
        for _ in range(10000):
            local_data.append([0] * 100)
        barrier.wait()
        time.sleep(2)

    tracker = MemTracker()
    baseline = tracker.get_curr_mem()["rss_mb"]

    threads = [
        threading.Thread(target=allocate_local, args=(barrier,))
        for _ in range(num_threads)
    ]

    for t in threads:
        t.start()

    time.sleep(2.5)
    peak = tracker.get_curr_mem()["rss_mb"]

    for t in threads:
        t.join()

    return {
        "baseline_mb": baseline,
        "peak_mb": peak,
        "overhead_mb": peak - baseline,
        "per_thread_mb": (peak - baseline) / num_threads,
    }
    """

    import tracemalloc

    def memory_intensive_task():
        # Your workload here
        data = [list(range(10000)) for _ in range(100)]
        # Process data...

    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    threads = [threading.Thread(target=memory_intensive_task) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    snapshot_after = tracemalloc.take_snapshot()

    top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
    for stat in top_stats[:10]:
        print(stat)


def test_shared_mem(num_threads):
    """All threads share one large data structure"""

    """
    Hypothesis:

    With GIL ON or OFF, the memory overhead difference should be small.
    The only memory difference is caused by thread bookkeeping/stack memory
    for each thread.

    Results:

    As expected, memory usage is nearly identical between GIl enabled and GIL disabled modes. This demonstrates that if there is any caused by GIL removal, it is caused primarily by the allocation management. Shared read-only data patterns show no memory penalty.

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

    By forcing mem allocator to handle high churns (constant creation and deletion of objects),
    we can observe possible differences in memory overhead with GIL on and off.

    Use flag visual==True to generate visuals using gil on and off json files

    Results: Once again, the memory overhead is similar with both GIL on and off.
    However, with GIL off, performance gain is substantial, with 3.7x faster with aggressive allocation testing.
    Seems like Python 3.13's allocator is well-tuned and handles free threading efficiently.

    """

    def allocate_and_free():
        while not stop_flag:
            data = []
            for _ in range(10000):
                data.append([0] * 100)
            del data

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


def visualize():
    import matplotlib.pyplot as plt

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "../membench_results")

    with open(os.path.join(output_dir, f"mem_frag_DISABLED.json"), "r") as f:
        samples1 = json.load(f)
    with open(os.path.join(output_dir, f"mem_frag_ENABLED.json"), "r") as f:
        samples2 = json.load(f)

    samples1 = samples1["results"]
    samples2 = samples2["results"]

    times_off = [s["timestamp"] - samples1[0]["timestamp"] for s in samples1]
    rss_off = [s["rss_mb"] for s in samples1]

    times_on = [s["timestamp"] - samples2[0]["timestamp"] for s in samples2]
    rss_on = [s["rss_mb"] for s in samples2]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(
        "Test 3: Memory Fragmentation Over Time", fontsize=16, fontweight="bold"
    )

    ax1.plot(times_on, rss_on, label="GIL ON", color="#2ecc71", linewidth=2, alpha=0.8)
    ax1.plot(
        times_off, rss_off, label="GIL OFF", color="#e74c3c", linewidth=2, alpha=0.8
    )
    ax1.set_xlabel("Time (seconds)", fontsize=12)
    ax1.set_ylabel("RSS Memory (MB)", fontsize=12)
    ax1.set_title("Memory Usage Over Time", fontsize=14, fontweight="bold")
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    import statistics

    stats_on = {
        "min": min(rss_on),
        "max": max(rss_on),
        "avg": statistics.mean(rss_on),
        "std": statistics.stdev(rss_on) if len(rss_on) > 1 else 0,
    }

    stats_off = {
        "min": min(rss_off),
        "max": max(rss_off),
        "avg": statistics.mean(rss_off),
        "std": statistics.stdev(rss_off) if len(rss_off) > 1 else 0,
    }

    metrics = ["Min", "Max", "Average", "Std Dev"]
    on_values = [stats_on["min"], stats_on["max"], stats_on["avg"], stats_on["std"]]
    off_values = [
        stats_off["min"],
        stats_off["max"],
        stats_off["avg"],
        stats_off["std"],
    ]

    x = range(len(metrics))
    width = 0.35

    bars1 = ax2.bar(
        [i - width / 2 for i in x],
        on_values,
        width,
        label="GIL ON",
        color="#2ecc71",
        alpha=0.7,
        edgecolor="black",
    )
    bars2 = ax2.bar(
        [i + width / 2 for i in x],
        off_values,
        width,
        label="GIL OFF",
        color="#e74c3c",
        alpha=0.7,
        edgecolor="black",
    )

    ax2.set_ylabel("Memory (MB)", fontsize=12)
    ax2.set_title("Statistical Comparison", fontsize=14, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics)
    ax2.legend(fontsize=11)
    ax2.grid(axis="y", alpha=0.3)

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.1f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    plt.savefig(os.path.join(output_dir, "visual.png"), dpi=300, bbox_inches="tight")
    plt.close()


def save_res(results, file_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "../membench_results")
    data = {"results": results}
    with open(os.path.join(output_dir, f"{file_name}.json"), "w") as f:
        json.dump(data, f, indent=2)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--test", type=int, default=None)
    parser.add_argument("--visual", type=bool, default=False)
    parser.add_argument("--num_threads", type=int, default=8)
    args = parser.parse_args()

    try:
        if hasattr(sys, "_is_gil_enabled"):
            gil_status = "DISABLED" if not sys._is_gil_enabled() else "ENABLED"
        else:
            gil_status = "ENABLED"
    except:
        gil_status = "ENABLED"

    print(f"GIL: {gil_status}")

    NUM_THREADS = args.num_threads
    print(f"Number of threads: {NUM_THREADS}")

    if args.test == 1:
        res = test_thread_local_mem(NUM_THREADS)
        print(res)
    elif args.test == 2:
        res = test_shared_mem(NUM_THREADS)
        print(res)
    elif args.test == 3:
        res = test_fragmentation(NUM_THREADS)
        save_res(res, f"mem_frag_{gil_status}")

    if args.visual:
        visualize()


if __name__ == "__main__":
    main()
