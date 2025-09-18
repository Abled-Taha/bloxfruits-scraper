import json
from typing import Any, Dict

def read_file(FILE:str) -> Dict[str, Any]:
    """
    Read the file and return its contents as a dictionary.
    If the file does not exist or is empty, return an empty dictionary.
    """
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            else:
                print(f"Warning: {FILE} does not contain a valid JSON object.")
                return {}
    except FileNotFoundError:
        print(f"Warning: {FILE} not found. Returning empty dictionary.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {FILE}: {e}")
        return {}
      
def write_file(FILE:str, data: Dict[str, Any]) -> None:
    """
    Write the given dictionary to the file.
    Creates the file if it does not exist as well as the directory.
    """
    import os
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error writing to {FILE}: {e}")
        
def check_file_validity(FILE:str, seconds:int=7200) -> bool:
    """
    Check when the file was last modified.
    Returns True if modified within the last 2 hours and not an empty object, False otherwise.
    """
    import os
    import time

    try:
        mod_time = os.path.getmtime(FILE)
        current_time = time.time()
        # Check if modified within the last 2 hours (7200 seconds) / given time
        return (current_time - mod_time) < seconds and os.path.getsize(FILE) > 2  # not empty {}
    except FileNotFoundError:
        print(f"Warning: {FILE} not found.")
        return False
      