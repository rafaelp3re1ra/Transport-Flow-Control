#!/usr/bin/env python3
"""
Example script for metrics analysis
Demonstrates various ways to process the generated JSON data
"""
import json
import csv
from pathlib import Path

def load_metrics(protocol):
    """Load metrics for a specific protocol"""
    # script is in <repo>/scripts/post_processing, results folder is at repo root
    script_dir = Path(__file__).resolve().parent
    results_dir = script_dir.parent.parent / 'results'
    json_path = results_dir / f'{protocol}_metrics.json'
    if not json_path.exists():
        print(f"File not found: {json_path}")
        return None

    with open(json_path) as f:
        return json.load(f)


def print_summary(protocol):
    """Print metrics summary"""
    data = load_metrics(protocol)
    if not data:
        return

    print(f"\n{'=' * 60}")
    print(f"SUMMARY - {protocol.upper()}")
    print(f"{'=' * 60}")

    summary = data['summary']
    print(f"Duration: {data['total_duration_seconds']} seconds")
    print(f"Start: {data['start_time']}")
    print(f"End: {data['end_time']}")
    print()
    print(f"Total Packets: {summary['total_packets']:,}")
    print(f"Total Bytes: {summary['total_bytes']:,} ({summary['total_bytes'] / 1024 / 1024:.2f} MB)")
    print(f"Average Bandwidth: {summary['avg_bandwidth_mbps']:.2f} Mbps")
    print(f"Average Jitter: {summary['avg_jitter_ms']:.2f} ms")
    print(f"Total Retransmissions: {summary['total_retransmissions']}")
    print(f"Average Loss: {summary['avg_loss_percent']:.2f}%")
    print(f"{'=' * 60}\n")


def analyze_bandwidth_stability(protocol):
    """Analyze bandwidth stability"""
    data = load_metrics(protocol)
    if not data:
        return

    bandwidths = [m['bandwidth_mbps'] for m in data['metrics_per_second']]

    min_bw = min(bandwidths)
    max_bw = max(bandwidths)
    avg_bw = sum(bandwidths) / len(bandwidths)

    # Simple standard deviation
    variance = sum((bw - avg_bw) ** 2 for bw in bandwidths) / len(bandwidths)
    std_dev = variance ** 0.5

    # Coefficient of variation (CV)
    cv = (std_dev / avg_bw) * 100 if avg_bw > 0 else 0

    print(f"\n{'=' * 60}")
    print(f"BANDWIDTH STABILITY ANALYSIS - {protocol.upper()}")
    print(f"{'=' * 60}")
    print(f"Minimum: {min_bw:.2f} Mbps")
    print(f"Maximum: {max_bw:.2f} Mbps")
    print(f"Average: {avg_bw:.2f} Mbps")
    print(f"Standard Deviation: {std_dev:.2f} Mbps")
    print(f"Coefficient of Variation: {cv:.2f}%")
    print()

    if cv < 10:
        print("✓ Very stable (CV < 10%)")
    elif cv < 20:
        print("⚠ Moderately stable (10% ≤ CV < 20%)")
    else:
        print("✗ Unstable (CV ≥ 20%)")

    print(f"{'=' * 60}\n")


def find_problematic_seconds(protocol, threshold_loss=1.0, threshold_jitter=10.0):
    """Find seconds with problems (high loss or jitter)"""
    data = load_metrics(protocol)
    if not data:
        return

    problematic = []
    for metric in data['metrics_per_second']:
        if metric['loss_percent'] > threshold_loss or metric['jitter_ms'] > threshold_jitter:
            problematic.append(metric)

    print(f"\n{'=' * 60}")
    print(f"PROBLEMATIC SECONDS - {protocol.upper()}")
    print(f"{'=' * 60}")
    print(f"Criteria: Loss > {threshold_loss}% OR Jitter > {threshold_jitter} ms")
    print()

    if not problematic:
        print("✓ No problematic seconds found!")
    else:
        print(f"⚠ Found {len(problematic)} problematic second(s):\n")
        for m in problematic:
            print(f"  Second {m['second']:2d}: "
                  f"Loss={m['loss_percent']:5.2f}%, "
                  f"Jitter={m['jitter_ms']:6.2f} ms, "
                  f"BW={m['bandwidth_mbps']:6.2f} Mbps")

    print(f"{'=' * 60}\n")


