import argparse
import math
import re
import sys
from pathlib import Path


FIELD_PATTERN = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)=([^\s]+)")


def _parse_fields(line: str) -> dict[str, str]:
    return dict(FIELD_PATTERN.findall(line))


def _new_measurement_group() -> dict:
    return {
        "durations": [],
        "count": 0,
        "errors": 0,
    }


def _parse_nonnegative_number(value: str | None) -> float | None:
    if value is None:
        return None

    try:
        number = float(value)
    except ValueError:
        return None

    if not math.isfinite(number) or number < 0:
        return None
    return number


def analyze_lines(lines) -> dict:
    requests = {}
    stages = {}
    retries = {}
    ignored_events = 0

    for line in lines:
        fields = _parse_fields(line)
        event = fields.get("event")

        if event == "http_request":
            duration = _parse_nonnegative_number(fields.get("duration_ms"))
            method = fields.get("method")
            route = fields.get("route")
            status_code = fields.get("status_code")
            if duration is None or not method or not route or not status_code:
                ignored_events += 1
                continue

            group = requests.setdefault(
                f"{method} {route}",
                _new_measurement_group(),
            )
            group["durations"].append(duration)
            group["count"] += 1
            if not status_code.isdigit() or int(status_code) >= 400:
                group["errors"] += 1

        elif event == "stage_timing":
            duration = _parse_nonnegative_number(fields.get("duration_ms"))
            stage = fields.get("stage")
            outcome = fields.get("outcome")
            if duration is None or not stage or not outcome:
                ignored_events += 1
                continue

            group = stages.setdefault(stage, _new_measurement_group())
            group["durations"].append(duration)
            group["count"] += 1
            if outcome != "success":
                group["errors"] += 1

        elif event == "provider_retry":
            operation = fields.get("operation")
            delay = _parse_nonnegative_number(fields.get("delay_seconds"))
            attempt = fields.get("attempt")
            if not operation or delay is None or not attempt or not attempt.isdigit():
                ignored_events += 1
                continue

            group = retries.setdefault(
                operation,
                {"count": 0, "total_delay_seconds": 0.0},
            )
            group["count"] += 1
            group["total_delay_seconds"] += delay

    return {
        "requests": requests,
        "stages": stages,
        "retries": retries,
        "ignored_events": ignored_events,
    }


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index
    return ordered[lower_index] + (
        ordered[upper_index] - ordered[lower_index]
    ) * fraction


def _format_measurement_table(title: str, groups: dict) -> list[str]:
    lines = [title, "-" * len(title)]
    if not groups:
        return lines + ["(no events)"]

    lines.append(
        f"{'Name':<42} {'N':>6} {'Errors':>8} {'p50 ms':>12} {'p95 ms':>12}"
    )
    for name, group in sorted(groups.items()):
        lines.append(
            f"{name[:42]:<42} {group['count']:>6} {group['errors']:>8} "
            f"{_percentile(group['durations'], 0.50):>12.2f} "
            f"{_percentile(group['durations'], 0.95):>12.2f}"
        )
    return lines


def format_report(summary: dict) -> str:
    lines = []
    lines.extend(_format_measurement_table("HTTP requests", summary["requests"]))
    lines.append("")
    lines.extend(_format_measurement_table("Workflow stages", summary["stages"]))
    lines.append("")
    lines.append("Provider retries")
    lines.append("----------------")
    if summary["retries"]:
        lines.append(f"{'Operation':<42} {'Retries':>8} {'Delay total s':>16}")
        for operation, group in sorted(summary["retries"].items()):
            lines.append(
                f"{operation[:42]:<42} {group['count']:>8} "
                f"{group['total_delay_seconds']:>16.2f}"
            )
    else:
        lines.append("(no retries)")

    lines.append(f"\nMalformed performance events ignored: {summary['ignored_events']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize CODEX backend performance logs. "
            "Use '-' to read from standard input."
        )
    )
    parser.add_argument("log_file", help="Path to the log file, or '-' for stdin")
    args = parser.parse_args(argv)

    if args.log_file == "-":
        summary = analyze_lines(sys.stdin)
    else:
        try:
            with Path(args.log_file).open(
                "r",
                encoding="utf-8",
                errors="replace",
            ) as log_file:
                summary = analyze_lines(log_file)
        except OSError as error:
            print(f"Unable to read log file: {error}", file=sys.stderr)
            return 2

    print(format_report(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
