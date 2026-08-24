import time
import os
from prometheus_client import Gauge, start_http_server

def read_cpu_times():
    with open("/proc/stat", "r") as f:
        for line in f:
            if line.startswith("cpu "):
                parts = line.split()
                values = list(map(int, parts[1:]))
                return values

    raise RuntimeError("CPU information not found")


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

    return (used / total) * 100

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

def main():
    previous = read_cpu_times()
    start_http_server(8000)
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

    process_count_prom = Gauge(
     "linux_process_count",
     "Number of running processes")
    
    while True:
        time.sleep(1)

        current = read_cpu_times()
        
        usage = calculate_cpu_usage(previous, current)
        memory_usage = read_memory_usage()
        load1, load5, load15 = read_load()
        context_switch = read_context_switches()
        process_count = read_process_count()
        """print(
            f"CPU usage:{usage:.2f}% "
        f"Memory:{memory_usage:.2f}% "
        f"Load:{load1:.2f}% "
        f"Context Switches:{context_switch} "
        f"No. of Processes Running:{process_count}"
        )"""
        cpu_usage_prom.set(usage)
        memory_usage_prom.set(memory_usage)
        load_1m_prom.set(load1)
        process_count_prom.set(process_count)
        previous = current


if __name__ == "__main__":
    main()
