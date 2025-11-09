#!/usr/bin/env python3
"""
TCP iperf3 Server - works with any congestion control (BBR, CUBIC, etc.)
Congestion control is set via sysctl in the Dockerfile
"""
import subprocess
import os

def main():
    cc_algorithm = os.environ.get('TCP_CONGESTION_CONTROL', 'cubic')
    print(f"Starting iperf3 server with {cc_algorithm.upper()} congestion control")
    subprocess.run("iperf3 -s -1 -p 5201", shell=True)

if __name__ == "__main__":
    main()
