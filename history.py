"""
Solve history management with JSON persistence
"""

import json
import os
from datetime import datetime
from pathlib import Path

# History file location
HISTORY_FILE = Path.home() / ".cube_history.json"
MAX_HISTORY = 100  # Keep last N solves


def load_history() -> list:
    """Load solve history from JSON file"""
    if not HISTORY_FILE.exists():
        return []
    
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_history(history: list):
    """Save solve history to JSON file"""
    # Keep only last MAX_HISTORY entries
    history = history[-MAX_HISTORY:]
    
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except IOError:
        pass


def add_solve(time_seconds: float, moves: list, is_pb: bool) -> dict:
    """Add a new solve to history"""
    history = load_history()
    
    now = datetime.now()
    
    solve = {
        "time": round(time_seconds, 2),
        "moves": moves,
        "move_count": len(moves),
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.strftime("%H:%M:%S"),
        "is_pb": is_pb
    }
    
    history.append(solve)
    save_history(history)
    
    return solve


def get_best_time() -> float:
    """Get the best time from history (persistent PB)"""
    history = load_history()
    
    if not history:
        return None
    
    return min(s["time"] for s in history)


def get_recent_times(n: int = 20) -> list:
    """Get the N most recent solve times for sparkline"""
    history = load_history()
    
    if not history:
        return []
    
    return [s["time"] for s in history[-n:]]


def get_statistics() -> dict:
    """Get solve statistics"""
    history = load_history()
    
    if not history:
        return {"count": 0}
    
    times = [s["time"] for s in history]
    
    stats = {
        "count": len(history),
        "best": min(times),
        "worst": max(times),
        "average": sum(times) / len(times),
    }
    
    # Ao5 (average of last 5, removing best and worst)
    if len(times) >= 5:
        last5 = sorted(times[-5:])
        stats["ao5"] = sum(last5[1:4]) / 3
    
    # Ao12
    if len(times) >= 12:
        last12 = sorted(times[-12:])
        stats["ao12"] = sum(last12[1:11]) / 10
    
    return stats


def generate_sparkline(times: list, width: int = 20) -> str:
    """Generate ASCII sparkline from times (lower is better, so inverted)"""
    if not times:
        return ""
    
    # Sparkline characters (8 levels)
    chars = "▁▂▃▄▅▆▇█"
    
    if len(times) == 1:
        return chars[0]
    
    min_t = min(times)
    max_t = max(times)
    
    if max_t == min_t:
        return chars[0] * min(len(times), width)
    
    # Take last 'width' times
    times = times[-width:]
    
    sparkline = ""
    for t in times:
        # Normalize: lower time = lower bar (better)
        normalized = (t - min_t) / (max_t - min_t)
        index = int(normalized * (len(chars) - 1))
        sparkline += chars[index]
    
    return sparkline
