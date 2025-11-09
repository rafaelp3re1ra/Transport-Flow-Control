#!/usr/bin/env python3
"""
TCP iperf3 Client - works with any congestion control (BBR, CUBIC, etc.)
Congestion control is set via sysctl in the Dockerfile
"""
import subprocess
import sys
import os

def main():
    server = sys.argv[1] if len(sys.argv) > 1 else "tcp_server"
    duration = int(os.environ.get('TEST_DURATION', 30))
    parallel = int(os.environ.get('TCP_PARALLEL_STREAMS', 5))
    window = os.environ.get('TCP_WINDOW_SIZE', '')
    cc_algorithm = os.environ.get('TCP_CONGESTION_CONTROL', 'cubic')
    
    print(f"Starting iperf3 client with {cc_algorithm.upper()} congestion control")
    print(f"Server: {server}, Duration: {duration}s, Parallel streams: {parallel}")
    
    cmd = f"iperf3 -c {server} -t {duration} -P {parallel}"
    if window:
        cmd += f" -w {window}"
    
    subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    main()
