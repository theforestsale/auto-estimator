import logging
import queue
from logging.handlers import QueueHandler, QueueListener


def setup_logging(app):
    log_queue = queue.Queue(-1)

    queue_handler = QueueHandler(log_queue)

    handlers = []

    try:
        file_handler = logging.FileHandler(app.config.get("LOG_FILE", "app.log"), encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        handlers.append(file_handler)
    except OSError:
        pass

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    handlers.append(console_handler)

    listener = QueueListener(log_queue, *handlers)
    listener.start()

    app.logger.addHandler(queue_handler)
    app.logger.setLevel(logging.INFO)
    root = logging.getLogger()
    root.addHandler(queue_handler)
    root.setLevel(logging.WARNING)

    return listener