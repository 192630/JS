#!/usr/bin/env python3
"""Build five-session institutional net flows from dated daily snapshots."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def parse_share_count(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not re.fullmatch(r"[+-]?\d+", text):
        return None
    return int(text)


def build(data_dir):
    history_dir = data_dir / "institutional_history"
    paths = sorted(path for path in history_dir.glob("*.json")
                   if re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.stem))[-5:]
    if len(paths) != 5:
        raise ValueError("Five dated institutional snapshots are required")

    daily_rows = []
    dates = []
    for path in paths:
        with path.open(encoding="utf-8") as source:
            payload = json.load(source)
        if payload.get("trade_date") != path.stem:
            raise ValueError(f"Trade date mismatch in {path.name}")
        rows = payload.get("institutional")
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"No institutional rows in {path.name}")
        daily_rows.append({
            str(row[0]).strip(): row for row in rows
            if isinstance(row, list) and len(row) > 11 and str(row[0]).strip()
        })
        dates.append(path.stem)

    by_code = {}
    for code in daily_rows[-1]:
        rows = [day.get(code) for day in daily_rows]
        if any(row is None for row in rows):
            continue
        values = [[parse_share_count(row[index]) for row in rows]
                  for index in (4, 10, 11)]
        if any(value is None for series in values for value in series):
            continue
        streaks = []
        for series in values:
            latest = series[-1]
            if latest == 0:
                streaks.append(0)
                continue
            sign = 1 if latest > 0 else -1
            count = 0
            for value in reversed(series):
                if value * sign <= 0:
                    break
                count += 1
            streaks.append(sign * count)
        by_code[code] = [sum(series) for series in values] + streaks

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "dates": dates,
        "sessions": 5,
        "fields": ["foreign_net_shares", "trust_net_shares", "dealer_net_shares",
                   "foreign_streak", "trust_streak", "dealer_streak"],
        "count": len(by_code),
        "by_code": by_code,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    result = build(args.data_dir)
    target = args.data_dir / "institutional_flow.json"
    with target.open("w", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, separators=(",", ":"))
    print(f"Built five-session institutional flows for {result['count']} securities")


if __name__ == "__main__":
    main()
