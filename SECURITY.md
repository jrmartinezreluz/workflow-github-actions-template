# Security Policy

This repository is a **sanitized reference/template**. It is not a live operational environment.

## Reporting a vulnerability

Use GitHub Security Advisories on this repository.

Do **not** open a public issue that contains secrets, private keys, credentials, kubeconfigs, or live infrastructure identifiers.

## Supported versions

The current tagged release (`v0.1.0` and later tags on `main`) is the supported template line.

## Secret handling

- Never commit `terraform.tfvars`, real `backend.hcl`, kubeconfig, WireGuard keys, or `.env` files with secrets.
- GitHub Actions must receive AWS roles and GitOps credentials via secrets/inputs.
- Inspect the GitHub OIDC `sub` claim in a real token; GitHub may emit repository unique IDs.
