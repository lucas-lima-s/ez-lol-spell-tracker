import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.riot.ddragon import cached_version, update_snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="pt_BR")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    print(f"Cached version: {cached_version() or 'none'}")
    report = update_snapshot(lang=args.lang, force=args.force)
    print(f"Data Dragon version: {report.version} (refresh: {report.refreshed})")
    print(f"Files downloaded: {report.downloaded}")
    if not report.complete:
        for failure in report.failures:
            print(f"FAILED: {failure}")
        print(
            f"Snapshot INCOMPLETE: {len(report.failures)} downloads failed, "
            "data files not updated"
        )
        sys.exit(1)
    print("Snapshot complete")


if __name__ == "__main__":
    main()
