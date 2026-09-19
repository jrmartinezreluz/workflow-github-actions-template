# Security scanning

| Control | Tool | When | Policy |
|---------|------|------|--------|
| Secrets | Gitleaks v8.21.2 (`--redact`, exit 1) | PR + main | fail on findings; values redacted |
| Image vulns | Trivy action 0.28.0 | every build | CRITICAL fail; HIGH report (`exit-code: 0`) |
| SBOM | Trivy SPDX JSON artifact | main push only | uploaded, no commercial SaaS |
| SAST | — | — | not configured (CodeQL deferred) |
| Lint | `node --check` (hotel backend) | PR + main | erpnext: no unit tests in repo |

First live Trivy run may fail on CRITICAL in base images (nginx/frappe). **Do not set Trivy exit-code 0 for CRITICAL.** Document findings and add `.trivyignore` only with operator review.

## Third-party Actions

| Action | Pin |
|--------|-----|
| actions/checkout | v4 (GitHub) |
| actions/upload-artifact | v4 (GitHub) |
| docker/setup-buildx-action | v3 (Docker) |
| docker/build-push-action | v6 (Docker) |
| aws-actions/configure-aws-credentials | v4 (AWS) |
| aws-actions/amazon-ecr-login | v2 (AWS) |
| aquasecurity/trivy-action | 0.28.0 |
| actions/create-github-app-token | v2 (GitHub) |
| gitleaks image | ghcr.io/gitleaks/gitleaks:v8.21.2 |

`actionlint` is not installed; workflow YAML was reviewed statically, not actionlint-validated.
