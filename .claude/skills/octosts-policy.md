---
name: octosts-policy
description: Generate a stub OctoSTS trust policy file in `.github/chainguard/` when a Linear issue reports a missing policy.
---

# OctoSTS Trust Policy Stub

When the linear-materializer picks up an issue titled `OctoSTS: trust policy missing for \`<identity>\``, generate a stub trust policy file at `.github/chainguard/<identity>.sts.yaml`.

## Inputs (from the issue body)

The issue body contains:
- `issuer` — the OIDC issuer URL from `actor.iss` in BQ (e.g. `https://accounts.google.com`, `https://token.actions.githubusercontent.com`)
- `subject` — the subject claim from `actor.sub` (e.g. a numeric GCP service-account ID, or a GitHub Actions subject)
- `identity` — the OctoSTS identity name (from the issue title; equals the filename stem)

## Stub format

```yaml
# Copyright YYYY Chainguard, Inc.
# SPDX-License-Identifier: Apache-2.0
#
# AUTO-GENERATED STUB. Do not merge as-is — fill in repositories and permissions.

issuer: <from issue>
subject: "<from issue>"

permissions:
  # TODO: scope permissions to the minimum required for this caller.
  # Common choices:
  #   pull_requests: read         # read PR review state
  #   pull_requests: write        # open/update PRs
  #   contents: read              # read repo contents
  #   contents: write             # push branches / commits
  #   issues: read | write
  #   checks: read | write        # post check runs (pins consumer to a single STS install — use carefully)
  #   workflows: write            # trigger / manage GitHub Actions
  pull_requests: read

repositories: []  # TODO: specify the repos this identity needs access to, or leave [] for org-wide read-only.
```

## Reference policies in this repo

- Image-gen pattern (write to `stereo`): `.github/chainguard/dev-mrisharma-image-gen.sts.yaml`, `.github/chainguard/dev-zkranurag-image-gen.sts.yaml`
- Read-only org-wide: `.github/chainguard/slack-reactor.sts.yaml`
- Bot scoped to specific repos: `.github/chainguard/eco-fixer-reconciler.sts.yaml`

Use the closest existing example as a starting point. **Always** include the `Do not merge as-is` comment line — the human reviewer must approve the repositories and permissions before merge.

## Commit message format

`feat(octosts): add stub trust policy for <identity>` with a one-line body pointing at the originating Linear issue.

## PR title

`feat(octosts): add stub trust policy for <identity>`

## Test plan section in PR description

> Manually verify the `subject` claim matches the service that needs access. After merge, the next `dev_octo-sts_exchange` from this identity should succeed; if it still fails with `no trust policy`, the subject is wrong.
