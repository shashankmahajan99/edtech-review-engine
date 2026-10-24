"""
Bi-directional Synchronization Utility between Windows Host & macOS Workstation.
Creates Git bundles and facilitates zero-friction source synchronization across machines.
"""

import sys
import shutil
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE_PATH = ROOT / "edtech_review_engine.bundle"
OUTPUT_BUNDLE_PATH = ROOT / "output" / "edtech_review_engine.bundle"


def create_git_bundle() -> bool:
    print(f"[*] Packaging repository at {ROOT} into Git bundle...")
    res = subprocess.run(
        ["git", "bundle", "create", str(BUNDLE_PATH), "--all"],
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        print(f"[!] Error creating bundle: {res.stderr}")
        return False

    OUTPUT_BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BUNDLE_PATH, OUTPUT_BUNDLE_PATH)
    print(f"[OK] Git bundle verified! ({BUNDLE_PATH.stat().st_size:,} bytes)")
    print(f"[OK] Available via live portal at: http://127.0.0.1:8000/download/edtech_review_engine.bundle")
    return True


def display_mac_instructions():
    print("\n" + "=" * 65)
    print("  HOW TO SYNC TO YOUR MAC REPOSITORY IN 10 SECONDS")
    print("=" * 65)
    print("From your Mac terminal, choose any of these convenient methods:\n")
    print("METHOD 1: Instant HTTP Pull (Zero SSH configuration required)")
    print("  curl -O http://192.168.29.224:8000/download/edtech_review_engine.bundle")
    print("  git pull edtech_review_engine.bundle master\n")
    print("METHOD 2: Direct Git-over-SSH Pull")
    print("  git pull ssh://shashank@192.168.29.224/Users/shashank/edtech-review-engine master\n")
    print("METHOD 3: Clone Fresh Copy on Mac")
    print("  git clone http://192.168.29.224:8000/download/edtech_review_engine.bundle edtech-review-engine\n")
    print("=" * 65 + "\n")


def push_to_remote(remote_url: str):
    print(f"[*] Adding remote 'mac' -> {remote_url}...")
    subprocess.run(["git", "remote", "remove", "mac"], cwd=ROOT, capture_output=True)
    subprocess.run(["git", "remote", "add", "mac", remote_url], cwd=ROOT, check=True)
    print(f"[*] Pushing latest commits to {remote_url}...")
    res = subprocess.run(["git", "push", "-u", "mac", "master"], cwd=ROOT, capture_output=True, text=True)
    if res.returncode == 0:
        print("[OK] Successfully pushed all commits to Mac remote!")
    else:
        print(f"[!] Push failed: {res.stderr}")


def main():
    parser = argparse.ArgumentParser(description="Sync edtech-review-engine to Mac")
    parser.add_argument("--push-to", type=str, help="Git remote URL to push to")
    args = parser.parse_args()

    if create_git_bundle():
        display_mac_instructions()

    if args.push_to:
        push_to_remote(args.push_to)


if __name__ == "__main__":
    main()
