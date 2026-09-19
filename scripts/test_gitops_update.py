#!/usr/bin/env python3
"""Local tests for gitops-update.py (no cluster, no AWS)."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "gitops-update.py"
GITOPS = Path(__file__).resolve().parent / "fixtures" / "gitops"
DIGEST_A = "sha256:" + ("a" * 64)
DIGEST_B = "sha256:" + ("b" * 64)
DIGEST_C = "sha256:" + ("c" * 64)


def run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--gitops-root", str(cwd), *args],
        check=check,
        text=True,
        capture_output=True,
    )


def setup_tree(tmp: Path) -> None:
    for app in ("hotel", "erpnext"):
        for role, env in (
            ("nonprod", "dev"),
            ("nonprod", "staging"),
            ("nonprod", "uat"),
            ("prod", "production"),
        ):
            src = GITOPS / "clusters" / role / env / f"{app}.yaml"
            dst = tmp / "clusters" / role / env / f"{app}.yaml"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)


def test_hotel_apply_and_promote(tmp: Path) -> None:
    run(
        [
            "apply-release",
            "--application",
            "hotel",
            "--environment",
            "dev",
            "--backend-repository",
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/nonprod/hotel-backend",
            "--backend-tag",
            "sha-deadbeef",
            "--backend-digest",
            DIGEST_A,
            "--frontend-repository",
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/nonprod/hotel-frontend",
            "--frontend-tag",
            "sha-deadbeef",
            "--frontend-digest",
            DIGEST_B,
        ],
        tmp,
    )
    out = run(["read-release", "--application", "hotel", "--environment", "dev", "--require-digest"], tmp)
    assert f"backend_digest={DIGEST_A}" in out.stdout
    assert f"frontend_digest={DIGEST_B}" in out.stdout or f"frontend_green_digest={DIGEST_B}" in out.stdout
    text = (tmp / "clusters/nonprod/dev/hotel.yaml").read_text()
    assert "hotel-dev.example.internal" in text

    run(
        ["promote-env", "--application", "hotel", "--source", "dev", "--target", "staging"],
        tmp,
    )
    st = run(["read-release", "--application", "hotel", "--environment", "staging", "--require-digest"], tmp)
    assert f"backend_digest={DIGEST_A}" in st.stdout
    assert "nonprod/hotel-backend" in st.stdout

    run(
        ["promote-env", "--application", "hotel", "--source", "staging", "--target", "uat"],
        tmp,
    )
    run(
        ["promote-env", "--application", "hotel", "--source", "uat", "--target", "production"],
        tmp,
    )
    pr = run(
        ["read-release", "--application", "hotel", "--environment", "production", "--require-digest"],
        tmp,
    )
    assert f"backend_digest={DIGEST_A}" in pr.stdout
    assert "prod/hotel-backend" in pr.stdout
    assert "nonprod/hotel-backend" not in pr.stdout

    bad = run(
        ["promote-env", "--application", "hotel", "--source", "dev", "--target", "production"],
        tmp,
        check=False,
    )
    assert bad.returncode != 0

    traffic = run(
        ["promote-traffic", "--application", "hotel", "--environment", "dev"],
        tmp,
        check=False,
    )
    from yaml import safe_load

    data = safe_load((tmp / "clusters/nonprod/dev/hotel.yaml").read_text())
    if (data.get("rollout") or {}).get("enabled"):
        assert traffic.returncode != 0
        assert "kubectl argo rollouts promote" in traffic.stderr
    else:
        assert traffic.returncode == 0
        assert data["frontend"]["slots"]["blue"]["image"]["digest"] == DIGEST_B
        assert data["blueGreen"]["activeSlot"] == "blue"


def test_erpnext(tmp: Path) -> None:
    run(
        [
            "apply-release",
            "--application",
            "erpnext",
            "--environment",
            "dev",
            "--repository",
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/nonprod/erpnext",
            "--tag",
            "sha-cafebabe",
            "--digest",
            DIGEST_C,
        ],
        tmp,
    )
    run(
        ["promote-env", "--application", "erpnext", "--source", "dev", "--target", "staging"],
        tmp,
    )
    run(
        [
            "promote-env",
            "--application",
            "erpnext",
            "--source",
            "staging",
            "--target",
            "production",
            "--emergency",
        ],
        tmp,
    )
    out = run(
        ["read-release", "--application", "erpnext", "--environment", "production", "--require-digest"],
        tmp,
    )
    assert f"application_digest={DIGEST_C}" in out.stdout
    assert "prod/erpnext" in out.stdout

    latest = run(
        [
            "apply-release",
            "--application",
            "erpnext",
            "--environment",
            "dev",
            "--repository",
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/nonprod/erpnext",
            "--tag",
            "latest",
            "--digest",
            DIGEST_C,
        ],
        tmp,
        check=False,
    )
    assert latest.returncode != 0


def test_bad_digest(tmp: Path) -> None:
    bad = run(
        [
            "apply-release",
            "--application",
            "erpnext",
            "--environment",
            "dev",
            "--repository",
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/nonprod/erpnext",
            "--tag",
            "sha-ok",
            "--digest",
            "sha256:short",
        ],
        tmp,
        check=False,
    )
    assert bad.returncode != 0


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        setup_tree(tmp)
        test_hotel_apply_and_promote(tmp)
        test_erpnext(tmp)
        test_bad_digest(tmp)
    print("gitops-update.py tests OK")


if __name__ == "__main__":
    main()
