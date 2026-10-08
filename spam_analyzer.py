"""
spam_analyzer.py - Roblox Chat Limit & Rate Limit Analyzer
Analyzes queued chat messages and interval timings against Roblox's TextChatService limits.
"""

from typing import List, Dict, Any, Tuple

ROBLOX_MAX_CHAR_LIMIT = 200
ROBLOX_BURST_WINDOW_SECONDS = 5.0
ROBLOX_MAX_MESSAGES_PER_WINDOW = 5
MINIMUM_SAFE_INTERVAL_SECONDS = 1.0
DANGEROUS_INTERVAL_SECONDS = 0.5


def analyze_chat_macro(messages: List[str], intervals_seconds: List[float], loop: bool = False) -> Dict[str, Any]:
    """
    Analyzes message list and intervals for Roblox chat limit compliance.
    
    Returns a dictionary:
    {
        "status": "SAFE" | "CAUTION" | "DANGER",
        "color": "#2ecc71" | "#f39c12" | "#e74c3c",
        "title": str,
        "warnings": List[str],
        "char_warnings": List[Dict[str, Any]],
        "avg_interval": float,
        "burst_rate_mps": float,
        "total_duration": float,
        "is_safe": bool
    }
    """
    warnings = []
    char_warnings = []
    status = "SAFE"
    color = "#2ecc71"  # Emerald green

    if not messages:
        return {
            "status": "SAFE",
            "color": "#2ecc71",
            "title": "No messages queued",
            "warnings": ["Add at least one message to begin."],
            "char_warnings": [],
            "avg_interval": 1.0,
            "burst_rate_mps": 0.0,
            "total_duration": 0.0,
            "is_safe": True
        }

    # 1. Check Character Limits (Roblox Max 200 chars)
    for idx, msg in enumerate(messages):
        char_count = len(msg)
        if char_count > ROBLOX_MAX_CHAR_LIMIT:
            char_warnings.append({
                "index": idx + 1,
                "length": char_count,
                "exceeded_by": char_count - ROBLOX_MAX_CHAR_LIMIT
            })
            warnings.append(
                f"Message #{idx + 1} has {char_count} chars (exceeds Roblox's {ROBLOX_MAX_CHAR_LIMIT}-character limit by {char_count - ROBLOX_MAX_CHAR_LIMIT}). It will be truncated or blocked!"
            )
            status = "DANGER"
            color = "#e74c3c"
        elif char_count == 0:
            warnings.append(f"Message #{idx + 1} is empty.")

    # 2. Check Repeated Consecutive Messages (Roblox Spam Filter)
    if len(messages) > 1:
        consecutive_dupes = 0
        for i in range(len(messages) - 1):
            if messages[i].strip() and messages[i].strip() == messages[i + 1].strip():
                consecutive_dupes += 1
        if consecutive_dupes > 0:
            warnings.append(
                f"Found {consecutive_dupes} consecutive duplicate message(s). Roblox spam filter may silently hide or drop repeat texts."
            )

    # 3. Check Timing & Interval Limits
    # Ensure intervals matches messages count
    safe_intervals = []
    for i in range(len(messages)):
        if i < len(intervals_seconds):
            val = max(0.01, float(intervals_seconds[i]))
        else:
            val = 1.0
        safe_intervals.append(val)

    total_duration = sum(safe_intervals)
    avg_interval = total_duration / len(safe_intervals) if safe_intervals else 1.0
    burst_rate_mps = 1.0 / avg_interval if avg_interval > 0 else 1.0

    # Calculate rolling 5-second window max messages
    # Simulate message send timestamps
    timestamps = [0.0]
    curr_time = 0.0
    for interval in safe_intervals[:-1]:
        curr_time += interval
        timestamps.append(curr_time)

    # If looping, simulate up to 15 seconds or 3 loops to detect runaway flood
    if loop and len(safe_intervals) > 0:
        loop_time = curr_time + safe_intervals[-1]
        for loop_idx in range(1, 3):
            for interval in safe_intervals:
                loop_time += interval
                timestamps.append(loop_time)

    max_in_5s = 0
    for t in timestamps:
        count_in_5s = sum(1 for other in timestamps if t <= other <= t + ROBLOX_BURST_WINDOW_SECONDS)
        if count_in_5s > max_in_5s:
            max_in_5s = count_in_5s

    # Assess Flood / Spam Threat
    min_interval = min(safe_intervals) if safe_intervals else 1.0
    
    if min_interval < 0.25 or max_in_5s > 6:
        status = "DANGER"
        color = "#e74c3c"  # Coral red
        warnings.append(
            f"FLOOD WARNING: Sends ~{max_in_5s} msgs in 5s (min interval {int(min_interval*1000)}ms). "
            f"Roblox rate limit is ~5 messages per 5s. Will trigger 'You are sending messages too quickly' mute!"
        )
    elif min_interval < DANGEROUS_INTERVAL_SECONDS or max_in_5s >= ROBLOX_MAX_MESSAGES_PER_WINDOW:
        if status != "DANGER":
            status = "CAUTION"
            color = "#f39c12"  # Amber orange
        warnings.append(
            f"HIGH SPEED WARNING: Interval is {int(min_interval*1000)}ms ({max_in_5s} msgs in 5s). "
            f"Close to Roblox chat spam threshold. May be throttled after a few messages."
        )
    elif min_interval < MINIMUM_SAFE_INTERVAL_SECONDS:
        if status == "SAFE":
            status = "CAUTION"
            color = "#f1c40f"  # Sun yellow
        warnings.append(
            f"MODERATE SPEED: Fast typing ({int(min_interval*1000)}ms). Safe for small bursts (2-3 messages), "
            f"but slow down if repeating continuously."
        )

    title_map = {
        "SAFE": "Safe Rate Limit (Complies with Roblox limits)",
        "CAUTION": "Caution: Fast Pace (Risk of Roblox Throttle)",
        "DANGER": "RATE LIMIT WARNING: Flood ban / mute imminent!"
    }

    return {
        "status": status,
        "color": color,
        "title": title_map[status],
        "warnings": warnings,
        "char_warnings": char_warnings,
        "avg_interval": avg_interval,
        "burst_rate_mps": burst_rate_mps,
        "total_duration": total_duration,
        "is_safe": status != "DANGER"
    }
