#!/usr/bin/env python3
"""
Script to plot comparative graphs between BBR, CUBIC, and QUIC protocols
"""
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


def plot_comparison(results_dir: Path):
    # Build expected file paths
    files = {
        'bbr_client': results_dir / 'bbr_client_timeline.csv',
        'bbr_server': results_dir / 'bbr_server_timeline.csv',
        'cubic_client': results_dir / 'cubic_client_timeline.csv',
        'cubic_server': results_dir / 'cubic_server_timeline.csv',
        'quic_client': results_dir / 'quic_client_timeline.csv',
        'quic_server': results_dir / 'quic_server_timeline.csv',
    }

    missing = [p for p in files.values() if not p.exists()]
    if missing:
        print('Error: missing required files in:', results_dir)
        for p in missing:
            print(' -', p.name)
        available = sorted([f.name for f in results_dir.glob('*.csv')]) if results_dir.exists() else []
        if available:
            print('\nCSV files found in', results_dir, ':')
            for a in available:
                print('  ', a)
        else:
            print('\nNo CSV files found in', results_dir)
        raise SystemExit(1)

    # Load timeline data
    bbr_client = pd.read_csv(files['bbr_client'])
    bbr_server = pd.read_csv(files['bbr_server'])
    cubic_client = pd.read_csv(files['cubic_client'])
    cubic_server = pd.read_csv(files['cubic_server'])
    quic_client = pd.read_csv(files['quic_client'])
    quic_server = pd.read_csv(files['quic_server'])

    # Create subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('BBR vs CUBIC vs QUIC Comparison - Metrics per Second', fontsize=16)

    # Bandwidth comparison
    ax1.plot(bbr_client['Second'], bbr_client['Bandwidth (Mbps)'], label='BBR Client', color='blue', alpha=0.7)
    ax1.plot(bbr_server['Second'], bbr_server['Bandwidth (Mbps)'], label='BBR Server', color='blue', linestyle='--', alpha=0.7)
    ax1.plot(cubic_client['Second'], cubic_client['Bandwidth (Mbps)'], label='CUBIC Client', color='red', alpha=0.7)
    ax1.plot(cubic_server['Second'], cubic_server['Bandwidth (Mbps)'], label='CUBIC Server', color='red', linestyle='--', alpha=0.7)
    ax1.plot(quic_client['Second'], quic_client['Bandwidth (Mbps)'], label='QUIC Client', color='green', alpha=0.8)
    ax1.plot(quic_server['Second'], quic_server['Bandwidth (Mbps)'], label='QUIC Server', color='green', linestyle='--', alpha=0.8)
    ax1.set_title('Bandwidth (Mbps)')
    ax1.set_xlabel('Second')
    ax1.set_ylabel('Mbps')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Packet Loss comparison (TCP protocols only - QUIC handles reliability differently)
    ax2.plot(bbr_client['Second'], bbr_client['Loss (%)'], label='BBR Client', color='blue', alpha=0.7)
    ax2.plot(bbr_server['Second'], bbr_server['Loss (%)'], label='BBR Server', color='blue', linestyle='--', alpha=0.7)
    ax2.plot(cubic_client['Second'], cubic_client['Loss (%)'], label='CUBIC Client', color='red', alpha=0.7)
    ax2.plot(cubic_server['Second'], cubic_server['Loss (%)'], label='CUBIC Server', color='red', linestyle='--', alpha=0.7)
    ax2.set_title('Packet Loss (%) - TCP Protocols')
    ax2.set_xlabel('Second')
    ax2.set_ylabel('%')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Retransmissions comparison (TCP protocols only - QUIC handles reliability differently)
    ax3.plot(bbr_client['Second'], bbr_client['Retransmissions'], label='BBR Client', color='blue', alpha=0.7)
    ax3.plot(bbr_server['Second'], bbr_server['Retransmissions'], label='BBR Server', color='blue', linestyle='--', alpha=0.7)
    ax3.plot(cubic_client['Second'], cubic_client['Retransmissions'], label='CUBIC Client', color='red', alpha=0.7)
    ax3.plot(cubic_server['Second'], cubic_server['Retransmissions'], label='CUBIC Server', color='red', linestyle='--', alpha=0.7)
    ax3.set_title('Retransmissions - TCP Protocols')
    ax3.set_xlabel('Second')
    ax3.set_ylabel('Count')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Jitter comparison
    ax4.plot(bbr_client['Second'], bbr_client['Jitter (ms)'], label='BBR Client', color='blue', alpha=0.7)
    ax4.plot(bbr_server['Second'], bbr_server['Jitter (ms)'], label='BBR Server', color='blue', linestyle='--', alpha=0.7)
    ax4.plot(cubic_client['Second'], cubic_client['Jitter (ms)'], label='CUBIC Client', color='red', alpha=0.7)
    ax4.plot(cubic_server['Second'], cubic_server['Jitter (ms)'], label='CUBIC Server', color='red', linestyle='--', alpha=0.7)
    ax4.plot(quic_client['Second'], quic_client['Jitter (ms)'], label='QUIC Client', color='green', alpha=0.8)
    ax4.plot(quic_server['Second'], quic_server['Jitter (ms)'], label='QUIC Server', color='green', linestyle='--', alpha=0.8)
    ax4.set_title('Jitter (ms)')
    ax4.set_xlabel('Second')
    ax4.set_ylabel('ms')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    out_png = results_dir / 'protocol_comparison.png'
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.show()

    print(f"Plot saved to: {out_png}")

def _parse_args():
    parser = argparse.ArgumentParser(description='Plot BBR vs CUBIC vs QUIC comparison using files in results/')
    parser.add_argument('--results', '-r', type=str, default=None,
                        help='Path to results directory (default: repo/results)')
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    # Determine results directory relative to script location if not provided
    if args.results:
        results_path = Path(args.results).expanduser().resolve()
    else:
        # script is in <repo>/scripts/post_processing, results folder is at repo root
        script_dir = Path(__file__).resolve().parent
        results_path = script_dir.parent.parent / 'results'

    plot_comparison(results_path)