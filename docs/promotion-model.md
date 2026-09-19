# Promotion model

| Step | How |
|------|-----|
| build → dev | `ci.yml` on `main` writes digest + opens PR |
| dev → staging | `promote.yml` workflow_dispatch |
| staging → uat | same (warns UAT DNS/SM may be missing) |
| uat → production | same + ECR manifest copy + **required** Environment |
| staging → production | only `emergency=true` |
| dev → production | **forbidden** |

Source of truth: read digest from `gitops-platform` source file (`read-release --require-digest`). No manual digest typing.

Hotel traffic: `traffic-promote.yml` copies green image identity (including digest) onto blue. Does not rebuild.
