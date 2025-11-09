import os
import subprocess

def get_env(key, default=None):
    value = os.environ.get(key)
    if value is None or value == '':
        return default
    return value

def build_tc_command():
    delay = get_env('DELAY')
    jitter = get_env('JITTER')
    loss = get_env('LOSS')
    bandwidth = get_env('BANDWIDTH')
    iface = 'eth0'
    netem = []
    if delay:
        if jitter:
            netem.append(f"delay {delay} {jitter}")
        else:
            netem.append(f"delay {delay}")
    if loss:
        netem.append(f"loss {loss}")
    if netem:
        cmd = f"tc qdisc replace dev {iface} root netem {' '.join(netem)}"
        return cmd
    return None

def build_tbf_command():
    bandwidth = get_env('BANDWIDTH')
    iface = 'eth0'
    if bandwidth:
        # Use 32kB burst and 400ms latency as defaults
        return f"tc qdisc replace dev {iface} root tbf rate {bandwidth} burst 32kbit latency 400ms"
    return None

def apply_netem():
    # Remove any existing qdisc
    subprocess.run("tc qdisc del dev eth0 root", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    tc_cmd = build_tc_command()
    tbf_cmd = build_tbf_command()
    print(f"Applying netem: {tc_cmd}")
    print(f"Applying tbf: {tbf_cmd}")
    if tc_cmd and tbf_cmd:
        # Combine: netem as root with handle 1:, tbf as child
        netem_cmd = tc_cmd.replace("root netem", "root handle 1: netem")
        print(f"Running: {netem_cmd}")
        subprocess.run(netem_cmd, shell=True, check=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        tbf_cmd_modified = tbf_cmd.replace("root tbf", "parent 1: handle 10: tbf")
        print(f"Running: {tbf_cmd_modified}")
        subprocess.run(tbf_cmd_modified, shell=True, check=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    elif tc_cmd:
        print(f"Running: {tc_cmd}")
        subprocess.run(tc_cmd, shell=True, check=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    elif tbf_cmd:
        print(f"Running: {tbf_cmd}")
        subprocess.run(tbf_cmd, shell=True, check=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

if __name__ == "__main__":
    apply_netem()
