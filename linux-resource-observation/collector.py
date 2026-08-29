import time
import os
import logging
from prometheus_client import Gauge, start_http_server, Counter

EXPORT_PORT = 8000
COLLECTION_INTERVAL = 1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger(__name__)

cpu_usage_prom = Gauge(
    "linux_cpu_usage_percent",
    "CPU utilization percentage")

memory_usage_prom = Gauge(
     "linux_memory_usage_percent",
     "Memory utilization percentage"
    )

load_1m_prom = Gauge(
      "linux_load_average_1m",
      "1 minute load average")
load_5m_prom = Gauge(
    "linux_load_average_5m",
    "5 minute load average"
)

load_15m_prom = Gauge(
    "linux_load_average_15m",
    "15 minute load average"
)
process_count_prom = Gauge(
     "linux_process_count",
     "Number of running processes")

memory_total_prom = Gauge(
    "linux_memory_total_bytes",
    "Total system memory"
)

memory_available_prom = Gauge(
    "linux_memory_available_bytes",
    "Available system memory"
)

memory_used_prom = Gauge(
    "linux_memory_used_bytes",
    "Used system memory"
)

swap_total_prom = Gauge(
    "linux_swap_total_bytes",
    "Total swap space"
)

swap_free_prom = Gauge(
    "linux_swap_free_bytes",
    "Free swap space"
)

swap_used_prom = Gauge(
    "linux_swap_used_bytes",
    "Used swap space"
)

context_switches_total_prom = Counter(
    "linux_context_switches_total",
    "Total number of context switches"
)

network_receive_bytes_total_prom = Counter(
    "linux_network_receive_bytes_total",
    "Total bytes received",
    ["interface"]
)

network_transmit_bytes_total_prom = Counter(
    "linux_network_transmit_bytes_total",
    "Total bytes transmitted",
    ["interface"]
)

network_receive_errors_total_prom = Counter(
    "linux_network_receive_errors_total",
    "Total received network errors",
    ["interface"]
)

network_transmit_errors_total_prom = Counter(
    "linux_network_transmit_errors_total",
    "Total transmitted network errors",
    ["interface"]
)

network_receive_drops_total_prom = Counter(
    "linux_network_receive_drops_total",
    "Total received network packets dropped",
    ["interface"]
)

network_transmit_drops_total_prom = Counter(
    "linux_network_transmit_drops_total",
    "Total transmitted network packets dropped",
    ["interface"]
)

disk_reads_total_prom = Counter(
    "linux_disk_reads_total",
    "Total disk read operations",
    ["device"]
)

disk_writes_total_prom = Counter(
    "linux_disk_writes_total",
    "Total disk write operations",
    ["device"]
)

disk_read_bytes_total_prom = Counter(
    "linux_disk_read_bytes_total",
    "Total bytes read from disk",
    ["device"]
)

disk_write_bytes_total_prom = Counter(
    "linux_disk_write_bytes_total",
    "Total bytes written to disk",
    ["device"]
)


def read_cpu_times():
    cpu_data = {}

    with open("/proc/stat", "r") as file:
        for line in file:

            if not line.startswith("cpu"):
                continue

            parts = line.split()

            if parts[0] == "cpu" or parts[0].startswith("cpu"):
                try:
                    values = list(map(int, parts[1:]))
                    cpu_data[parts[0]] = values
                except ValueError:
                    continue

    return cpu_data


def calculate_cpu_usage(previous, current):
    previous_total = sum(previous)
    current_total = sum(current)

    previous_idle = previous[3] + previous[4]
    current_idle = current[3] + current[4]

    total_delta = current_total - previous_total
    idle_delta = current_idle - previous_idle

    if total_delta == 0:
        return 0.0

    busy_delta = total_delta - idle_delta

    return (busy_delta / total_delta) * 100


def read_memory_usage():
    memory = {}

    with open("/proc/meminfo", "r") as f:
        for line in f:
            key, value = line.split(":")
            memory[key] = int(value.split()[0])

    total = memory["MemTotal"]
    available = memory["MemAvailable"]

    used = total - available
    swap_total_value = memory.get("SwapTotal", 0)
    swap_free_value = memory.get("SwapFree", 0)

    swap_used_value = swap_total_value - swap_free_value
    return (total,available,used,swap_total_value,swap_free_value,swap_used_value)

def read_load():

    with open("/proc/loadavg", "r") as f:
        for line in f:
            values = line.split()

    return float(values[0]),float(values[1]),float(values[2])


def read_context_switches():
    with open("/proc/stat", "r") as f:
        for line in f:
            if line.startswith("ctxt "):
                return int(line.split()[1])

    raise RuntimeError("Context switch counter not found")

def read_process_count():
    count = 0

    for entry in os.listdir("/proc"):
        if entry.isdigit():
            count += 1

    return count

def read_disk_stats():

    disks = {}

    with open("/proc/diskstats", "r") as file:
        for line in file:
            parts = line.split()
            if len(parts) < 14:
                continue
            device = parts[2]
            try:
                reads_completed = int(parts[3])
                sectors_read = int(parts[5])
                writes_completed = int(parts[7])
                sectors_written = int(parts[9])

            except ValueError:
                continue

            # Linux sector size is normally 512 bytes.
            bytes_read = sectors_read * 512
            bytes_written = sectors_written * 512

            disks[device] = {
                "reads": reads_completed,
                "writes": writes_completed,
                "read_bytes": bytes_read,
                "write_bytes": bytes_written,
            }

    return disks

