#!/usr/bin/env python3
"""Migrate hotel GitOps values from slot images to a single frontend.image + rollout.

Release candidate: frontend.slots.green (Phase 06 CI writes green). If green is missing,
use the image of blueGreen.activeSlot. If blue and green tags/digests differ, still select
green and print a warning. Fail if no candidate image exists.

Does not use regex. Does not talk to the cluster.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

ROOT_DEFAULT = Path("GITOPS_ROOT (set by the test fixture)")
PATHS = [
    Path("clusters/nonprod/dev/hotel.yaml"),
    Path("clusters/nonprod/staging/hotel.yaml"),
    Path("clusters/nonprod/uat/hotel.yaml"),
    Path("clusters/prod/production/hotel.yaml"),
]
AUTOPROMOTE = {
    "dev": True,
    "staging": True,
    "uat": False,
    "production": False,
}
SCALE_DOWN = {
    "dev": 30,
    "staging": 30,
    "uat": 30,
    "production": 300,
}


def load(path: Path) -> dict:
    with path.open() as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a mapping")
    return data


def dump(path: Path, data: dict) -> None:
    with path.open("w") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False, sort_keys=False, width=120)


def env_name(data: dict) -> str:
    global_ = data.get("global") or {}
    env = global_.get("environment")
    if env not in AUTOPROMOTE:
        raise ValueError(f"unknown global.environment: {env}")
    return env


def image_identity(image: dict | None) -> tuple[str, str, str]:
    image = image or {}
    return (
        str(image.get("repository") or ""),
        str(image.get("tag") or ""),
        str(image.get("digest") or ""),
    )


def select_candidate(data: dict) -> dict:
    frontend = data.get("frontend") or {}
    existing = (frontend.get("image") or {}) if isinstance(frontend.get("image"), dict) else {}
    if existing.get("repository"):
        return existing

    slots = frontend.get("slots") or {}
    if not isinstance(slots, dict):
        raise ValueError("frontend.slots missing; cannot select release candidate")
    green = (slots.get("green") or {}).get("image") or {}
    active_slot = ((data.get("blueGreen") or {}).get("activeSlot")) or "blue"
    active = (slots.get(active_slot) or {}).get("image") or {}

    green_id = image_identity(green)
    active_id = image_identity(active)
    if green_id[0]:
        if active_id[0] and green_id != active_id:
            print(
                "warning: green and active slot images differ; "
                "using green (Phase 06 release candidate)",
                file=sys.stderr,
            )
        return dict(green)
    if active_id[0]:
        print(
            f"warning: green slot empty; using activeSlot={active_slot}",
            file=sys.stderr,
        )
        return dict(active)
    raise ValueError("no frontend image candidate (green and activeSlot empty)")


def migrate_file(path: Path) -> None:
    data = load(path)
    env = env_name(data)
    candidate = select_candidate(data)
    frontend = data.setdefault("frontend", {})
    frontend["image"] = {
        "repository": candidate.get("repository", ""),
        "tag": candidate.get("tag", ""),
        "digest": candidate.get("digest", ""),
        "pullPolicy": candidate.get("pullPolicy", "IfNotPresent"),
    }
    data["rollout"] = {
        "enabled": True,
        "autoPromotionEnabled": AUTOPROMOTE[env],
        "scaleDownDelaySeconds": SCALE_DOWN[env],
        "analysis": {"enabled": False},
    }
    dump(path, data)
    print(f"migrated {path} env={env} autoPromotion={AUTOPROMOTE[env]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gitops-root", type=Path, default=ROOT_DEFAULT)
    args = parser.parse_args()
    root = args.gitops_root
    for rel in PATHS:
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        migrate_file(path)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
