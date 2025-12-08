# CS 263 Project - Fall 2025

A comprehensive benchmark suite for analyzing the performance and memory safety implications of Python 3.13's experimental free-threading mode (GIL-disabled).

## Overview

Python's Global Interpreter Lock (GIL) has long been a bottleneck for CPU-bound multithreaded programs, allowing only one thread to execute Python bytecode at a time. **Python 3.13** introduces an experimental **free-threading mode** that allows the GIL to be disabled, enabling true parallelism in Python threads.

This project provides a suite of benchmarks to empirically measure:

- **Performance improvements** when the GIL is disabled for CPU-bound tasks
- **Memory safety trade-offs** (race conditions) in free-threaded code
- **Thread creation overhead** compared to process-based parallelism
- **I/O-bound vs CPU-bound** workload behavior

## Requirements

- **Python 3.13** (standard GIL-enabled build)
- **Python 3.13t** (free-threading build with `PYTHON_GIL=0` or `-X gil=0`)

### Dependencies

```text
numpy==2.3.4
psutil==7.1.3
pyperf==2.9.0
pyperformance==1.13.0
```

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/realmatthewpeng/cs263-python-multithreading.git
   cd cs263-python-multithreading/project
   ```

2. **Set up virtual environments:**

   For Python 3.13 (GIL-enabled):

   ```bash
   python3.13 -m venv venv3.13
   source venv3.13/bin/activate
   pip install -r requirements.txt
   ```

   For Python 3.13t (free-threading):

   ```bash
   python3.13t -m venv venv3.13t
   source venv3.13t/bin/activate
   pip install -r requirements.txt
   ```

## Usage

### Running Benchmarks

All benchmarks are located in the `benchmarks/` directory. Run each Python file with the `--help` argument for more detailed usage instructions.

### pyperformance

`pyperformance` is a standard Python implementation benchmark. This project used `pyperformance` to measure single thread performance. To run `pyperformance`, please refer to the [pyperformance documentation](https://pyperformance.readthedocs.io/). Inside of the `pyperf_results` directory, `compare_full_bench.py` can be used to calculate the % runtime performance change based on the output of two `pyperformance` runs. See `full_bench_313.txt` or `full_bench_313t.txt` for the expected file format that `compare_full_bench.py` uses.

## Authors

Matthew Peng, @realmatthewpeng
Tim Kim, @taeseongk
