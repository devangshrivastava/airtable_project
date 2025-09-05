import time
import datetime
from functools import wraps
from dateutil import parser as dtparser

def retry_with_backoff(max_retries=3, backoff_factor=2):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    wait_time = backoff_factor ** attempt
                    print(f"  ⚠️  Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator

def safe_get_field(record, field_name, default=None):
    """Safely get field value from Airtable record"""
    return record.get("fields", {}).get(field_name, default)

def parse_date_safe(date_str):
    """Safely parse date string"""
    if not date_str:
        return None
    try:
        return dtparser.parse(date_str).date()
    except Exception:
        return None

def calculate_experience_years(exp_records):
    """Calculate total years of experience"""
    total_days = 0
    today = datetime.date.today()
    
    for record in exp_records:
        start_str = safe_get_field(record, "Start")
        end_str = safe_get_field(record, "End")
        
        start_date = parse_date_safe(start_str)
        if not start_date:
            continue
            
        end_date = parse_date_safe(end_str) if end_str else today
        if end_date >= start_date:
            total_days += (end_date - start_date).days
    
    return total_days / 365.25
