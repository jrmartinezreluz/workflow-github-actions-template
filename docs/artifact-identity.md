# Artifact identity

Authoritative: `digest: sha256:<64 hex>`

Human: `tag: sha-<gitsha>`

Forbidden tags: `latest`, `dev`, `staging`, `prod`, `production`.

Helm (`arkhadia-common.image`): if digest set → `repository@digest`, else `repository:tag`.

Hotel Deployments render `@sha256` when digest is set.

ERPNext **upstream** Frappe chart still templates `repository:tag` and ignores `digest`. GitOps still stores digest for promotion/copy. Unique `sha-<git>` tags are treated as immutable until the wrapper/upstream supports digest pull.
