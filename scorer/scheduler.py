"""
scorer/scheduler.py — Täglicher Score-Run um 06:00 UTC.

Verwendung:
  python -m scorer.scheduler

Env-Variablen:
  ALERT_WEBHOOK_URL   Optional. POST-Benachrichtigung bei Fehler.
  SCHEDULE_TIME       Optional. Uhrzeit im Format "HH:MM" (default: "06:00").
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone

import httpx
import schedule

from scorer.run import _setup_logging, run

logger = logging.getLogger(__name__)

ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "06:00")
_RETRY_DELAY_SECONDS = 3600  # retry after 1 hour on failure


# ---------------------------------------------------------------------------
# Webhook notification
# ---------------------------------------------------------------------------

def _send_alert(message: str) -> None:
    if not ALERT_WEBHOOK_URL:
        return
    try:
        httpx.post(ALERT_WEBHOOK_URL, json={"text": message}, timeout=10.0)
        logger.debug("Alert sent to webhook")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to send alert: %s", exc)


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

def _run_job() -> None:
    logger.info("Scheduled job triggered at %s", datetime.now(timezone.utc).isoformat())
    try:
        scores = asyncio.run(run(netuids=None, dry_run=False, force_refresh=False))
        if scores:
            logger.info("Scheduled run succeeded: %d subnets scored", len(scores))
        else:
            raise RuntimeError("compute_all_subnets returned empty list")
    except Exception as exc:  # noqa: BLE001
        logger.error("Scheduled run FAILED: %s", exc, exc_info=True)
        _send_alert(f"subnet-intelligence score run failed: {exc}")
        # Schedule a one-off retry after 1 hour
        logger.info("Scheduling retry in %ds", _RETRY_DELAY_SECONDS)
        schedule.every(_RETRY_DELAY_SECONDS).seconds.do(_run_once_and_cancel).tag("retry")


def _run_once_and_cancel() -> str:
    """Retry job that cancels itself after one execution."""
    _run_job()
    # Remove all retry tags so it doesn't repeat
    schedule.clear("retry")
    return schedule.CancelJob


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    _setup_logging(verbose=False)
    logger.info("Scheduler starting — daily run at %s UTC", SCHEDULE_TIME)

    schedule.every().day.at(SCHEDULE_TIME).do(_run_job)

    logger.info("Next run: %s", schedule.next_run())

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
