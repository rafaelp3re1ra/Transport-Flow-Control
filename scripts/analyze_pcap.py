import sys
from scapy.all import rdpcap, TCP, UDP, IP
import os
import csv

def analyze_pcap(pcap_path, protocol):
    packets = rdpcap(pcap_path)
    if not packets:
        print("No packets in pcap")
        return {}

    start_time = packets[0].time
    end_time = packets[-1].time
    duration = end_time - start_time
    if duration == 0:
        duration = 1  # avoid div by zero

    total_bytes = sum(len(pkt) for pkt in packets)
    bandwidth_mbps = (total_bytes * 8) / (duration * 1000000)  # Mbps

    # Calculate jitter (variation in packet arrival times)
    jitter_ms = 0
    if len(packets) > 1:
        inter_arrival_times = []
        for i in range(1, len(packets)):
            inter_arrival_times.append((packets[i].time - packets[i-1].time) * 1000)  # Convert to ms
        if len(inter_arrival_times) > 1:
            # Jitter is the average deviation in inter-arrival times
            mean_iat = sum(inter_arrival_times) / len(inter_arrival_times)
            jitter_ms = sum(abs(iat - mean_iat) for iat in inter_arrival_times) / len(inter_arrival_times)

    retransmissions = 0
    loss_estimate = 0
    rtt_ms = 'N/A'

    if protocol.lower() == 'tcp':
        seq_nums = {}
        syn_ack_times = {}  # Track SYN-ACK for RTT estimation
        
        for pkt in packets:
            if TCP in pkt and IP in pkt:
                src = pkt[IP].src
                dst = pkt[IP].dst
                seq = pkt[TCP].seq
                ack = pkt[TCP].ack
                flags = pkt[TCP].flags
                
                # RTT estimation: SYN -> SYN-ACK time
                if flags & 0x02 and not (flags & 0x10):  # SYN without ACK
                    syn_ack_times[(src, dst)] = pkt.time
                elif flags & 0x12:  # SYN-ACK
                    key = (dst, src)
                    if key in syn_ack_times:
                        rtt_estimate = (pkt.time - syn_ack_times[key]) * 1000  # ms
                        if rtt_ms == 'N/A':
                            rtt_ms = rtt_estimate
                        else:
                            rtt_ms = (rtt_ms + rtt_estimate) / 2  # Average RTT
                
                # Retransmission detection
                key = (src, dst, seq)
                if key in seq_nums:
                    retransmissions += 1
                else:
                    seq_nums[key] = True
        
        # Rough loss estimate: retransmissions / total packets
        total_tcp_packets = sum(1 for pkt in packets if TCP in pkt)
        if total_tcp_packets > 0:
            loss_estimate = (retransmissions / total_tcp_packets) * 100
    elif protocol.lower() == 'udp':
        # For UDP/QUIC, retransmissions not directly visible
        retransmissions = 'N/A'
        loss_estimate = 'N/A'

    metrics = {
        'duration_seconds': duration,
        'total_packets': len(packets),
        'total_bytes': total_bytes,
        'bandwidth_mbps': bandwidth_mbps,
        'jitter_ms': jitter_ms,
        'rtt_ms': rtt_ms,
        'retransmissions': retransmissions,
        'estimated_loss_percent': loss_estimate
    }

    print(f"Duration: {duration:.2f} seconds")
    print(f"Total packets: {len(packets)}")
    print(f"Total bytes: {total_bytes}")
    print(f"Bandwidth: {bandwidth_mbps:.2f} Mbps")
    print(f"Jitter: {jitter_ms:.2f} ms")
    print(f"RTT: {rtt_ms if rtt_ms == 'N/A' else f'{rtt_ms:.2f} ms'}")
    print(f"Retransmissions: {retransmissions}")
    print(f"Estimated loss: {loss_estimate}%")

    return metrics

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python analyze_pcap.py <protocol> <client_pcap> [server_pcap] [csv_path]")
        sys.exit(1)
    protocol = sys.argv[1]
    client_pcap = sys.argv[2]
    server_pcap = sys.argv[3] if len(sys.argv) > 3 and '.pcap' in sys.argv[3] else None
    csv_path = sys.argv[4] if len(sys.argv) > 4 else (sys.argv[3] if len(sys.argv) > 3 and '.csv' in sys.argv[3] else None)
    
    # Determine protocol name
    pcap_filename = os.path.basename(client_pcap)
    if 'bbr' in pcap_filename.lower():
        protocol_name = 'BBR'
    elif 'cubic' in pcap_filename.lower():
        protocol_name = 'CUBIC'
    elif 'quic' in pcap_filename.lower():
        protocol_name = 'QUIC'
    else:
        protocol_name = protocol.upper()
    
    client_metrics = analyze_pcap(client_pcap, protocol)
    server_metrics = analyze_pcap(server_pcap, protocol) if server_pcap and os.path.exists(server_pcap) else None
    
    if csv_path:
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Congestion Control Protocol', protocol_name])
            writer.writerow([])
            
            if server_metrics:
                writer.writerow(['Metric Name', 'Client', 'Server', 'Total/Average'])
                writer.writerow(['Duration (seconds)', f"{client_metrics['duration_seconds']:.2f}", f"{server_metrics['duration_seconds']:.2f}", f"{max(client_metrics['duration_seconds'], server_metrics['duration_seconds']):.2f}"])
                writer.writerow(['Total Packets', client_metrics['total_packets'], server_metrics['total_packets'], client_metrics['total_packets'] + server_metrics['total_packets']])
                writer.writerow(['Total Bytes', client_metrics['total_bytes'], server_metrics['total_bytes'], client_metrics['total_bytes'] + server_metrics['total_bytes']])
                writer.writerow(['Bandwidth (Mbps)', f"{client_metrics['bandwidth_mbps']:.2f}", f"{server_metrics['bandwidth_mbps']:.2f}", f"{(client_metrics['bandwidth_mbps'] + server_metrics['bandwidth_mbps'])/2:.2f}"])
                writer.writerow(['Jitter (ms)', f"{client_metrics['jitter_ms']:.2f}", f"{server_metrics['jitter_ms']:.2f}", f"{(client_metrics['jitter_ms'] + server_metrics['jitter_ms'])/2:.2f}"])
                
                # RTT
                client_rtt = client_metrics['rtt_ms']
                server_rtt = server_metrics['rtt_ms']
                if client_rtt != 'N/A' and server_rtt != 'N/A':
                    avg_rtt = (client_rtt + server_rtt) / 2
                    writer.writerow(['RTT (ms)', f"{client_rtt:.2f}", f"{server_rtt:.2f}", f"{avg_rtt:.2f}"])
                else:
                    writer.writerow(['RTT (ms)', client_rtt if client_rtt == 'N/A' else f"{client_rtt:.2f}", server_rtt if server_rtt == 'N/A' else f"{server_rtt:.2f}", 'N/A'])
                
                if client_metrics['retransmissions'] != 'N/A':
                    writer.writerow(['Retransmissions', client_metrics['retransmissions'], server_metrics['retransmissions'], client_metrics['retransmissions'] + server_metrics['retransmissions']])
                    writer.writerow(['Packet Loss (%)', f"{client_metrics['estimated_loss_percent']:.2f}", f"{server_metrics['estimated_loss_percent']:.2f}", f"{(client_metrics['estimated_loss_percent'] + server_metrics['estimated_loss_percent'])/2:.2f}"])
                else:
                    writer.writerow(['Retransmissions', 'N/A', 'N/A', 'N/A'])
                    writer.writerow(['Packet Loss (%)', 'N/A', 'N/A', 'N/A'])
            else:
                writer.writerow(['Metric Name', 'Value'])
                writer.writerow(['Duration (seconds)', f"{client_metrics['duration_seconds']:.2f}"])
                writer.writerow(['Total Packets', client_metrics['total_packets']])
                writer.writerow(['Total Bytes', client_metrics['total_bytes']])
                writer.writerow(['Bandwidth (Mbps)', f"{client_metrics['bandwidth_mbps']:.2f}"])
                writer.writerow(['Jitter (ms)', f"{client_metrics['jitter_ms']:.2f}"])
                writer.writerow(['RTT (ms)', client_metrics['rtt_ms'] if client_metrics['rtt_ms'] == 'N/A' else f"{client_metrics['rtt_ms']:.2f}"])
                writer.writerow(['Retransmissions', client_metrics['retransmissions']])
                writer.writerow(['Packet Loss (%)', client_metrics['estimated_loss_percent'] if client_metrics['estimated_loss_percent'] == 'N/A' else f"{client_metrics['estimated_loss_percent']:.2f}"])
        print(f"Metrics saved to {csv_path}")