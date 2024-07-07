from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import time
from utils import TicToc, FindPi
import logging

def monte_carlo_pi_multi(num_samples, num_threads):
    tt = TicToc()
    tt.tic()
    n = num_samples
    find_pis = []
    threads = []
    
    samples_per_thread = num_samples // num_threads

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(FindPi().throw_points_static, samples_per_thread) for _ in range(num_threads)]
        results = [future.result() for future in as_completed(futures)]

    inner = sum(res[0] for res in results)
    total = sum(res[1] for res in results)
    
    logging.info(f"PI = %.8f | I / N = %d / %d | TIME = %.5f seconds"
                 % (4 * inner / total, inner, total, tt.toc()))
    return 4 * inner / total
