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
        # I believe sleeping automatically causes thread switches
        # time.sleep(0.00001)
        # Also see: https://www.reddit.com/r/learnprogramming/comments/16mlz4h/race_condition_doesnt_happen_from_python_310/
        counter = old_value + 1

def get_one():
    return 1
    
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

    # Results (Probably need to run multiple times to see variability)
    # Python 3.13t (GIL Disabled)
    # test_unsafe(10,1000)
    #   Error rate: 48.23%
    #   Time: 0.0020 s 
    # test_unsafe(1,10000)
    #   Error rate: 0.00%
    #   Time: 0.0013 s
    # test_unsafe(2,5000)
    #   Error rate: 36.38%
    #   Time: 0.0014 s
    # test_unsafe(5,2000)
    #   Error rate: 56.46%
    #   Time: 0.0018 s

    # Python 3.13 (GIL Enabled)
    # test_unsafe(10,1000)
    #   Error rate: 0.00%
    #   Time: 0.0017 s 
    # test_unsafe(1,10000)
    #   Error rate: 0.00%
    #   Time: 0.0012 s
    # test_unsafe(2,5000)
    #   Error rate: 0.00%
    #   Time: 0.0008 s
    # test_unsafe(5,2000)
    #   Error rate: 0.00%
    #   Time: 0.0012 s