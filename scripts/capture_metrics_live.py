import subprocess
import sys
import time
import os
import signal
import json
import csv
from datetime import datetime
from scapy.all import sniff, TCP, UDP, IP
import threading

class LiveMetricsCollector:
    def __init__(self, protocol, iface, port, json_path):
        self.protocol = protocol
        self.iface = iface
        self.port = port
        self.json_path = json_path
        self.metrics_per_second = []
        self.current_second_data = {
            'packets': [],
            'bytes': 0,
            'retrans': 0,
            'seq_nums': {}
        }
        self.start_time = None
        self.current_second = 0
        self.running = True
        self.lock = threading.Lock()
        
    def packet_callback(self, pkt):
        if not self.running:
            return False  # Stop sniffing
            
        current_time = time.time()
        if self.start_time is None:
            self.start_time = current_time
            
        elapsed = current_time - self.start_time
        second = int(elapsed)
        
        with self.lock:
            # If second changed, save metrics from previous second
            if second > self.current_second:
                self._save_second_metrics()
                self.current_second = second

            # Process current packet
            pkt_size = len(pkt)
            self.current_second_data['packets'].append({
                'time': current_time,
                'size': pkt_size
            })
            self.current_second_data['bytes'] += pkt_size
            
            # Detecta retransmissões (TCP)
            if self.protocol.lower() == 'tcp' and TCP in pkt and IP in pkt:
                src = pkt[IP].src
                dst = pkt[IP].dst
                seq = pkt[TCP].seq
                key = (src, dst, seq)
                
                if key in self.current_second_data['seq_nums']:
                    self.current_second_data['retrans'] += 1
                else:
                    self.current_second_data['seq_nums'][key] = True
    
    def _save_second_metrics(self):
        """Save metrics for the current second"""
        if not self.current_second_data['packets']:
            return

        packets = self.current_second_data['packets']
        num_packets = len(packets)
        total_bytes = self.current_second_data['bytes']

        # Calculate bandwidth (Mbps) for this second
        bandwidth_mbps = (total_bytes * 8) / 1000000

        # Calculate jitter (variation in packet arrival times)
        jitter_ms = 0
        if num_packets > 1:
            inter_arrival_times = []
            for i in range(1, len(packets)):
                iat = (packets[i]['time'] - packets[i-1]['time']) * 1000  # ms
                inter_arrival_times.append(iat)

            if inter_arrival_times:
                mean_iat = sum(inter_arrival_times) / len(inter_arrival_times)
                jitter_ms = sum(abs(iat - mean_iat) for iat in inter_arrival_times) / len(inter_arrival_times)

        # Calculate loss rate
        loss_percent = 0
        if self.protocol.lower() == 'tcp' and num_packets > 0:
            loss_percent = (self.current_second_data['retrans'] / num_packets) * 100

        metrics = {
            'second': self.current_second,
            'timestamp': datetime.now().isoformat(),
            'packets': num_packets,
            'bytes': total_bytes,
            'bandwidth_mbps': round(bandwidth_mbps, 2),
            'jitter_ms': round(jitter_ms, 2),
            'retransmissions': self.current_second_data['retrans'],
            'loss_percent': round(loss_percent, 2)
        }

        self.metrics_per_second.append(metrics)

        # Reset for next second
        self.current_second_data = {
            'packets': [],
            'bytes': 0,
            'retrans': 0,
            'seq_nums': {}
        }
    
    def start_capture(self):
        """Start packet capture in a separate thread"""
        def capture_thread():
            # Filter packets by specified port
            if self.protocol.lower() == 'tcp':
                filter_str = f'tcp port {self.port}'
            elif self.protocol.lower() == 'udp':
                filter_str = f'udp port {self.port}'
            else:
                filter_str = f'port {self.port}'

            sniff(iface=self.iface, filter=filter_str, prn=self.packet_callback,
                  stop_filter=lambda x: not self.running, store=False)

        self.capture_thread = threading.Thread(target=capture_thread, daemon=True)
        self.capture_thread.start()

    def stop_capture(self):
        """Stop capture and save final metrics"""
        self.running = False
        time.sleep(1)  # Wait for thread to finish

        with self.lock:
            # Save metrics for last second if any
            if self.current_second_data['packets']:
                self._save_second_metrics()

        # Save complete JSON
        self._save_json()

    def _save_json(self):
        """Save all metrics in JSON format"""
        output = {
            'protocol': self.protocol,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            'end_time': datetime.now().isoformat(),
            'total_duration_seconds': self.current_second + 1,
            'metrics_per_second': self.metrics_per_second,
            'summary': self._calculate_summary()
        }
        
        with open(self.json_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"JSON metrics saved to {self.json_path}")

    def _calculate_summary(self):
        """Calculate summary metrics for the entire test"""
        if not self.metrics_per_second:
            return {}

        total_packets = sum(m['packets'] for m in self.metrics_per_second)
        total_bytes = sum(m['bytes'] for m in self.metrics_per_second)
        avg_bandwidth = sum(m['bandwidth_mbps'] for m in self.metrics_per_second) / len(self.metrics_per_second)
        avg_jitter = sum(m['jitter_ms'] for m in self.metrics_per_second) / len(self.metrics_per_second)
        total_retrans = sum(m['retransmissions'] for m in self.metrics_per_second)
        avg_loss = sum(m['loss_percent'] for m in self.metrics_per_second) / len(self.metrics_per_second)

        return {
            'total_packets': total_packets,
            'total_bytes': total_bytes,
            'avg_bandwidth_mbps': round(avg_bandwidth, 2),
            'avg_jitter_ms': round(avg_jitter, 2),
            'total_retransmissions': total_retrans,
            'avg_loss_percent': round(avg_loss, 2)
        }


