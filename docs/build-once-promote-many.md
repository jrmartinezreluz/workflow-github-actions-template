# Build once, promote many

One image per component per `main` commit. Environments only change GitOps pointers.

```text
build id A → digest X
DEV        → X
STAGING    → X
UAT        → X
PRODUCTION → X  (ECR copy nonprod → prod, same digest)
```

Hotel release set: backend digest + frontend green digest from the **same** CI run. Do not mix builds.

Traffic (green→blue) is not an environment promotion.
