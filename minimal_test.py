import threading
import queue
import signal
import time
import asyncio
import psutil
import logging

class EventDrivenQueueProcessor:
    def __init__(self, worker_count=10, min_workers=1, max_workers=20, scale_threshold=5, scale_down_delay=30):
        self.task_queue = queue.Queue()
        self.initial_worker_count = worker_count
        self.max_workers = max_workers
        self.min_workers = min_workers
        self.scale_threshold = scale_threshold
        self.workers = []
        self.stop_event = threading.Event()
        self.producer_thread = None
        self.monitor_thread = None
        self.completed_tasks = 0
        self.error_count = 0
        self.lock = threading.Lock()
        self.last_scale_down_time = 0
        self.scale_down_delay = scale_down_delay  # Minimum time (seconds) between scale-downs

        # Set up logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)

    def start_workers(self, worker_func, count):
        for _ in range(count):
            worker = threading.Thread(target=self.worker_process, args=(worker_func,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)

    def start_producer(self, producer_func):
        self.producer_thread = threading.Thread(target=self.run_producer, args=(producer_func,))
        self.producer_thread.daemon = True
        self.producer_thread.start()

    def run_producer(self, producer_func):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(producer_func(self.task_queue, self.stop_event))
        except Exception as e:
            self.logger.error(f"Producer encountered an exception: {e}")
        finally:
            loop.close()

    def worker_process(self, worker_func):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def process_tasks():
            while not self.stop_event.is_set() or not self.task_queue.empty():
                try:
                    task = self.task_queue.get(timeout=0.5)
                    if task is None:  # Poison pill received
                        self.task_queue.task_done()
                        break
                    await worker_func(task)
                    self.task_queue.task_done()
                    with self.lock:
                        self.completed_tasks += 1
                except queue.Empty:
                    continue
                except Exception as e:
                    with self.lock:
                        self.error_count += 1
                    self.logger.error(f"Worker encountered an exception: {e}")

        try:
            loop.run_until_complete(process_tasks())
        finally:
            # Remove the current worker from the workers list on termination
            with self.lock:
                self.workers.remove(threading.current_thread())
            loop.close()

    def wait_for_completion(self):
        while True:
            with self.lock:
                # Check if all worker threads have finished
                if len(self.workers) == 0:
                    break
            # Sleep for a short while to avoid busy-waiting
            time.sleep(1)

    def signal_handler(self, signum, frame):
        self.logger.info("Termination signal received")
        self.stop_event.set()

    def monitor_system(self, worker_func):
        while not self.stop_event.is_set():
            # Sleep before the next monitoring check
            time.sleep(5)

            with self.lock:
                queue_size = self.task_queue.qsize()
                current_worker_count = len(self.workers)

            # Scale up workers if the queue size exceeds the threshold and we haven't reached max_workers
            if queue_size > self.scale_threshold and current_worker_count < self.max_workers:
                self.logger.info(f"Scaling up: Adding workers (Current: {current_worker_count})")
                additional_workers = max(min(int((((max(queue_size - self.scale_threshold, 0)) * 0.2) ** 1.3)), self.max_workers - current_worker_count), 0)
                self.start_workers(worker_func, additional_workers)

            # Scale down if the queue is well below the threshold, we have more workers than min_workers,
            # and it's been long enough since the last scale down
            elif queue_size < self.scale_threshold / 2 and current_worker_count > self.min_workers:
                current_time = time.time()
                if current_time - self.last_scale_down_time > self.scale_down_delay:
                    self.logger.info(f"Scaling down: Removing workers (Current: {current_worker_count})")
                    self.stop_extra_workers(1)
                    self.last_scale_down_time = current_time  # Update the last scale-down time

            # Log system status
            self.logger.info(
                f"Queue size: {queue_size}, Active workers: {current_worker_count}, "
                f"Completed tasks: {self.completed_tasks}, Errors: {self.error_count}"
            )
            self.completed_tasks = 0

            # Monitor system resources
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            self.logger.info(f"System CPU Usage: {cpu_usage}%, Memory Usage: {memory_usage}%")

    def stop_extra_workers(self, count):
        for _ in range(count):
            self.task_queue.put(None)  # Insert None as a poison pill to terminate one worker

    def run(self, producer_func, worker_func):
        # Clear the stop event in case it's set from a previous run
        self.stop_event.clear()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Start initial workers
        self.start_workers(worker_func, self.initial_worker_count)

        # Start the producer
        self.start_producer(lambda task_queue, stop_event: producer_func(task_queue, stop_event))

        # Start monitoring
        self.monitor_thread = threading.Thread(target=self.monitor_system, args=(worker_func,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        # Wait for the producer thread to finish
        if self.producer_thread:
            self.producer_thread.join()

        # Insert poison pills to stop worker threads
        for _ in range(len(self.workers)):
            self.task_queue.put(None)  # Poison pill

        # Wait for all worker threads to finish
        for worker in self.workers:
            worker.join()

        # Wait for the monitor thread to finish
        if self.monitor_thread:
            self.monitor_thread.join()

        self.logger.info("All processes have been terminated gracefully.")

# Example async producer function
async def example_producer(task_queue, stop_event):
    count = 0
    while not stop_event.is_set():
        task_queue.put(f"Task-{count}")
        count += 1
        await asyncio.sleep(0.1)

# Example async worker function
async def example_worker(task):
    # print(f"Processing task: {task}")
    await asyncio.sleep(1)

# Example usage
if __name__ == "__main__":
    processor = EventDrivenQueueProcessor(worker_count=10, min_workers=1, max_workers=20, scale_threshold=10, scale_down_delay=30)
    processor.run(example_producer, example_worker)
