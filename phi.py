import sys
import logging
import json
import psutil
import time
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import TicToc, FindPi
from monte_carlo import monte_carlo_pi_multi
from remote_tasks import ssh_connect, remote_monte_carlo_pi, read_hosts

logging.basicConfig(level=logging.INFO)


def measure_performance(func, *args):
    start_time = time.time()
    cpu_usage_start = psutil.cpu_percent(interval=None)
    memory_usage_start = psutil.virtual_memory().percent

    hasil = func(*args)

    cpu_usage_end = psutil.cpu_percent(interval=None)
    memory_usage_end = psutil.virtual_memory().percent
    end_time = time.time()
    execution_time = end_time - start_time
    execution_rate = hasil / execution_time if hasil else 0

    cpu_usage = (cpu_usage_start + cpu_usage_end) / 2
    memory_usage = (memory_usage_start + memory_usage_end) / 2

    logging.info(
        f"Performance metrics: CPU Usage = {cpu_usage:.2f}%, Memory Usage = {
            memory_usage:.2f}%, Execution Time = {execution_time:.2f} seconds, Execution Rate = {execution_rate:.2f} tasks/s"
    )

    return cpu_usage, memory_usage, execution_time, execution_rate, hasil


def plot_performance(local_data, cluster_data):
    labels = [
        "CPU Usage (%)",
        "Memory Usage (%)",
        "Execution Time (s)",
        "Execution Rate (tasks/s)",
    ]
    data_sources = []

    if local_data:
        local_means = np.mean([list(data[:4]) for data in local_data], axis=0)
        data_sources.append(("Local Machine", local_means))
    if cluster_data:
        cluster_means = np.mean([list(data[:4]) for data in cluster_data], axis=0)
        data_sources.append(("Cluster Machine", cluster_means))

    width = 0.35  # lebar bar
    fig, ax = plt.subplots()
    ind = np.arange(len(labels))

    for i, (label, means) in enumerate(data_sources):
        ax.barh(ind - width / 2 + i * width, means, width, label=label)

    ax.set(yticks=ind, yticklabels=labels, ylim=[2 * width - 1, len(labels)])
    ax.legend()

    plt.show()


def run_local_tasks():
    logging.info("Running tasks locally...")
    num_samples = 10**10
    num_threads = psutil.cpu_count(logical=True)
    result = monte_carlo_pi_multi(num_samples, num_threads)
    hasil = result
    return hasil


def run_cluster_tasks(hosts):
    logging.info("Running tasks in cluster...")
    num_samples = 10**10
    num_threads = psutil.cpu_count(logical=True)  # Get the number of CPU cores
    results = []

    with ThreadPoolExecutor(max_workers=len(hosts)) as executor:
        futures = [
            executor.submit(
                remote_monte_carlo_pi,
                ssh_connect(host),
                num_samples // len(hosts),
                num_threads,
            )
            for host in hosts
        ]
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)
                logging.info(f"Result: {result}")
    hasil = 0
    for i in range(len(hosts)):
        hasil += float(results[i])
    hasil = hasil / len(hosts)
    return hasil


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python phi.py [local|cluster]")
        sys.exit(1)

    mode = sys.argv[1]

    local_data = []
    cluster_data = []

    if mode == "local":
        local_data.append(measure_performance(run_local_tasks))
    elif mode == "cluster":
        hosts = read_hosts("hosts.json")
        try:
            cluster_data.append(measure_performance(run_cluster_tasks, hosts))
        except FileNotFoundError as e:
            logging.error(e)
            sys.exit(1)
    else:
        print("Invalid mode. Please use 'local' or 'cluster'.")
        sys.exit(1)

    if local_data:
        logging.info("Average Local Machine Performance:")
        logging.info(np.mean([list(data[:4]) for data in local_data], axis=0))
        logging.info(f"Local results: {local_data[-1][4]}")
    if cluster_data:
        cluster_data = [data for data in cluster_data if data[4]]
        if cluster_data:
            logging.info("Average Cluster Machine Performance:")
            logging.info(np.mean([list(data[:4]) for data in cluster_data], axis=0))
            logging.info(f"Cluster results: {cluster_data[-1][4]}")
        else:
            logging.info("No valid cluster results to display.")

    if local_data or cluster_data:
        plot_performance(local_data, cluster_data)
    else:
        logging.info("No data available for plotting.")
