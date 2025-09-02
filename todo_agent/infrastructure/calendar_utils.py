"""
Calendar utilities for generating calendar output in system prompts.
"""

import calendar
import subprocess
from datetime import datetime, timedelta


def get_calendar_output() -> str:
    """
    Generate calendar output for previous, current, and next month.

    Returns:
        Formatted calendar string showing three months side by side
    """
    try:
        # Use cal to get current month calendar
        result = subprocess.run(["cal"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        # Fallback to Python calendar module
        return _get_python_cal_output()


def _get_python_cal_output() -> str:
    """
    Generate calendar output using Python calendar module as fallback.

    Returns:
        Calendar output formatted similar to cal command
    """
    current_date = datetime.now()

    # Calculate previous, current, and next month
    prev_month = current_date - timedelta(days=current_date.day)
    next_month = current_date.replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)

    calendars = []

    for date in [prev_month, current_date, next_month]:
        cal = calendar.month(date.year, date.month)
        calendars.append(cal.strip())

    return "\n\n".join(calendars)


def get_current_month_calendar() -> str:
    """
    Get calendar for current month only.

    Returns:
        Calendar output for current month
    """
    try:
        result = subprocess.run(["cal"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        # Fallback to Python calendar
        current_date = datetime.now()
        return calendar.month(current_date.year, current_date.month).strip()
