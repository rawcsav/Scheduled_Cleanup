#!/home/rawcsav21/.virtualenvs/cleanupvenv/bin/python3
import configparser
import logging
import os
import shutil
import signal
import time
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

LOGGING_LEVEL = getattr(logging, config.get('DEFAULT', 'LoggingLevel', fallback='INFO'))
LOG_FILE = config.get('DEFAULT', 'LogFile', fallback='cleanup_log.log')
THRESHOLD_MINUTES = config.getint('DEFAULT', 'ThresholdMinutes', fallback=180)

TMP_PATH = config.get('PATHS', 'TmpPath', fallback='/tmp')
AI_UTILS_PATH = config.get('PATHS', 'AIUtilsPath', fallback='/home/rawcsav21/AIUtilsFlask/app/main_user_directory')
SPOTIFY_FLASK_PATH = config.get('PATHS', 'SpotifyFlaskPath', fallback='/home/rawcsav21/SpotifyFlask/app/user_data_dir')

# Initialize logging with configuration values
logging.basicConfig(filename=LOG_FILE, level=LOGGING_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')


def remove_empty_dirs(path):
    for root, dirs, _ in os.walk(path, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
                logging.info(f"Deleted empty directory: {dir_path}")


def is_stale(path, threshold_minutes=THRESHOLD_MINUTES):
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.utcnow() - mtime > timedelta(minutes=threshold_minutes)


def cleanup_path(path, threshold_minutes=THRESHOLD_MINUTES):
    for root, dirs, files in os.walk(path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            if is_stale(file_path, threshold_minutes):
                for _ in range(3):  # Retry up to 3 times
                    try:
                        os.remove(file_path)
                        logging.info(f"Deleted stale file: {file_path}")
                        break
                    except (OSError, Exception) as e:
                        logging.error(f"Error deleting file {file_path}: {e}")
                        time.sleep(5)  # Wait for 5 seconds before retrying

        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if is_stale(dir_path, threshold_minutes):
                for _ in range(3):  # Retry up to 3 times
                    try:
                        shutil.rmtree(dir_path)
                        logging.info(f"Deleted stale directory: {dir_path}")
                        break
                    except (OSError, Exception) as e:
                        logging.error(f"Error deleting directory {dir_path}: {e}")
                        time.sleep(5)  # Wait for 5 seconds before retrying

    # Remove any empty directories post cleanup
    remove_empty_dirs(path)


def scheduled_cleanup():
    cleanup_path(TMP_PATH)
    cleanup_path(AI_UTILS_PATH)
    cleanup_path(SPOTIFY_FLASK_PATH)


def graceful_shutdown(signum, frame):
    logging.info("Received shutdown signal. Shutting down gracefully...")
    scheduler.shutdown()
    logging.info("Scheduler shut down successfully.")
    exit(0)


scheduler = BackgroundScheduler()

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    scheduler.add_job(scheduled_cleanup, 'interval', hours=1)
    scheduler.start()

    logging.info("Cleanup scheduler started. Waiting for tasks...")

    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        graceful_shutdown(None, None)
