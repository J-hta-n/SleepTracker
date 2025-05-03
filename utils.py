import re
from datetime import datetime, timedelta


def get_sleep_date(dt: datetime) -> datetime:
    if dt.hour >= 0 and dt.hour < 20:
        return dt.date()
    else:
        return (dt + timedelta(days=1)).date()


def can_record_sleep_now(dt: datetime) -> bool:
    # Set sleep window to prevent accidental entries
    return dt.hour >= 20 or dt.hour < 12


def can_record_wakeup_now(dt: datetime) -> bool:
    # Set wakeup window to prevent accidental entries
    return dt.hour >= 3 and dt.hour < 20


def parse_duration(text: str) -> timedelta:
    pattern = re.compile(r"(?:(\d+(?:\.\d+)?)h)?\s*(?:(\d+)m)?", re.IGNORECASE)
    match = pattern.fullmatch(text.strip().replace(" ", ""))
    if not match:
        raise ValueError(
            "Invalid duration format. Try formats like '1h30m', '90m', or '1.5h'."
        )

    hours, minutes = match.groups()
    hours = float(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    return timedelta(hours=hours, minutes=minutes)


def human_readable_duration(td: timedelta) -> str:
    total_minutes = int(td.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    return " ".join(parts) if parts else "0 minutes"
