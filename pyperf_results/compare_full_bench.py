import re
from pathlib import Path


MEAN_RE = re.compile(r"^Mean\s*\+-\s*std\s*dev:\s*(?P<mean>[\d]*\.?\d+)\s*(?P<unit>ns|us|ms|sec)\s*\+-\s*(?P<std>[\d]*\.?\d+)\s*(?P<std_unit>ns|us|ms|sec)\s*$")

HEADER_RE = re.compile(r"^###\s*(?P<name>.+?)\s*###\s*$")


def parse(path):
    """Return benchmark_name -> mean_seconds."""
    data = {}
    cur_name = None
    sec_map = {
        "sec": 1.0,
        "ms": 1e-3,
        "us": 1e-6,
        "ns": 1e-9,
    }

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            m = HEADER_RE.match(line)
            if m:
                cur_name = m.group("name").strip()
                continue

            if cur_name is not None:
                mm = MEAN_RE.match(line)
                if mm:
                    mean = float(mm.group("mean"))
                    unit = mm.group("unit")
                    mean_sec = mean * sec_map.get(unit, 1.0)
                    data[cur_name] = mean_sec
                    cur_name = None
                    continue
            
            # print(line)

    return data


def compare_files(a, b):
    a_map = parse(a)
    b_map = parse(b)

    keys = sorted(a_map.keys())

    rows = []
    for k in keys:
        ta = a_map.get(k)
        tb = b_map.get(k)
        pct = None
        if ta is not None and tb is not None and ta != 0:
            pct = (tb - ta) / ta * 100.0
        rows.append((k, ta, tb, pct))

    pct_values = []

    print(f"Compared {a} vs {b}")
    print(f"{'Benchmark':60} | {'A(s)':>12} | {'B(s)':>12} | {'% change':>9}")
    print("-" * 102)
    for name, ta, tb, pct in rows:
        ta_s = "N/A" if ta is None else f"{ta:.6f}"
        tb_s = "N/A" if tb is None else f"{tb:.6f}"
        pct_s = "N/A"
        if pct is not None:
            pct_values.append(pct)
            pct_s = f"{pct:+7.3f}%"
        print(f"{name[:60]:60} | {ta_s:>12} | {tb_s:>12} | {pct_s:>9}")

    # compute average percent change
    avg_pct = sum(pct_values) / len(pct_values)
    print()
    print(f"Average % change across {len(pct_values)} benchmarks: {avg_pct:+7.3f}%")


a = Path("pyperf_results/full_bench_313.txt")
b = Path("pyperf_results/full_bench_313t.txt")
compare_files(a, b)

