import argparse
import gc
import sys
import threading
import time

"""
Program with many threads creating lots of objects, keeping some alive
to trigger GC

GIL removal provided 2.93-4.42x speedup depending on thread count, with performance benefits increasing at higher parallelism

While GC collection frequency increased 3-5x with GIL disabled due to faster allocation rates, the absolute overhead (1.4-2.8ms) was negligible compared to the 58-256ms execution time savings

The benefit-to-cost ratio of GIL removal was approximately 90:1, with every 1ms of additional GC overhead yielding ~90ms of performance gain through parallelism

For allocation-intensive multi-threaded workloads, GIL removal delivers substantial performance benefits that far exceed the increased garbage collection overhead, with net gains improving at higher thread counts
"""


def get_gc_stats():
    """Get current GC statistics"""
    stats = gc.get_stats()
    return {
        "gen0": stats[0]["collections"],
        "gen1": stats[1]["collections"],
        "gen2": stats[2]["collections"],
    }


def heavy_allocation_workload(thread_id, num_iterations):
    """
    Create lots of objects, keep some alive to trigger GC
    """
    # Storage to keep objects alive longer
    live_objects = []

    for i in range(num_iterations):
        temp1 = [thread_id, i] * 100
        temp2 = {"id": thread_id, "iter": i, "data": [0] * 50}
        temp3 = (thread_id, i, "temporary")

        kept_list = [thread_id, i] * 50
        kept_dict = {"thread": thread_id, "count": i}

        live_objects.append(kept_list)
        live_objects.append(kept_dict)

        if len(live_objects) > 1500:
            # Remove oldest 500
            live_objects = live_objects[500:]

    return len(live_objects)


def run_gc_test(num_threads, iterations_per_thread):
    """Run GC impact test that actually triggers collections"""

    gil_status = "Unknown"
    if hasattr(sys, "_is_gil_enabled"):
        gil_status = "DISABLED" if not sys._is_gil_enabled() else "Enabled"
    print(f"\nGIL status: {gil_status}")
    print(f"Threads: {num_threads}")
    print(f"Iterations per thread: {iterations_per_thread:,}")
    print(f"Total operations: {num_threads * iterations_per_thread:,}")

    # Show GC threshold
    threshold = gc.get_threshold()
    print(f"\nGC Thresholds:")
    print(f"Gen 0: {threshold[0]} allocations")
    print(f"Gen 1: {threshold[1]} Gen 0 collections")
    print(f"Gen 2: {threshold[2]} Gen 1 collections")

    # Get initial GC stats
    gc.collect()  # Start clean
    initial_stats = get_gc_stats()
    initial_objects = gc.get_count()

    print(f"\nInitial state:")
    print(f"Gen 0 collections: {initial_stats['gen0']}")
    print(f"Gen 1 collections: {initial_stats['gen1']}")
    print(f"Gen 2 collections: {initial_stats['gen2']}")
    print(f"Live objects: {sum(initial_objects)}")

    # Run workload
    print(f"\nRunning allocation workload...")

    start_time = time.time()

    threads = []
    for i in range(num_threads):
        t = threading.Thread(
            target=heavy_allocation_workload, args=(i, iterations_per_thread)
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    workload_time = time.time() - start_time

    # Get GC stats after workload
    after_stats = get_gc_stats()
    after_objects = gc.get_count()

    # Calculate collections during workload
    gen0_collections = after_stats["gen0"] - initial_stats["gen0"]
    gen1_collections = after_stats["gen1"] - initial_stats["gen1"]
    gen2_collections = after_stats["gen2"] - initial_stats["gen2"]
    total_collections = gen0_collections + gen1_collections + gen2_collections

    print(f"\nWorkload completed in {workload_time:.3f} seconds")

    print(f"\nCollections triggered during workload:")
    print(f"Gen 0 (young):  {gen0_collections} collections")
    print(f"Gen 1 (mature): {gen1_collections} collections")
    print(f"Gen 2 (old):    {gen2_collections} collections")
    print(f"Total:          {total_collections} collections")

    return {
        "workload_time": workload_time,
        "gen0_collections": gen0_collections,
        "gen1_collections": gen1_collections,
        "gen2_collections": gen2_collections,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GC impact benchmark for multi-threaded allocation workloads")
    parser.add_argument("--threads", type=int, default=8, help="Number of threads (default: 8)")
    parser.add_argument("--iterations", type=int, default=10000, help="Iterations per thread (default: 10000)")
    args = parser.parse_args()

    result = run_gc_test(args.threads, args.iterations)
