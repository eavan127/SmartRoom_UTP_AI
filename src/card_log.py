"""CSV log of card collection and return. Student codes only."""
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "logs" / "card_log.csv"
COLUMNS = ["timestamp", "booking_id", "room", "action", "method", "students", "seconds"]


def append(booking, action, method, students, seconds):
    LOG.parent.mkdir(exist_ok=True)
    row = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "booking_id": booking["booking_id"],
        "room": booking["room"],
        "action": action,            # collect | return
        "method": method,            # face | staff override
        "students": ";".join(students),
        "seconds": round(seconds, 1),
    }])
    row.to_csv(LOG, mode="a", header=not LOG.exists(), index=False)


def read():
    if not LOG.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(LOG)


def cards_out():
    """Booking ids whose last logged action is 'collect'."""
    df = read()
    if df.empty:
        return set()
    last = df.groupby("booking_id")["action"].last()
    return set(last[last == "collect"].index)