def read_network_stats():

    interfaces = {}

    with open("/proc/net/dev", "r") as file:

        for line in file:

            if ":" not in line:
                continue

            interface, data = line.split(":", 1)
            interface = interface.strip()
            values = data.split()
            if len(values) < 16:
                continue
            try:

                interfaces[interface] = {
                    "rx_bytes": int(values[0]),
                    "rx_packets": int(values[1]),
                    "rx_errors": int(values[2]),
                    "rx_drops": int(values[3]),

                    "tx_bytes": int(values[8]),
                    "tx_packets": int(values[9]),
                    "tx_errors": int(values[10]),
                    "tx_drops": int(values[11]),
                }

            except ValueError:
                continue

    return interfaces


def collection_metrics(previous_cpu_time,previous_network_stats,previous_disks_stats):

    current_cpu_time = read_cpu_times()

    if "cpu" in previous_cpu_time and "cpu" in current_cpu_time:

        usage = calculate_cpu_usage(previous_cpu_time["cpu"], current_cpu_time["cpu"])

    load1m,load5m,load15m = read_load()
    total,available,used,swap_total_value,swap_free_value,swap_used_value = read_memory_usage()
    
    process_count = read_process_count()
    
    
    memory_total_prom.set(total)
    memory_available_prom.set(available)
    memory_used_prom.set(used)

    if total > 0:
        memory_usage_prom.set((used / total) * 100)

     
    current_context_switches = read_context_switches()

    if collection_metrics.previous_context_switches is not None:

        delta = current_context_switches - collection_metrics.previous_context_switches

        if delta > 0:
            context_switches_total_prom.inc(delta)

    collection_metrics.previous_context_switches = current_context_switches
    
    cuurent_network_stats = read_network_stats()

    for interface, stats in cuurent_network_stats.items():

        if interface not in previous_network_stats:
            continue

        previous = previous_network_stats[interface]

        rx_bytes_delta = max(0,stats["rx_bytes"] - previous["rx_bytes"])
        tx_bytes_delta = max(0,stats["tx_bytes"] - previous["tx_bytes"])
        rx_errors_delta = max(0,stats["rx_errors"] - previous["rx_errors"])
        tx_errors_delta = max(0,stats["tx_errors"] - previous["tx_errors"])
        rx_drops_delta = max(0,stats["rx_drops"] - previous["rx_drops"])
        tx_drops_delta = max(0,stats["tx_drops"] - previous["tx_drops"])

        if rx_bytes_delta:
            network_receive_bytes_total_prom.labels(interface=interface).inc(rx_bytes_delta)

        if tx_bytes_delta:
            network_transmit_bytes_total_prom.labels(interface=interface).inc(tx_bytes_delta)

        if rx_errors_delta:
            network_receive_errors_total_prom.labels(interface=interface).inc(rx_errors_delta)

        if tx_errors_delta:
            network_transmit_errors_total_prom.labels(interface=interface).inc(tx_errors_delta)

        if rx_drops_delta:
            network_receive_drops_total_prom.labels(interface=interface).inc(rx_drops_delta)

        if tx_drops_delta:
            network_transmit_drops_total_prom.labels(interface=interface).inc(tx_drops_delta)
    

    current_disks_stats = read_disk_stats()

    for device, stats in current_disks_stats.items():

        # Avoid counting partitions such as sda1/sda2
        # as independent physical devices in this simple lab.
        if device not in previous_disks_stats:
            continue

        previous = previous_disks_stats[device]
        reads_delta = max(0,stats["reads"] - previous["reads"])
        writes_delta = max(0,stats["writes"] - previous["writes"])
        read_bytes_delta = max(0, stats["read_bytes"] - previous["read_bytes"])
        write_bytes_delta = max(0, stats["write_bytes"] - previous["write_bytes"])

        if reads_delta:
            disk_reads_total_prom.labels(device=device).inc(reads_delta)
        if writes_delta:
            disk_writes_total_prom.labels(device=device).inc(writes_delta)
        if read_bytes_delta:
            disk_read_bytes_total_prom.labels(device=device).inc(read_bytes_delta)
        if write_bytes_delta:
            disk_write_bytes_total_prom.labels(device=device).inc(write_bytes_delta)

    swap_total_prom.set(swap_total_value)
    swap_free_prom.set(swap_free_value)
    swap_used_prom.set(swap_used_value)
    process_count_prom.set(process_count)
    cpu_usage_prom.set(usage)
    load_1m_prom.set(load1m)
    load_5m_prom.set(load5m)
    load_15m_prom.set(load15m)

    return current_cpu_time,cuurent_network_stats,current_disks_stats

# Static variable
collection_metrics.previous_context_switches = None

def main():

    logger.info("Starting Linux Resource Observatory on port %s",EXPORT_PORT)
    start_http_server(EXPORT_PORT)
    previous_cpu_time = read_cpu_times()
    previous_network_stats = read_network_stats()
    previous_disks_stats = read_disk_stats()
    
    while True:
        time.sleep(COLLECTION_INTERVAL)  
        previous_cpu_time,previous_network_stats,previous_disks_stats = collection_metrics(previous_cpu_time,previous_network_stats,previous_disks_stats)

if __name__ == "__main__":
    main()