def compare_protocols():
    """Compare all tested protocols"""
    protocols = ['bbr_client', 'cubic_client', 'quic_client']
    results = {}

    for protocol in protocols:
        data = load_metrics(protocol)
        if data:
            results[protocol] = data['summary']

    if not results:
        print("No results found!")
        return

    print(f"\n{'=' * 60}")
    print(f"PROTOCOL COMPARISON")
    print(f"{'=' * 60}\n")

    # Comparative table
    print(f"{'Metric':<30} {'BBR':>12} {'CUBIC':>12} {'QUIC':>12}")
    print(f"{'-' * 30} {'-' * 12} {'-' * 12} {'-' * 12}")

    metrics_to_compare = [
        ('Total Packets', 'total_packets', 'd'),
        ('Total Bytes (MB)', 'total_bytes', ',.2f', lambda x: x / 1024 / 1024),
        ('Avg Bandwidth (Mbps)', 'avg_bandwidth_mbps', '.2f'),
        ('Avg Jitter (ms)', 'avg_jitter_ms', '.2f'),
        ('Total Retrans', 'total_retransmissions', 'd'),
        ('Avg Loss (%)', 'avg_loss_percent', '.2f'),
    ]

    for metric_name, key, fmt, *transforms in metrics_to_compare:
        transform = transforms[0] if transforms else lambda x: x
        row = f"{metric_name:<30}"

        for protocol in protocols:
            if protocol in results:
                value = results[protocol].get(key, 0)
                value = transform(value)
                row += f" {value:>12{fmt}}"
            else:
                row += f" {'N/A':>12}"

        print(row)

    print(f"{'-' * 30} {'-' * 12} {'-' * 12} {'-' * 12}\n")

    # Ranking by bandwidth
    print("🏆 Ranking by Average Bandwidth:")
    sorted_by_bw = sorted(results.items(), key=lambda x: x[1]['avg_bandwidth_mbps'], reverse=True)
    for i, (protocol, summary) in enumerate(sorted_by_bw, 1):
        proto_name = protocol.replace('_client', '').upper()
        print(f"  {i}. {proto_name:6} - {summary['avg_bandwidth_mbps']:.2f} Mbps")

    print()

    # Ranking by jitter (lower is better)
    print("🎯 Ranking by Lowest Jitter:")
    sorted_by_jitter = sorted(results.items(), key=lambda x: x[1]['avg_jitter_ms'])
    for i, (protocol, summary) in enumerate(sorted_by_jitter, 1):
        proto_name = protocol.replace('_client', '').upper()
        print(f"  {i}. {proto_name:6} - {summary['avg_jitter_ms']:.2f} ms")

    print()

    # Ranking by loss (lower is better)
    print("📉 Ranking by Lowest Loss:")
    sorted_by_loss = sorted(results.items(), key=lambda x: x[1]['avg_loss_percent'])
    for i, (protocol, summary) in enumerate(sorted_by_loss, 1):
        proto_name = protocol.replace('_client', '').upper()
        print(f"  {i}. {proto_name:6} - {summary['avg_loss_percent']:.2f}%")

    print(f"{'=' * 60}\n")


def export_comparison_csv():
    """Export comparison to CSV"""
    protocols = ['bbr_client', 'cubic_client', 'quic_client']
    results = {}

    for protocol in protocols:
        data = load_metrics(protocol)
        if data:
            results[protocol] = data['summary']

    if not results:
        print("No results found!")
        return

    # script is in <repo>/scripts/post_processing, results folder is at repo root
    script_dir = Path(__file__).resolve().parent
    results_dir = script_dir.parent.parent / 'results'
    csv_path = results_dir / 'protocol_comparison.csv'

    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Header
        writer.writerow(['Metric', 'BBR', 'CUBIC', 'QUIC'])

        # Data
        metrics = [
            ('Total Packets', 'total_packets'),
            ('Total Bytes', 'total_bytes'),
            ('Avg Bandwidth (Mbps)', 'avg_bandwidth_mbps'),
            ('Avg Jitter (ms)', 'avg_jitter_ms'),
            ('Total Retransmissions', 'total_retransmissions'),
            ('Avg Loss (%)', 'avg_loss_percent'),
        ]

        for metric_name, key in metrics:
            row = [metric_name]
            for protocol in protocols:
                if protocol in results:
                    row.append(results[protocol].get(key, 'N/A'))
                else:
                    row.append('N/A')
            writer.writerow(row)

    print(f"✓ Comparison exported to: {csv_path}\n")


def main():
    """Main function - runs all analyses"""
    print("\n" + "=" * 60)
    print("PROTOCOL METRICS ANALYSIS")
    print("=" * 60)

    # Check if there are results
    script_dir = Path(__file__).resolve().parent
    results_dir = script_dir.parent.parent / 'results'
    if not results_dir.exists():
        print("\n❌ 'results' directory not found!")
        print("Run the tests first: docker-compose --profile all up --build\n")
        return

    json_files = list(results_dir.glob('*_metrics.json'))
    if not json_files:
        print("\n❌ No metrics JSON files found in 'results'!")
        print("Run the tests first: docker-compose --profile all up --build\n")
        return

    print(f"\n✓ Found {len(json_files)} metrics file(s)\n")

    # Extract protocols from filenames
    protocols = [f.stem.replace('_metrics', '') for f in json_files]

    # Individual analyses
    for protocol in protocols:
        print_summary(protocol)
        analyze_bandwidth_stability(protocol)
        find_problematic_seconds(protocol, threshold_loss=0.5, threshold_jitter=5.0)

    # Protocol comparison
    if len(protocols) > 1:
        compare_protocols()
        export_comparison_csv()

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
