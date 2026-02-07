"""
Benchmark report generator: reads JSONL results and outputs comparison tables.

Usage:
    # Compare latest benchmark run
    python3 src/benchmark_report.py

    # Compare specific run
    python3 src/benchmark_report.py output/benchmarks/20260207_143000_baseline/results.jsonl

    # Compare two runs side by side
    python3 src/benchmark_report.py output/benchmarks/20260207_*/results.jsonl

    # Save report to file
    python3 src/benchmark_report.py --output report.md
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def load_results(jsonl_path: str) -> List[Dict]:
    """Load benchmark results from a JSONL file."""
    results = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def extract_run_label(jsonl_path: str) -> str:
    """Extract a human-readable label from the results file path."""
    p = Path(jsonl_path)
    # Try loading config.json from the same directory
    config_path = p.parent / "config.json"
    if config_path.exists():
        with config_path.open() as f:
            config = json.load(f)
            if config.get("label"):
                return config["label"]
    # Fall back to directory name
    return p.parent.name


def compute_stats(values: List[float]) -> Dict:
    """Compute mean, min, max, std for a list of values."""
    if not values:
        return {"mean": None, "min": None, "max": None, "count": 0}
    n = len(values)
    mean = sum(values) / n
    min_val = min(values)
    max_val = max(values)
    return {
        "mean": round(mean, 1),
        "min": round(min_val, 1),
        "max": round(max_val, 1),
        "count": n,
    }


def generate_summary_table(results: List[Dict], label: str) -> str:
    """Generate a summary markdown table for one benchmark run."""
    successful = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") == "error"]

    if not successful:
        return f"## {label}\n\nNo successful results.\n"

    # Collect metrics
    composites = []
    face_sims = []
    vibrancies = []
    edge_scores = []
    times = []
    costs = []

    for r in successful:
        q = r.get("quality", {})
        if q.get("composite_score") is not None:
            composites.append(q["composite_score"])
        if q.get("face_similarity_raw") is not None:
            face_sims.append(q["face_similarity_raw"])
        if q.get("color_vibrancy") is not None:
            vibrancies.append(q["color_vibrancy"])
        if q.get("edge_cleanliness") is not None:
            edge_scores.append(q["edge_cleanliness"])
        if r.get("total_elapsed_seconds") is not None:
            times.append(r["total_elapsed_seconds"])
        if r.get("total_cost_estimate") is not None:
            costs.append(r["total_cost_estimate"])

    # Pipeline description
    has_swap = any(r.get("face_swap_enabled") for r in successful)
    backends = sorted(set(r.get("backend", "?") for r in successful))
    styles = sorted(set(r.get("style", "?") for r in successful))
    seed = successful[0].get("seed", "random")

    lines = []
    lines.append(f"## {label}")
    lines.append("")
    lines.append(f"**Pipeline:** {', '.join(backends)}{' + face swap' if has_swap else ''}")
    lines.append(f"**Styles:** {', '.join(styles)}")
    lines.append(f"**Photos:** {len(set(r['photo'] for r in successful))} | **Runs:** {len(successful)} OK, {len(failed)} failed")
    lines.append(f"**Seed:** {seed}")
    lines.append("")

    # Summary stats table
    lines.append("| Metric | Mean | Min | Max | Count |")
    lines.append("|--------|------|-----|-----|-------|")

    if composites:
        s = compute_stats(composites)
        pass_rate = sum(1 for c in composites if c >= 70) / len(composites) * 100
        lines.append(f"| Composite Score | **{s['mean']}** | {s['min']} | {s['max']} | {s['count']} |")
        lines.append(f"| Pass Rate (>=70) | **{pass_rate:.0f}%** | | | |")
    if face_sims:
        s = compute_stats(face_sims)
        lines.append(f"| Face Similarity | **{s['mean']}** | {s['min']} | {s['max']} | {s['count']} |")
    if vibrancies:
        s = compute_stats(vibrancies)
        lines.append(f"| Color Vibrancy | **{s['mean']}** | {s['min']} | {s['max']} | {s['count']} |")
    if edge_scores:
        s = compute_stats(edge_scores)
        lines.append(f"| Edge Cleanliness | **{s['mean']}** | {s['min']} | {s['max']} | {s['count']} |")
    if times:
        s = compute_stats(times)
        lines.append(f"| Time (seconds) | **{s['mean']}** | {s['min']} | {s['max']} | {s['count']} |")
    if costs:
        total = sum(costs)
        avg = total / len(costs)
        lines.append(f"| Cost/run | **${avg:.3f}** | | | ${total:.2f} total |")

    lines.append("")
    return "\n".join(lines)


def generate_per_photo_table(results: List[Dict], label: str) -> str:
    """Generate a per-photo breakdown table."""
    successful = [r for r in results if r.get("status") == "success" and r.get("quality")]

    if not successful:
        return ""

    lines = []
    lines.append(f"### Per-Photo Breakdown ({label})")
    lines.append("")
    lines.append("| Photo | Composite | Face Sim | Vibrancy | Edge | Time | Cost | Pass |")
    lines.append("|-------|-----------|----------|----------|------|------|------|------|")

    # Group by photo, take best run per photo
    by_photo = defaultdict(list)
    for r in successful:
        by_photo[r["photo"]].append(r)

    for photo_path in sorted(by_photo.keys()):
        runs = by_photo[photo_path]
        # Pick best by composite score
        scored = [r for r in runs if r.get("quality", {}).get("composite_score") is not None]
        if not scored:
            continue
        best = max(scored, key=lambda r: r["quality"]["composite_score"])

        q = best["quality"]
        photo_name = Path(photo_path).stem
        composite = q.get("composite_score", "?")
        face_sim = q.get("face_similarity_raw")
        face_str = f"{face_sim:.2f}" if face_sim is not None else "n/a"
        vibrancy = q.get("color_vibrancy", "?")
        edge = q.get("edge_cleanliness", "?")
        elapsed = best.get("total_elapsed_seconds", "?")
        cost = best.get("total_cost_estimate", 0)
        passed = "PASS" if q.get("pass") else "FAIL"

        lines.append(f"| {photo_name} | {composite} | {face_str} | {vibrancy} | {edge} | {elapsed}s | ${cost:.3f} | {passed} |")

    lines.append("")
    return "\n".join(lines)


def generate_comparison(all_results: Dict[str, List[Dict]]) -> str:
    """Generate a side-by-side comparison of multiple benchmark runs."""
    if len(all_results) < 2:
        return ""

    lines = []
    lines.append("## Side-by-Side Comparison")
    lines.append("")

    # Build comparison row for each label
    header = ["Metric"]
    for label in all_results:
        header.append(label)
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    # Composite
    row = ["Composite (mean)"]
    for label, results in all_results.items():
        composites = [r["quality"]["composite_score"] for r in results
                      if r.get("status") == "success" and r.get("quality", {}).get("composite_score") is not None]
        row.append(f"**{sum(composites)/len(composites):.1f}**" if composites else "n/a")
    lines.append("| " + " | ".join(row) + " |")

    # Face sim
    row = ["Face Similarity (mean)"]
    for label, results in all_results.items():
        sims = [r["quality"]["face_similarity_raw"] for r in results
                if r.get("status") == "success" and r.get("quality", {}).get("face_similarity_raw") is not None]
        row.append(f"**{sum(sims)/len(sims):.2f}**" if sims else "n/a")
    lines.append("| " + " | ".join(row) + " |")

    # Pass rate
    row = ["Pass Rate"]
    for label, results in all_results.items():
        composites = [r["quality"]["composite_score"] for r in results
                      if r.get("status") == "success" and r.get("quality", {}).get("composite_score") is not None]
        if composites:
            rate = sum(1 for c in composites if c >= 70) / len(composites) * 100
            row.append(f"{rate:.0f}%")
        else:
            row.append("n/a")
    lines.append("| " + " | ".join(row) + " |")

    # Cost
    row = ["Cost/run"]
    for label, results in all_results.items():
        costs = [r.get("total_cost_estimate", 0) for r in results if r.get("status") == "success"]
        row.append(f"${sum(costs)/len(costs):.3f}" if costs else "n/a")
    lines.append("| " + " | ".join(row) + " |")

    # Time
    row = ["Time (mean)"]
    for label, results in all_results.items():
        times = [r.get("total_elapsed_seconds", 0) for r in results if r.get("status") == "success"]
        row.append(f"{sum(times)/len(times):.1f}s" if times else "n/a")
    lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark comparison report.")
    parser.add_argument(
        "results", nargs="*",
        help="JSONL result files to compare (default: output/benchmarks/latest/results.jsonl)",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Save report to file (default: print to stdout)",
    )
    args = parser.parse_args()

    # Default to latest if no args
    if not args.results:
        latest = Path("output/benchmarks/latest/results.jsonl")
        if latest.exists():
            args.results = [str(latest)]
        else:
            # Find all results files
            benchmark_dir = Path("output/benchmarks")
            results_files = sorted(benchmark_dir.glob("*/results.jsonl"))
            if not results_files:
                print("No benchmark results found. Run benchmark_runner.py first.")
                sys.exit(1)
            # Use the most recent
            args.results = [str(results_files[-1])]
            print(f"Using most recent: {results_files[-1]}")

    # Load all result files
    all_results = {}
    for path in args.results:
        label = extract_run_label(path)
        results = load_results(path)
        all_results[label] = results

    # Generate report
    report_lines = ["# Benchmark Report", ""]

    for label, results in all_results.items():
        report_lines.append(generate_summary_table(results, label))
        report_lines.append(generate_per_photo_table(results, label))

    if len(all_results) >= 2:
        report_lines.append(generate_comparison(all_results))

    report = "\n".join(report_lines)

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
