import json
from datetime import date


with open("data/market_history.json", encoding="utf-8") as file:
    history = json.load(file)

with open("data/backfill_progress.json", encoding="utf-8") as file:
    progress = json.load(file)

errors = []
checked_rows = 0
incomplete_rows = 0
today = date.today().isoformat()

if not isinstance(history, dict):
    raise SystemExit("market_history.json must be a JSON object")

for code, rows in history.items():
    if code == "_meta":
        continue
    if not isinstance(rows, list):
        errors.append(f"{code}: history is not a list")
        continue

    seen_dates = set()
    previous_date = ""
    for row in rows:
        checked_rows += 1
        if not isinstance(row, dict):
            errors.append(f"{code}: row is not an object")
            continue

        row_date = str(row.get("date", ""))
        if not row_date or row_date > today:
            errors.append(f"{code}: invalid date {row_date!r}")
        if row_date in seen_dates:
            errors.append(f"{code}: duplicate date {row_date}")
        if previous_date and row_date < previous_date:
            errors.append(f"{code}: dates are not sorted")
        seen_dates.add(row_date)
        previous_date = row_date

        values = [
            row.get("open"),
            row.get("high"),
            row.get("low"),
            row.get("close"),
            row.get("volume"),
        ]
        if any(value is None for value in values):
            incomplete_rows += 1
            continue

        try:
            open_price, high, low, close = map(float, values[:4])
            volume = int(values[4])
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"{code} {row_date}: malformed OHLCV ({error})")
            continue

        if min(open_price, high, low, close) <= 0:
            errors.append(f"{code} {row_date}: non-positive price")
        if high < max(open_price, low, close) or low > min(open_price, high, close):
            errors.append(f"{code} {row_date}: inconsistent OHLC")
        if volume < 0:
            errors.append(f"{code} {row_date}: negative volume")

required_progress = {
    "processed_codes",
    "successful_codes",
    "empty_codes",
    "failed_requests",
    "next_index",
    "updated_at",
}
missing_progress = sorted(required_progress - progress.keys())
if missing_progress:
    errors.append("progress missing: " + ", ".join(missing_progress))

if progress.get("processed_codes") != (
    progress.get("successful_codes", 0) + progress.get("empty_codes", 0)
):
    errors.append("progress counts do not reconcile")

if errors:
    print("Historical data validation failed:")
    for error in errors[:50]:
        print("-", error)
    if len(errors) > 50:
        print(f"- ... and {len(errors) - 50} more")
    raise SystemExit(1)

print(
    "Historical data validation passed: "
    f"{checked_rows} rows checked, {incomplete_rows} incomplete source rows warned"
)
