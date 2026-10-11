import time


def run() -> None:
    # V1 worker boundary. Email jobs will be leased and processed here after the
    # transactional outbox tables are added in the inventory milestone.
    while True:
        time.sleep(30)


if __name__ == "__main__":
    run()

