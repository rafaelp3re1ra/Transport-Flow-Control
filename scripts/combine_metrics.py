#!/usr/bin/env python3
"""
Script to combine client and server metrics into a single summary CSV
"""
import json
import csv
import sys
import os

def combine_metrics(client_json_path, server_json_path, output_csv_path):
    """
    Combine client and server metrics into a single summary CSV

    Args:
        client_json_path: Path to the client JSON
        server_json_path: Path to the server JSON
        output_csv_path: Path to the combined CSV
    """
    # Read the JSONs
    with open(client_json_path, 'r') as f:
        client_data = json.load(f)

    with open(server_json_path, 'r') as f:
        server_data = json.load(f)

    client_summary = client_data.get('summary', {})
    server_summary = server_data.get('summary', {})

    # Extract protocol from filename (e.g., 'quic' from 'quic_client_metrics.json')
    protocol = os.path.basename(client_json_path).split('_')[0].lower()

    # Create combined CSV
    with open(output_csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Header
        writer.writerow(['Metric Name', 'Client', 'Server', 'Total/Average'])

        # Duration - get from total_duration_seconds in main JSON
        client_duration = client_data.get('total_duration_seconds', 0)
        server_duration = server_data.get('total_duration_seconds', 0)
        total_duration = max(client_duration, server_duration)
        writer.writerow(['Duration (seconds)',
                        client_duration,
                        server_duration,
                        total_duration])

        # Total Packets - sum
        client_packets = client_summary.get('total_packets', 0)
        server_packets = server_summary.get('total_packets', 0)
        total_packets = client_packets + server_packets
        writer.writerow(['Total Packets',
                        client_packets, 
                        server_packets,
                        total_packets])

        # Total Bytes - sum
        client_bytes = client_summary.get('total_bytes', 0)
        server_bytes = server_summary.get('total_bytes', 0)
        total_bytes = client_bytes + server_bytes
        writer.writerow(['Total Bytes',
                        client_bytes,
                        server_bytes,
                        total_bytes])

        # Bandwidth - average (uses avg_bandwidth_mbps from summary)
        client_bw = client_summary.get('avg_bandwidth_mbps', 0)
        server_bw = server_summary.get('avg_bandwidth_mbps', 0)
        avg_bw = (client_bw + server_bw) / 2 if (client_bw > 0 or server_bw > 0) else 0
        writer.writerow(['Bandwidth (Mbps)',
                        f"{client_bw:.2f}",
                        f"{server_bw:.2f}",
                        f"{avg_bw:.2f}"])

        # Jitter - average (uses avg_jitter_ms from summary)
        client_jitter = client_summary.get('avg_jitter_ms', 0)
        server_jitter = server_summary.get('avg_jitter_ms', 0)
        avg_jitter = (client_jitter + server_jitter) / 2 if (client_jitter > 0 or server_jitter > 0) else 0
        writer.writerow(['Jitter (ms)',
                        f"{client_jitter:.2f}",
                        f"{server_jitter:.2f}",
                        f"{avg_jitter:.2f}"])

        # RTT - average (uses avg_rtt_ms from summary if exists)
        client_rtt = client_summary.get('avg_rtt_ms', 0)
        server_rtt = server_summary.get('avg_rtt_ms', 0)
        if client_rtt > 0 and server_rtt > 0:
            avg_rtt = (client_rtt + server_rtt) / 2
            writer.writerow(['RTT (ms)',
                            f"{client_rtt:.2f}",
                            f"{server_rtt:.2f}",
                            f"{avg_rtt:.2f}"])
        elif client_rtt > 0:
            writer.writerow(['RTT (ms)',
                            f"{client_rtt:.2f}",
                            '0.00',
                            f"{client_rtt:.2f}"])
        elif server_rtt > 0:
            writer.writerow(['RTT (ms)',
                            '0.00',
                            f"{server_rtt:.2f}",
                            f"{server_rtt:.2f}"])
        else:
            writer.writerow(['RTT (ms)', '0.00', '0.00', 'N/A'])

        # Retransmissions - sum (uses total_retransmissions from summary)
        client_retrans = client_summary.get('total_retransmissions', 0)
        server_retrans = server_summary.get('total_retransmissions', 0)
        total_retrans = client_retrans + server_retrans
        writer.writerow(['Retransmissions',
                        client_retrans,
                        server_retrans,
                        total_retrans])

        # Packet Loss
        if protocol == 'quic':
            # For QUIC, calculate loss based on packet asymmetry
            # Usually client has more packets, so loss = (client - server) / client * 100
            # But handle both cases symmetrically
            client_packets = client_summary.get('total_packets', 0)
            server_packets = server_summary.get('total_packets', 0)

            if client_packets > server_packets:
                # Client has more packets (typical case)
                lost_packets = client_packets - server_packets
                total_expected = client_packets
            elif server_packets > client_packets:
                # Server has more packets (unusual case)
                lost_packets = server_packets - client_packets
                total_expected = server_packets
            else:
                # Equal packets - no loss
                lost_packets = 0
                total_expected = client_packets or server_packets

            if total_expected == 0:
                loss_percent = 0
            else:
                loss_percent = (lost_packets / total_expected) * 100

            writer.writerow(['Packet Loss (%)',
                            f"{loss_percent:.2f}",
                            'N/A',
                            f"{loss_percent:.2f}"])
        else:
            # For TCP protocols, use avg_loss_percent from summary
            client_loss = client_summary.get('avg_loss_percent', 0)
            server_loss = server_summary.get('avg_loss_percent', 0)
            avg_loss = (client_loss + server_loss) / 2 if (client_loss > 0 or server_loss > 0) else 0
            writer.writerow(['Packet Loss (%)',
                            f"{client_loss:.2f}",
                            f"{server_loss:.2f}",
                            f"{avg_loss:.2f}"])

        # Net Data Loss (bytes-based for all protocols)
        client_bytes = client_summary.get('total_bytes', 0)
        server_bytes = server_summary.get('total_bytes', 0)
        if server_bytes > 0:
            net_loss_percent = max(0, ((server_bytes - client_bytes) / server_bytes) * 100)
        else:
            net_loss_percent = 0
        writer.writerow(['Net Data Loss (%)',
                        f"{net_loss_percent:.2f}",
                        'N/A',
                        f"{net_loss_percent:.2f}"])

    print(f"✓ Combined CSV generated: {output_csv_path}")
    return output_csv_path


def wait_for_file(filepath, timeout=60, check_interval=1):
    """Wait for a file to be created"""
    import time
    elapsed = 0
    while elapsed < timeout:
        if os.path.exists(filepath):
            return True
        time.sleep(check_interval)
        elapsed += check_interval
    return False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python combine_metrics.py <client_json> <server_json> <output_csv>")
        print("\nExample:")
        print("  python combine_metrics.py results/bbr_client_metrics.json results/bbr_server_metrics.json results/bbr_combined_summary.csv")
        sys.exit(1)

    client_json = sys.argv[1]
    server_json = sys.argv[2]
    output_csv = sys.argv[3]

    # Wait for both JSON files to exist
    print(f"Waiting for client file: {client_json}")
    if not wait_for_file(client_json, timeout=120):
        print(f"✗ Timeout waiting for client file: {client_json}")
        sys.exit(1)

    print(f"Waiting for server file: {server_json}")
    if not wait_for_file(server_json, timeout=120):
        print(f"✗ Timeout waiting for server file: {server_json}")
        sys.exit(1)

    print("Both files found. Combining metrics...")
    combine_metrics(client_json, server_json, output_csv)
