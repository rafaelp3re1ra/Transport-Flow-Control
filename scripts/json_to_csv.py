#!/usr/bin/env python3
"""
Script to convert metrics JSON files to separate CSVs (timeline and summary)
"""
import json
import csv
import sys
import os

def json_to_timeline_csv(json_path, timeline_csv_path):
    """
    Convert a metrics JSON file to CSV with only per-second data (timeline)

    Args:
        json_path: Path to the input JSON file
        timeline_csv_path: Path to the timeline CSV file
    """
    # Read the JSON
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Write the timeline CSV
    with open(timeline_csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Header for per-second metrics
        writer.writerow(['Second', 'Timestamp', 'Packets', 'Bytes', 'Bandwidth (Mbps)',
                        'Jitter (ms)', 'Retransmissions', 'Loss (%)'])

        # Per-second data (timeline only, no summary)
        for metric in data.get('metrics_per_second', []):
            writer.writerow([
                metric.get('second', 0),
                metric.get('timestamp', ''),
                metric.get('packets', 0),
                metric.get('bytes', 0),
                metric.get('bandwidth_mbps', 0),
                metric.get('jitter_ms', 0),
                metric.get('retransmissions', 0),
                metric.get('loss_percent', 0)
            ])

    print(f"Timeline CSV generated: {timeline_csv_path}")
    return timeline_csv_path


def json_to_summary_csv(json_path, summary_csv_path):
    """
    Convert a metrics JSON file to CSV with only summary statistics (summary)

    Args:
        json_path: Path to the input JSON file
        summary_csv_path: Path to the summary CSV file
    """
    # Read the JSON
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Write the summary CSV
    with open(summary_csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Header
        writer.writerow(['Metric', 'Value'])

        # Summary statistics
        summary = data.get('summary', {})
        writer.writerow(['Duration (seconds)', data.get('total_duration_seconds', 0)])
        writer.writerow(['Total Packets', summary.get('total_packets', 0)])
        writer.writerow(['Total Bytes', summary.get('total_bytes', 0)])
        writer.writerow(['Average Bandwidth (Mbps)', summary.get('avg_bandwidth_mbps', 0)])
        writer.writerow(['Average Jitter (ms)', summary.get('avg_jitter_ms', 0)])
        writer.writerow(['Total Retransmissions', summary.get('total_retransmissions', 0)])
        writer.writerow(['Average Loss (%)', summary.get('avg_loss_percent', 0)])

    print(f"Summary CSV generated: {summary_csv_path}")
    return summary_csv_path


def batch_convert(results_dir='./results'):
    """
    Convert all JSON files in the results directory to CSVs (timeline and summary)

    Args:
        results_dir: Directory containing the JSON files
    """
    if not os.path.exists(results_dir):
        print(f"Directory not found: {results_dir}")
        return

    json_files = [f for f in os.listdir(results_dir) if f.endswith('.json')]

    if not json_files:
        print(f"No JSON files found in {results_dir}")
        return

    print(f"Found {len(json_files)} JSON files")

    for json_file in json_files:
        json_path = os.path.join(results_dir, json_file)
        base_name = json_file.replace('.json', '')
        timeline_csv_path = os.path.join(results_dir, f'{base_name}_timeline.csv')
        summary_csv_path = os.path.join(results_dir, f'{base_name}_summary.csv')

        try:
            json_to_timeline_csv(json_path, timeline_csv_path)
            json_to_summary_csv(json_path, summary_csv_path)
        except Exception as e:
            print(f"Error converting {json_file}: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == '--batch':
            # Batch mode: convert all JSONs in the results directory
            results_dir = sys.argv[2] if len(sys.argv) > 2 else './results'
            batch_convert(results_dir)
        else:
            # Single mode: convert a specific file
            json_path = sys.argv[1]

            if not os.path.exists(json_path):
                print(f"File not found: {json_path}")
                sys.exit(1)

            # Generate both CSVs (timeline and summary)
            base_name = json_path.replace('.json', '')
            timeline_csv_path = sys.argv[2] if len(sys.argv) > 2 else f'{base_name}_timeline.csv'
            summary_csv_path = sys.argv[3] if len(sys.argv) > 3 else f'{base_name}_summary.csv'

            json_to_timeline_csv(json_path, timeline_csv_path)
            json_to_summary_csv(json_path, summary_csv_path)
    else:
        print("Usage:")
        print("  python json_to_csv.py <json_file> [timeline_csv_file] [summary_csv_file]")
        print("  python json_to_csv.py --batch [results_dir]")
        sys.exit(1)
