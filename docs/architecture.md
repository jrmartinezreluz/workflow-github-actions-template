# Architecture

```text
solution-hospitality-booking / solution-enterprise-erp
    CI on pull_request (scan + build, no ECR push)
    CI on main (scan + build + ECR push + SBOM + DEV GitOps PR)
         ↓
workflow scripts (gitops-update.py)
         ↓
gitops-platform PR (never direct main for production)
         ↓
Argo CD (not synced by this phase)
```

Reusable workflow YAML lives in `repos/workflow-github-actions` and is **copied** into each app under `.github/workflows/` so CI runs before that GitHub repository exists.

OIDC: still `AWS_ROLE_ARN` + `repo:…:*` trust. Target Environments claims are documented; **not applied**.

n8n has no application CI in this phase.
