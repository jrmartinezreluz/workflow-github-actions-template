# workflow-github-actions-template

Sanitized reusable GitHub Actions for **build once / promote many** delivery: container CI (Trivy, optional ECR push, SBOM, Cosign), Gitleaks, and GitOps PRs that update digest fields.

This is a **curated public template**. It is **not** the live operational workflow repository.

## Workflows

| File | Purpose |
|------|---------|
| `container-ci.yml` | buildx, Trivy, optional ECR push, SPDX SBOM, Cosign |
| `security-scan.yml` | Gitleaks |
| `reusable-gitops-pr.yml` | branch + PR against a GitOps repo (never push `main`) |
| `promote-gitops.yml` | callable promote-env wrapper |

## Inputs and secrets (no hardcoded org)

```yaml
jobs:
  gitops:
    uses: example-org/workflow-github-actions-template/.github/workflows/reusable-gitops-pr.yml@v0.1.0
    with:
      application: hotel
      mode: apply-release
      gitops_owner: ${{ vars.GITOPS_OWNER }}
      gitops_repository: ${{ vars.GITOPS_REPOSITORY }}
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
      GITOPS_APP_ID: ${{ secrets.GITOPS_APP_ID }}
      GITOPS_APP_PRIVATE_KEY: ${{ secrets.GITOPS_APP_PRIVATE_KEY }}
```

`role-to-assume` comes from `secrets.AWS_ROLE_ARN`. Do not hardcode account IDs.

## Versioning

Consumers should pin `@v0.1.0` or an immutable SHA. Do not use `@main` in production callers.

Third-party actions that were SHA-pinned in the source remain pinned.

## Tests

```bash
python3 scripts/test_gitops_update.py
```

## License

Apache-2.0. See `LICENSE` and `SECURITY.md`.
