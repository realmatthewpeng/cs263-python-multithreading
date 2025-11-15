"""
Run a program and monitor its total memory usage (RSS), including all child
processes. Prints live memory usage and reports peak usage at the end.

Usage:
    python3 run_and_monitor.py python3 your_prog.py arg1 arg2 ...
"""

import sys
import time
import psutil
import subprocess

def get_total_rss(proc):
    """Return total RSS of proc + all children."""
    try:
        p = psutil.Process(proc.pid)
    except psutil.NoSuchProcess:
        return 0

    total = 0

    try:
        total += p.memory_info().rss
    except psutil.Error:
        pass

    for child in p.children(recursive=True):
        try:
            total += child.memory_info().rss
        except psutil.Error:
            pass

    return total


def main():
    if len(sys.argv) < 2:
        print("Usage: run_and_monitor.py <command> [args...]")
        sys.exit(1)

    # Command to execute (list of args)
    cmd = sys.argv[1:]

    # Start target program
    print(f"Starting: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd)

    peak = 0

    try:
        while True:
            # Poll process; break if finished
            if proc.poll() is not None:
                break

            mem = get_total_rss(proc)
            peak = max(peak, mem)
            # print(f"RSS: {mem / (1024*1024):.2f} MB")

            time.sleep(0.1)  # sampling interval
    finally:
        # Ensure process is reaped in case of exceptions
        try:
            proc.wait(timeout=1)
        except Exception:
            pass

    print("\nProcess finished.")
    print(f"Peak memory usage: {peak / (1024*1024):.2f} MB")


if __name__ == "__main__":
    main()

"""
Python 3.13t Results:

python3 benchmarks/run_and_monitor.py python3 benchmarks/thread_overhead.py --selected 0 --threads 16 --iters 1000
Peak memory usage: 18.47 MB

python3 benchmarks/run_and_monitor.py python3 benchmarks/thread_overhead.py --selected 1 --threads 16 --iters 1000
Peak memory usage: 18.58 MB

python3 benchmarks/run_and_monitor.py python3 benchmarks/thread_overhead.py --selected 2 --threads 16 --iters 1000
Peak memory usage: 18.63 MB

python3 benchmarks/run_and_monitor.py python3 benchmarks/thread_overhead.py --selected 3 --threads 16 --iters 1000
Peak memory usage: 18.89 MB

python3 benchmarks/run_and_monitor.py python3 benchmarks/thread_overhead.py --selected 4 --threads 16 --iters 20  
Peak memory usage: 224.78 MB

python3 benchmarks/run_and_monitor.py python3 benchmarks/thread_overhead.py --selected 5 --threads 16 --iters 20  
Peak memory usage: 264.16 MB

python3 benchmarks/run_and_monitor.py python3 benchmarks/thread_overhead.py --selected 6 --threads 16 --iters 20  
Peak memory usage: 109.70 MB
"""