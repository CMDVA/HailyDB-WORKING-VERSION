"""
SPC Day Utility Functions for HailyDB
Handles Storm Prediction Center's non-standard reporting day definitions
"""
from datetime import datetime, timedelta
from typing import Tuple


def get_current_spc_day_utc() -> str:
    """
    Returns current SPC day string in YYYY-MM-DD format.
    
    SPC defines its "storm day" as:
    - From 1200 UTC on day N
    - To 1159 UTC on day N+1
    
    Logic:
    - If current UTC time >= 12:00Z, SPC day is today (UTC date)
    - If current UTC time < 12:00Z, SPC day is yesterday (UTC date - 1)
    
    Returns:
        str: SPC day in YYYY-MM-DD format
    """
    now_utc = datetime.utcnow()
    
    if now_utc.hour >= 12:
        # Current time is >= 12:00Z, so SPC day is today
        spc_day = now_utc.date()
    else:
        # Current time is < 12:00Z, so SPC day is yesterday
        spc_day = (now_utc - timedelta(days=1)).date()
    
    return spc_day.strftime('%Y-%m-%d')


def get_spc_day_window_utc(spc_day: str) -> Tuple[datetime, datetime]:
    """
    Returns the UTC start and end times for a given SPC day.
    
    Args:
        spc_day: SPC day string in YYYY-MM-DD format
        
    Returns:
        Tuple of (start_time, end_time) in UTC
    """
    from datetime import datetime
    
    # Parse the SPC day
    spc_date = datetime.strptime(spc_day, '%Y-%m-%d').date()
    
    # Start time: 12:00 UTC on the SPC day
    start_time = datetime.combine(spc_date, datetime.min.time().replace(hour=12))
    
    # End time: 11:59 UTC on the next day
    end_time = datetime.combine(spc_date + timedelta(days=1), datetime.min.time().replace(hour=11, minute=59, second=59))
    
    return start_time, end_time


def get_spc_day_window_description(spc_day: str) -> str:
    """
    Returns a human-readable description of the SPC day window.
    
    Args:
        spc_day: SPC day string in YYYY-MM-DD format
        
    Returns:
        str: Window description in format "YYYY-MM-DDTHH:MMZ → YYYY-MM-DDTHH:MMZ"
    """
    start_time, end_time = get_spc_day_window_utc(spc_day)
    return f"{start_time.strftime('%Y-%m-%dT%H:%MZ')} → {end_time.strftime('%Y-%m-%dT%H:%MZ')}"