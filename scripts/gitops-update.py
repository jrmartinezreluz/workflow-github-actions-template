#!/usr/bin/env python3
"""YAML-aware GitOps image updates (digest-first, no regex) (digest-first, no regex)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
FORBIDDEN_TAGS = frozenset({"latest", "dev", "stg", "staging", "prod", "production"})
ENVIRONMENTS = ("dev", "staging", "uat", "production")
APPS = ("hotel", "erpnext")

# build → dev is CI, not this chain. Emergency override: staging → production.
PROMOTION_CHAIN = {
    ("dev", "staging"),
    ("staging", "uat"),
    ("uat", "production"),
}
EMERGENCY_CHAIN = {("staging", "production")}

PATHS = {
    "hotel": {
        "dev": Path("clusters/nonprod/dev/hotel.yaml"),
        "staging": Path("clusters/nonprod/staging/hotel.yaml"),
        "uat": Path("clusters/nonprod/uat/hotel.yaml"),
        "production": Path("clusters/prod/production/hotel.yaml"),
    },
    "erpnext": {
        "dev": Path("clusters/nonprod/dev/erpnext.yaml"),
        "staging": Path("clusters/nonprod/staging/erpnext.yaml"),
        "uat": Path("clusters/nonprod/uat/erpnext.yaml"),
        "production": Path("clusters/prod/production/erpnext.yaml"),
    },
}

CANONICAL_PREFIX = "nonprod"
PROD_PREFIX = "prod"


def load(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"GitOps values file missing: {path}")
    with path.open() as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a mapping")
    return data


def dump(path: Path, data: Any) -> None:
    with path.open("w") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False, sort_keys=False, width=120)


def validate_digest(digest: str) -> str:
    digest = digest.strip()
    if not DIGEST_RE.match(digest):
        raise ValueError(f"invalid OCI digest (want sha256:<64 hex>): {digest!r}")
    return digest


def validate_tag(tag: str) -> str:
    tag = tag.strip()
    if not tag:
        raise ValueError("image tag is required")
    if tag.lower() in FORBIDDEN_TAGS:
        raise ValueError(f"mutable/environment tag not allowed: {tag}")
    return tag


def _ensure_map(parent: dict, key: str) -> dict:
    val = parent.get(key)
    if val is None:
        parent[key] = {}
        return parent[key]
    if not isinstance(val, dict):
        raise ValueError(f"{key} must be a mapping")
    return val


def set_image_fields(image: dict, *, repository: str, tag: str, digest: str) -> None:
    image["repository"] = repository
    image["tag"] = validate_tag(tag)
    image["digest"] = validate_digest(digest)
    image.setdefault("pullPolicy", "IfNotPresent")


def hotel_uses_rollout(data: dict) -> bool:
    rollout = data.get("rollout") or {}
    if rollout.get("enabled") is True:
        return True
    frontend = data.get("frontend") or {}
    image = frontend.get("image") or {}
    return bool(image.get("repository"))


def hotel_artifact_images(data: dict) -> dict[str, dict]:
    backend = _ensure_map(_ensure_map(data, "backend"), "image")
    if hotel_uses_rollout(data):
        frontend = _ensure_map(_ensure_map(data, "frontend"), "image")
        return {"backend": backend, "frontend": frontend}
    green = _ensure_map(
        _ensure_map(_ensure_map(_ensure_map(data, "frontend"), "slots"), "green"),
        "image",
    )
    return {"backend": backend, "frontend_green": green}


def erpnext_artifact_images(data: dict) -> dict[str, dict]:
    return {"application": _ensure_map(_ensure_map(data, "erpnext"), "image")}


def artifact_images(app: str, data: dict) -> dict[str, dict]:
    if app == "hotel":
        return hotel_artifact_images(data)
    if app == "erpnext":
        return erpnext_artifact_images(data)
    raise ValueError(f"unsupported application: {app}")


def rewrite_repo_prefix(repository: str, *, to_prod: bool) -> str:
    if to_prod:
        return repository.replace(f"/{CANONICAL_PREFIX}/", f"/{PROD_PREFIX}/")
    return repository.replace(f"/{PROD_PREFIX}/", f"/{CANONICAL_PREFIX}/")


def copy_image(src: dict, dst: dict, *, production_repos: bool) -> None:
    repo = src.get("repository")
    tag = src.get("tag")
    digest = src.get("digest")
    if not repo or not tag or not digest:
        raise ValueError(
            "source image missing repository, tag, or digest — cannot promote"
        )
    validate_digest(str(digest))
    validate_tag(str(tag))
    if production_repos:
        repo = rewrite_repo_prefix(str(repo), to_prod=True)
    set_image_fields(dst, repository=str(repo), tag=str(tag), digest=str(digest))
    if src.get("pullPolicy"):
        dst["pullPolicy"] = src["pullPolicy"]


def assert_chain(source: str, target: str, *, emergency: bool) -> None:
    pair = (source, target)
    if pair in PROMOTION_CHAIN:
        return
    if emergency and pair in EMERGENCY_CHAIN:
        return
    raise ValueError(
        f"invalid promotion {source} → {target}. "
        "Allowed: dev→staging, staging→uat, uat→production"
        + (" (emergency: staging→production)" if not emergency else "")
        + ". dev→production is never allowed."
    )


def cmd_apply_release(args: argparse.Namespace) -> None:
    root = Path(args.gitops_root)
    path = root / PATHS[args.application][args.environment]
    data = load(path)
    images = artifact_images(args.application, data)
    if args.application == "hotel":
        set_image_fields(
            images["backend"],
            repository=args.backend_repository,
            tag=args.backend_tag,
            digest=args.backend_digest,
        )
        frontend_key = "frontend" if "frontend" in images else "frontend_green"
        set_image_fields(
            images[frontend_key],
            repository=args.frontend_repository,
            tag=args.frontend_tag,
            digest=args.frontend_digest,
        )
    else:
        set_image_fields(
            images["application"],
            repository=args.repository,
            tag=args.tag,
            digest=args.digest,
        )
    dump(path, data)
    print(f"updated {path}")


def cmd_promote_env(args: argparse.Namespace) -> None:
    assert_chain(args.source, args.target, emergency=args.emergency)
    if args.source == "dev" and args.target == "production":
        raise ValueError("dev → production is not allowed")
    root = Path(args.gitops_root)
    src_path = root / PATHS[args.application][args.source]
    dst_path = root / PATHS[args.application][args.target]
    src = load(src_path)
    dst = load(dst_path)
    src_images = artifact_images(args.application, src)
    dst_images = artifact_images(args.application, dst)
    to_prod = args.target == "production"
    for key, src_img in src_images.items():
        copy_image(src_img, dst_images[key], production_repos=to_prod)
    dump(dst_path, dst)
    print(f"promoted {args.application} {args.source} → {args.target} ({dst_path})")
    if args.target == "uat":
        print("WARNING: UAT infrastructure dependencies may not exist yet")


def cmd_promote_traffic(args: argparse.Namespace) -> None:
    if args.application != "hotel":
        raise ValueError("traffic promotion is hotel-only (green → blue slot)")
    root = Path(args.gitops_root)
    path = root / PATHS["hotel"][args.environment]
    data = load(path)
    if hotel_uses_rollout(data):
        raise ValueError(
            "rollout.enabled: do not copy GitOps slots. "
            "Promote traffic with: kubectl argo rollouts promote <rollout> -n <ns>"
        )
    slots = _ensure_map(_ensure_map(data, "frontend"), "slots")
    green = _ensure_map(slots.setdefault("green", {}), "image")
    blue = _ensure_map(slots.setdefault("blue", {}), "image")
    if not green.get("digest"):
        raise ValueError("green slot has no digest to promote")
    copy_image(green, blue, production_repos=False)
    slots["blue"]["theme"] = slots.get("green", {}).get(
        "theme", slots.get("blue", {}).get("theme", "summer")
    )
    _ensure_map(data, "blueGreen")["activeSlot"] = "blue"
    dump(path, data)
    print(f"traffic-promoted green → blue in {path} (activeSlot=blue)")


def cmd_read_release(args: argparse.Namespace) -> None:
    root = Path(args.gitops_root)
    path = root / PATHS[args.application][args.environment]
    data = load(path)
    images = artifact_images(args.application, data)
    for name, img in images.items():
        digest = img.get("digest") or ""
        if args.require_digest:
            validate_digest(str(digest))
        print(f"{name}_repository={img.get('repository', '')}")
        print(f"{name}_tag={img.get('tag', '')}")
        print(f"{name}_digest={digest}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gitops-root", type=Path, default=Path("."))
    sub = p.add_subparsers(dest="command", required=True)

    ap = sub.add_parser("apply-release", help="Write a CI-built release into one env file")
    ap.add_argument("--application", required=True, choices=APPS)
    ap.add_argument("--environment", required=True, choices=ENVIRONMENTS)
    ap.add_argument("--backend-repository")
    ap.add_argument("--backend-tag")
    ap.add_argument("--backend-digest")
    ap.add_argument("--frontend-repository")
    ap.add_argument("--frontend-tag")
    ap.add_argument("--frontend-digest")
    ap.add_argument("--repository")
    ap.add_argument("--tag")
    ap.add_argument("--digest")
    ap.set_defaults(func=cmd_apply_release)

    pr = sub.add_parser("promote-env", help="Copy artifact identity source → target")
    pr.add_argument("--application", required=True, choices=APPS)
    pr.add_argument("--source", required=True, choices=ENVIRONMENTS)
    pr.add_argument("--target", required=True, choices=ENVIRONMENTS)
    pr.add_argument(
        "--emergency",
        action="store_true",
        help="Allow staging → production only (never dev → production)",
    )
    pr.set_defaults(func=cmd_promote_env)

    tr = sub.add_parser("promote-traffic", help="Hotel: copy green image onto blue")
    tr.add_argument("--application", default="hotel", choices=("hotel",))
    tr.add_argument("--environment", required=True, choices=ENVIRONMENTS)
    tr.set_defaults(func=cmd_promote_traffic)

    rd = sub.add_parser("read-release", help="Print artifact fields from an env file")
    rd.add_argument("--application", required=True, choices=APPS)
    rd.add_argument("--environment", required=True, choices=ENVIRONMENTS)
    rd.add_argument("--require-digest", action="store_true")
    rd.set_defaults(func=cmd_read_release)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "apply-release":
        if args.application == "hotel":
            missing = [
                n
                for n in (
                    "backend_repository",
                    "backend_tag",
                    "backend_digest",
                    "frontend_repository",
                    "frontend_tag",
                    "frontend_digest",
                )
                if not getattr(args, n)
            ]
            if missing:
                raise SystemExit(f"hotel apply-release missing: {missing}")
        else:
            if not (args.repository and args.tag and args.digest):
                raise SystemExit("erpnext apply-release needs --repository --tag --digest")
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
