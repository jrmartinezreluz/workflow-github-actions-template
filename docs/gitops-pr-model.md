# GitOps PR model

No direct push to `gitops-platform` `main` from the new pipelines.

```text
CI/promote → branch promote/<app>/<env>/<short-sha> → Pull Request → merge policy
```

DEV may enable auto-merge. Production **never** auto-merges.

## GitHub App (target)

Permissions (repository):

- Contents: Read and Write
- Pull requests: Read and Write
- Metadata: Read

Install on: `gitops-platform` (required), plus `solution-hospitality-booking`, `solution-enterprise-erp`, `workflow-github-actions` if desired. Not org-wide.

Secrets on app repos:

```text
GITOPS_APP_ID
GITOPS_APP_PRIVATE_KEY
```

## PAT fallback (temporary)

`GITOPS_PAT` still works if App secrets are absent. Workflows emit a warning. **Removing PAT is blocked** until the App exists.
