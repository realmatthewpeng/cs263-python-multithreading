import threading
import time

# Command is:
# python3.13t -X gil=0 mem_safety.py

# Shared counter
counter = 0
counter_lock = threading.Lock()

# Track errors
errors = 0

def unsafe_incr(n):
    """Increment without lock (race condition)"""
    global counter, errors
    for _ in range(n):
        old_value = counter
        # Sleeping vs Not Sleeping causes different behavior
        time.sleep(0.00001)
        counter = old_value + 1

def safe_incr(n):
    """Increment with lock (thread safe)"""
    global counter
    for _ in range(n):
        with counter_lock:
            counter += 1

def test_unsafe(num_threads, increments_per_thread):
    """Test without synchronization"""
    global counter, errors
    counter = 0
    errors = 0

    print(f"\n--- UNSAFE MODE ---")
    print(f"Threads: {num_threads}, Increments per thread: {increments_per_thread}")
    print(f"Expected final value: {num_threads * increments_per_thread}")

    threads = []
    start = time.time()

    for _ in range(num_threads):
        t = threading.Thread(target=unsafe_incr, args=(increments_per_thread,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start
    expected = num_threads * increments_per_thread
    errors = expected - counter

    print(f"Actual final value: {counter}")
    print(f"Lost increments: {errors}")
    print(f"Error rate: {(errors/expected)*100:.2f}%")
    print(f"Time: {elapsed:.4f}s")

def test_safe(num_threads, increments_per_thread):
    """Test with synchronization"""
    global counter, errors
    counter = 0
    errors = 0

    print(f"\n--- SAFE MODE ---")
    print(f"Threads: {num_threads}, Increments per thread: {increments_per_thread}")
    print(f"Expected final value: {num_threads * increments_per_thread}")

    threads = []
    start = time.time()

    for _ in range(num_threads):
        t = threading.Thread(target=safe_incr, args=(increments_per_thread,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start
    expected = num_threads * increments_per_thread
    errors = expected - counter

    print(f"Actual final value: {counter}")
    print(f"Lost increments: {errors}")
    print(f"Error rate: {(errors/expected)*100:.2f}%")
    print(f"Time: {elapsed:.4f}s")


if __name__ == "__main__":
    import sys

    # Check GIL status
    try:
        if hasattr(sys, '_is_gil_enabled'):
            gil_status = "DISABLED" if not sys._is_gil_enabled() else "ENABLED"
        else:
            gil_status = "ENABLED"
    except:
        gil_status = "ENABLED"

    print(f"GIL: {gil_status}")

    # Run tests
    test_unsafe(10, 1000)
    test_safe(10, 1000)
