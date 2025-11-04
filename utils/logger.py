import logging
import os
from logging.handlers import RotatingFileHandler
import json
import time

def setup_logger(run_id: str, level=logging.INFO, log_dir="reports"):
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger("uask")
    logger.setLevel(level)
    if logger.handlers:
        return logger

    file_path = os.path.join(log_dir, f"run-{run_id}.log")
    file_handler = RotatingFileHandler(file_path, maxBytes=5_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(file_handler)

    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(stream)

    def _json_log(level_name, msg, extra=None):
        entry = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "level": level_name,
            "message": msg,
        }
        if extra:
            entry.update(extra)
        logger_method = getattr(logger, level_name.lower(), logger.info)
        logger_method(json.dumps(entry, ensure_ascii=False))

    # attach helper to logger
    logger.json = _json_log
    return logger
