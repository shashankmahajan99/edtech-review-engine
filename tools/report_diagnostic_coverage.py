"""Print KB diagnostic coverage against the deterministic analyser."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.review import diagnostics  # noqa: E402


def main() -> None:
    coverage = diagnostics.coverage()
    print(f"diagnostics: {coverage['diagnostics']}")
    for status, count in coverage["by_status"].items():
        print(f"  {status:10s} {count}")
    print(f"rules with a diagnostic: {coverage['rules_with_diagnostic']}")
    print("rules without one:")
    for rule in coverage["rules_without_diagnostic"]:
        print("  -", rule)

    print("\nhuman-only diagnostics:")
    for entry in diagnostics.entries():
        if entry["status"] == "human_only":
            print(f"  {entry['id']:28s} {entry['reason']}")

    print("\nnot implemented:")
    for entry in diagnostics.entries():
        if entry["status"] == "no_rule":
            print(f"  {entry['id']:28s} {entry['reason']}")


if __name__ == "__main__":
    main()
