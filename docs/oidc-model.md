# OIDC model

IAM roles should trust GitHub OIDC subjects scoped to repository **and** environment.

Name form:

```text
repo:<github-owner>/<repository>:environment:dev
```

Unique-ID form (inspect a real token):

```text
repo:<github-owner>@<orgId>/<repository>@<repoId>:environment:dev
```

Do not use `repo:<github-owner>/*`.
