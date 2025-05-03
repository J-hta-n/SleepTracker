import re
from datetime import datetime, timedelta

from dateutil import parser

from date_utils import TIMEZONE


def parse_24_hour_time_format(input: str) -> datetime | None:
    try:
        validated_timestamp = datetime.strptime(input, "%H%M").time()
        return validated_timestamp
    except ValueError:
        return None


def parse_day_month_format(input: str) -> datetime | None:
    try:
        day_month = datetime.strptime(input, "%d/%m")
        return day_month
    except ValueError:
        return None


def parse_duration(input: str) -> timedelta | None:
    try:
        pattern = re.compile(r"(?:(\d+(?:\.\d+)?)h)?\s*(?:(\d+)m)?", re.IGNORECASE)
        match = pattern.fullmatch(input.strip().replace(" ", ""))
        if not match:
            raise ValueError()
        hours, minutes = match.groups()
        hours = float(hours) if hours else 0
        minutes = int(minutes) if minutes else 0
        return timedelta(hours=hours, minutes=minutes)
    except ValueError:
        return None


def parse_datetime_string(dt_str: str) -> datetime:
    return parser.isoparse(dt_str).astimezone(TIMEZONE)
