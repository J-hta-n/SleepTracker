from datetime import datetime, time, timedelta

import pytz

# TODO: Allow for timezone customization
TIMEZONE = pytz.timezone("Asia/Singapore")


def get_sleep_date(dt: datetime) -> datetime:
    if dt.hour >= 0 and dt.hour < 20:
        return dt.date()
    else:
        return (dt + timedelta(days=1)).date()


def get_readable_date(dt: datetime) -> str:
    return dt.strftime("%-d %b")


def get_readable_time(dt: datetime) -> str:
    return dt.strftime("%-I:%M%p").lower()


def get_default_bedtime(dt: datetime) -> datetime:
    return TIMEZONE.localize(
        datetime.combine(dt.date() - timedelta(days=1), time(22, 0))
    )


def get_default_sleep_time(dt: datetime) -> datetime:
    return TIMEZONE.localize(
        datetime.combine(dt.date() - timedelta(days=1), time(22, 15))
    )


def get_default_alarm_time(dt: datetime) -> datetime:
    return TIMEZONE.localize(datetime.combine(dt.date(), time(7, 0)))


def get_default_wakeup_time(dt: datetime) -> datetime:
    return TIMEZONE.localize(datetime.combine(dt.date(), time(7, 15)))


def can_record_sleep_now(dt: datetime) -> bool:
    # Set sleep window to prevent accidental entries
    return dt.hour >= 20 or dt.hour < 12


def can_record_wakeup_now(dt: datetime) -> bool:
    # Set wakeup window to prevent accidental entries
    return dt.hour >= 3 and dt.hour < 20


def get_readable_duration(td: timedelta) -> str:
    total_minutes = int(td.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    return " ".join(parts) if parts else "0 minutes"
