#!/usr/bin/env python3
"""Report whether the WhatsApp bridge is actually working.

launchd answers "is the process running". The failure that matters here is
"running but not syncing" - or not running at all while reads keep succeeding
against a frozen archive, which is indistinguishable from a quiet day unless
something checks.

Exits 0 when healthy, 1 when not. On failure it posts a macOS notification, so
a silent stall becomes visible without watching a terminal.

    ./healthcheck.py           # check, notify on failure
    ./healthcheck.py --quiet   # check, no notification (for cron/manual use)
"""

import subprocess
import sys

import whatsapp


def notify(title: str, message: str) -> None:
    """Post a macOS notification. Never let this failing mask the health result."""
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification {message!r} with title {title!r}'],
            capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    quiet = "--quiet" in sys.argv
    h = whatsapp.bridge_health()

    age = h["newest_message_age_minutes"]
    age_str = f"{age:.0f}m" if age is not None else "unknown"

    if h["healthy"]:
        print(f"ok: bridge reachable, newest message {age_str} old")
        return 0

    reason = h["warning"] or "unhealthy"
    print(f"FAIL: {reason} (newest message {age_str} old)", file=sys.stderr)
    if not quiet:
        notify("WhatsApp bridge", reason)
    return 1


if __name__ == "__main__":
    sys.exit(main())
