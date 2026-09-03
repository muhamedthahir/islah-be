"""
Convert cookie rows pasted from Chrome DevTools (Application > Storage > Cookies,
select rows, Ctrl+C) into the Netscape cookies.txt format yt-dlp expects.

Usage:
    python scripts/cookies_to_netscape.py raw_cookies.txt cookies.txt
"""

import csv
import sys
from datetime import datetime, timezone


def to_epoch(value: str) -> int:
    value = value.strip()
    if not value or value.lower() in {"session", "-"}:
        return 0
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def convert(input_path: str, output_path: str) -> None:
    seen: set[tuple[str, str, str]] = set()
    lines = ["# Netscape HTTP Cookie File\n"]

    with open(input_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row or not row[0].strip():
                continue

            name = row[0].strip()
            if name.lower() == "name":
                continue

            value = row[1] if len(row) > 1 else ""
            domain = row[2] if len(row) > 2 else ""
            path = row[3] if len(row) > 3 else "/"
            expires_raw = row[4] if len(row) > 4 else ""
            secure_flag = row[7].strip() if len(row) > 7 else ""

            key = (name, domain, path)
            if key in seen:
                continue
            seen.add(key)

            include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
            secure = "TRUE" if secure_flag else "FALSE"
            expiry = to_epoch(expires_raw)

            lines.append(
                "\t".join([domain, include_subdomains, path or "/", secure, str(expiry), name, value]) + "\n"
            )

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Wrote {len(lines) - 1} cookies to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/cookies_to_netscape.py raw_cookies.txt cookies.txt")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
