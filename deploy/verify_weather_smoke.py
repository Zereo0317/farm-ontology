"""Refuse a weather smoke response that represents an upstream gap."""
import json
import math
import sys


def verify_weather(payload):
    if not isinstance(payload, dict) or "gap" in payload or payload.get("http_status") != 200:
        raise ValueError("weather response is a gap or upstream error")
    current = payload.get("returned")
    if not isinstance(current, dict) or not isinstance(current.get("time"), str) or not current["time"].strip():
        raise ValueError("weather response lacks observation time")
    value = current.get("temperature_2m")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("weather response lacks a finite temperature")


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as source:
        verify_weather(json.load(source))
