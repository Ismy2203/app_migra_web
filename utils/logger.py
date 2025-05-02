import os
import logging

log_file_path = os.path.abspath("migration_logs.txt")
LOG_TEXT = []

def setup_logger():
    global LOG_TEXT
    logging.basicConfig(filename=log_file_path, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    LOG_TEXT = []

def log_message(message):
    print(message)
    with open(log_file_path, 'a', encoding="utf-8") as log_file:
        log_file.write(message + '\n')
 