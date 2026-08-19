"""Time one `Network.open` configuration, optionally under cProfile.

Loading a large network is dominated by how much of it is read, so the knobs
that matter are the companions and the filters. This times one combination of
them, repeatedly, and reports the minimum and median.

Usage
-----
uv run python tests/profiling/profile_network_loading.py --res-path <path-to-result-file>

Companions and a quantities filter are opt-in:
uv run python tests/profiling/profile_network_loading.py --res-path <res> --companions <resx> <inp>
uv run python tests/profiling/profile_network_loading.py --res-path <res> --quantities Pressure

Add --profile for a cProfile pass on top of the timed runs, then inspect it with:
uv run snakeviz tests/profiling/output/profile.prof
"""

import argparse
import cProfile
import gc
import json
import pstats
import statistics
import sys
import time
from pathlib import Path

import mikeio1d
from mikeio1d.network import Network

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--res-path",
        type=Path,
        required=True,
        help="Path to the EPANET .res file to load.",
    )
    parser.add_argument(
        "--companions",
        nargs="*",
        type=Path,
        default=None,
        help="Companion files to read alongside the result: a '.resx' for extra "
        "results, an '.inp' for reach lengths. Omit to let them be found beside "
        "the result file; pass with no values to read none.",
    )
    parser.add_argument(
        "--quantities",
        nargs="+",
        default=None,
        help="Quantity name(s) to pass as the 'quantities' filter to "
        "Network.open, e.g. --quantities Pressure. Omit to load every quantity "
        "(the default, unfiltered behavior).",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="How many timed loads to run. The reported figures are the "
        "minimum and median over these.",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="Loads to run before timing starts. The first load in a process "
        "pays a one-off mikeio1d/.NET start-up cost of several seconds, which "
        "is identical across revisions and would otherwise swamp the "
        "comparison. Its duration is still reported, as 'cold'.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run one extra load under cProfile and dump it to "
        "<output-dir>/<label>.prof. Off by default, because the profiler "
        "inflates the runtime and so distorts the timings.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the result as a single JSON object instead of prose, for "
        "a driver script to collect.",
    )
    parser.add_argument(
        "--label",
        default="profile",
        help="Tag used for the output .prof filename, e.g. 'main' or "
        "'network-loading'.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write the .prof file to.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    kwargs: dict[str, object] = {}
    if args.companions is not None:
        kwargs["companions"] = [companion.resolve() for companion in args.companions]
    if args.quantities is not None:
        kwargs["quantities"] = args.quantities

    res_path = args.res_path.resolve()

    def timed_load() -> tuple[float, float, int, int, list[str]]:
        gc.collect()
        start, start_cpu = time.perf_counter(), time.process_time()
        network = Network.open(res_path, **kwargs)  # type: ignore[arg-type]
        elapsed = time.perf_counter() - start
        # CPU time counts only this process, so an antivirus scan of the result
        # file or any other busy process shows up in the wall clock but not
        # here. It is the steadier of the two for comparing revisions; the wall
        # clock is what a user actually waits.
        elapsed_cpu = time.process_time() - start_cpu
        summary = (
            elapsed,
            elapsed_cpu,
            network.graph.number_of_nodes(),
            len(network._reaches),
            sorted(network.quantities),
        )
        # Freed before returning so every load starts from a comparable heap
        # rather than growing one.
        del network
        return summary

    cold = [timed_load()[0] for _ in range(args.warmup)]

    seconds, cpu_seconds = [], []
    for _ in range(args.repeat):
        elapsed, elapsed_cpu, n_nodes, n_reaches, quantities = timed_load()
        seconds.append(elapsed)
        cpu_seconds.append(elapsed_cpu)

    if args.profile:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        stats_path = args.output_dir / f"{args.label}.prof"
        gc.collect()
        profiler = cProfile.Profile()
        profiler.enable()
        Network.open(res_path, **kwargs)  # type: ignore[arg-type]
        profiler.disable()
        profiler.dump_stats(stats_path)

    result = {
        "label": args.label,
        # Recorded so a driver can prove each case really imported the source
        # tree it meant to, rather than silently falling back to the default.
        "mikeio1d": str(Path(mikeio1d.__file__).parent),
        "seconds": seconds,
        "cpu_seconds": cpu_seconds,
        "cold": cold[0] if cold else None,
        "min": min(seconds),
        "median": statistics.median(seconds),
        "cpu_min": min(cpu_seconds),
        "n_nodes": n_nodes,
        "n_reaches": n_reaches,
        "quantities": quantities,
    }

    if args.json:
        print(json.dumps(result))
        return

    print(f"Label:      {args.label}")
    print(f"res:        {res_path}")
    print(f"companions: {kwargs.get('companions', 'found beside the result')}")
    print(f"quantities: {args.quantities or 'all'}")
    print(f"nodes:      {n_nodes}   reaches: {n_reaches}")
    print(f"loaded:     {', '.join(quantities)}")
    if cold:
        print(f"cold:       {cold[0]:.2f}s (discarded)")
    print(f"seconds:    {', '.join(f'{s:.2f}' for s in seconds)}")
    print(f"cpu:        {', '.join(f'{s:.2f}' for s in cpu_seconds)}")
    print(
        f"min:        {min(seconds):.2f}s   median: {statistics.median(seconds):.2f}s"
    )

    if args.profile:
        print(f"\nWrote profile stats to {stats_path}", file=sys.stderr)
        pstats.Stats(str(stats_path)).sort_stats("cumulative").print_stats(20)


if __name__ == "__main__":
    main()
