"""
scheduler.py — Keep running in the background and post every day at POST_TIME.
Run with: python scheduler.py
"""

import schedule
import time
import logging
from datetime import datetime
from main import run_daily_post
from config import POST_TIME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler(),
    ],
)


def job():
    logging.info("Scheduled job triggered.")
    try:
        run_daily_post()
        logging.info("Job completed successfully.")
    except Exception as e:
        logging.error(f"Job failed: {e}", exc_info=True)


def main():
    logging.info(f"Scheduler started. Will post every day at {POST_TIME}.")
    schedule.every().day.at(POST_TIME).do(job)

    # Optionally post immediately on first run (comment out if not desired)
    # job()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