def generate_timeline_csv(json_path, timeline_csv_path):
    """Generate a CSV with only per-second metrics (timeline)"""
    with open(json_path, 'r') as f:
        data = json.load(f)

    with open(timeline_csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Header
        writer.writerow(['Second', 'Timestamp', 'Packets', 'Bytes', 'Bandwidth (Mbps)',
                        'Jitter (ms)', 'Retransmissions', 'Loss (%)'])

        # Per-second data (timeline only, no summary)
        for metric in data['metrics_per_second']:
            writer.writerow([
                metric['second'],
                metric['timestamp'],
                metric['packets'],
                metric['bytes'],
                metric['bandwidth_mbps'],
                metric['jitter_ms'],
                metric['retransmissions'],
                metric['loss_percent']
            ])

    print(f"Timeline CSV saved to {timeline_csv_path}")


def generate_summary_csv(json_path, summary_csv_path):
    """Generate a CSV with only summary statistics (summary)"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

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

    print(f"Summary CSV saved to {summary_csv_path}")


def run_capture_and_command(protocol, iface, port, pcap_path, json_path, command, timeline_csv_path=None, summary_csv_path=None):
    """
    Run packet capture with real-time metrics
    """
    # Start tcpdump for PCAP file (maintain compatibility)
    tcpdump_cmd = [
        'tcpdump', '-i', iface, f'{protocol} port {port}', '-w', pcap_path
    ]
    tcpdump_proc = subprocess.Popen(tcpdump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    # Start live metrics collector
    collector = LiveMetricsCollector(protocol, iface, port, json_path)
    collector.start_capture()
    time.sleep(1)

    # Run protocol command
    try:
        test_duration = int(os.environ.get('TEST_DURATION', 30))
        result = subprocess.run(command, shell=True, timeout=test_duration + 5)
    except subprocess.TimeoutExpired:
        print(f"Command timed out after {test_duration} seconds")
    finally:
        # Stop metrics collector
        collector.stop_capture()

        # Stop tcpdump
        tcpdump_proc.send_signal(signal.SIGINT)
        tcpdump_proc.wait()

    print(f"PCAP saved to {pcap_path}")

    # Generate separate CSVs from JSON
    if timeline_csv_path:
        generate_timeline_csv(json_path, timeline_csv_path)
    if summary_csv_path:
        generate_summary_csv(json_path, summary_csv_path)


if __name__ == "__main__":
    # Usage: python capture_metrics_live.py <protocol> <iface> <port> <pcap_path> <json_path> <command> [timeline_csv_path] [summary_csv_path]
    if len(sys.argv) < 7:
        print("Usage: python capture_metrics_live.py <protocol> <iface> <port> <pcap_path> <json_path> <command> [timeline_csv_path] [summary_csv_path]")
        sys.exit(1)

    protocol = sys.argv[1]
    iface = sys.argv[2]
    port = sys.argv[3]
    pcap_path = sys.argv[4]
    json_path = sys.argv[5]
    command = sys.argv[6]
    timeline_csv_path = sys.argv[7] if len(sys.argv) > 7 else None
    summary_csv_path = sys.argv[8] if len(sys.argv) > 8 else None

    run_capture_and_command(protocol, iface, port, pcap_path, json_path, command, timeline_csv_path, summary_csv_path)
