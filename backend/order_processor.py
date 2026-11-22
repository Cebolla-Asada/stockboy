import threading
import time


def start_order_processor(process_callback):

    def run():
        while True:
            try:
                process_callback()
            except Exception as error:
                print("Order processor error:", error)

            time.sleep(2)

    worker = threading.Thread(
        target=run,
        daemon=True
    )

    worker.start()