# Transport Flow Protocol Comparison

This project compares the performance of TCP CUBIC, TCP BBR, and QUIC v1 under configurable network conditions using Docker containers. It automates network emulation, traffic capture, and metrics collection for fair protocol evaluation.

## Protocols Tested

- **TCP CUBIC**: Default congestion control in Linux
- **TCP BBR**: Bottleneck Bandwidth and Round-trip propagation time
- **QUIC v1**: Modern transport protocol over UDP

## Requirements

- **Docker Desktop** (Windows/macOS) or **Docker Engine** (Linux)
- **docker-compose**
- 2GB+ RAM recommended
- Network capabilities: NET_ADMIN (for tc netem)

### Platform Support

Runs on any platform with Docker:

- Windows 10/11 (Docker Desktop with WSL2)
- Linux (native Docker)
- macOS (Docker Desktop)

## Quick Start

1. Edit `config.env` to set network conditions and test parameters
2. Run all protocols:
   ```bash
   docker-compose --profile all up --build
   ```
3. Results are saved in the `results/` folder

### Individual Protocols

```bash
docker-compose --profile bbr up --build
docker-compose --profile cubic up --build
docker-compose --profile quic up --build
```

## Configuration

Network conditions and test parameters are defined in `config.env`:

```bash
# Network Conditions
DELAY=50ms        # Network delay (e.g., 0ms, 50ms, 200ms)
JITTER=10ms       # Delay variation (optional, leave empty to disable)
LOSS=1%           # Packet loss percentage (e.g., 0%, 1%, 5%, 15%)
BANDWIDTH=20mbit  # Bandwidth limit (e.g., 1mbit, 20mbit, 1000mbit)

# Test Parameters
TEST_DURATION=30  # Test duration in seconds (e.g., 15, 30, 60, 120)
QUIC_TRANSFERS=5  # Number of parallel QUIC transfers (1-10)
QUIC_DATA_SIZE_MB=5  # Data size per QUIC stream in MB (max 10)

# TCP Parameters (BBR/CUBIC)
TCP_PARALLEL_STREAMS=5  # Number of parallel TCP streams (1-8)
TCP_WINDOW_SIZE=        # TCP buffer size (e.g., 64K, 128K, 1M) - leave empty for auto
```

## Architecture

The project uses 6 Docker containers in an isolated bridge network:

- TCP servers/clients using iperf3 (BBR/CUBIC)
- QUIC servers/clients using aioquic
- Network emulation via tc netem
- Real-time metrics capture and PCAP analysis

## Scripts and Tools

### Main Scripts

- **`capture_metrics_live.py`**: Real-time network metrics capture (packets, bandwidth, jitter, retransmissions)
- **`analyze_pcap.py`**: PCAP file analysis and summary generation
- **`apply_netem.py`**: Applies network conditions using tc netem
- **`json_to_csv.py`**: Converts JSON metrics to CSV format

### Post-Processing Scripts

Located in `scripts/post_processing/`:

- **`analyze_metrics.py`**: Performs comprehensive analysis of protocol metrics including bandwidth stability assessment, identification of problematic seconds (high loss or jitter), and comparative ranking of protocols by performance metrics. Generates detailed summaries and exports comparison tables to CSV.
- **`plot_comparison.py`**: Creates visual comparative plots of protocol performance metrics, helping to visualize differences in bandwidth, jitter, and loss across BBR, CUBIC, and QUIC protocols.

### Workflow

**During Test:**

1. Apply network conditions
2. Run protocol test
3. All metrics in results folder

## Output Files

Results are saved in `results/`:

### Capture Files

- **PCAP files**: Raw packet captures (`*_client.pcap`, `*_server.pcap`)
- **JSON files**: Second-by-second metrics (`*_metrics.json`)

### Analysis Files

- **Per-second CSV**: Timestamped metrics for each second
- **Summary CSV**: Overall statistics combining client/server data

### Metrics Captured

- Packets per second
- Bandwidth (Mbps)
- Jitter (ms)
- Retransmissions (TCP only)
- Packet loss percentage

## Dependencies

### Python Packages

- `scapy` - Packet analysis
- `aioquic` - QUIC protocol (QUIC containers only)

### System Packages

- `tcpdump` - Packet capture
- `iproute2` - Network tools (tc)
- `iperf3` - TCP tests

## Troubleshooting

### Common Issues

**Docker network overlap error**

```bash
docker network prune -f
```

**Empty/incomplete results**

- Check Docker logs: `docker-compose logs <service>`
- Verify network conditions in `config.env`
- Ensure correct ports (TCP: 5201, QUIC: 443)

## Technical Details

### Congestion Control

Algorithms are activated via sysctl (already in Linux kernel):

- BBR: `sysctl -w net.ipv4.tcp_congestion_control=bbr`
- CUBIC: `sysctl -w net.ipv4.tcp_congestion_control=cubic`

### Network Emulation

Uses `tc netem` for delay/jitter/loss and `tc tbf` for bandwidth limits.

### Packet Analysis

- TCP: Retransmission detection via sequence numbers
- QUIC: Loss calculated from client-server packet asymmetry

## Contributing

Feel free to open issues or submit pull requests for improvements.
