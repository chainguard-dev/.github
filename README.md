# .github
Default files to be used for any public repository under the chainguard-dev organization.

This repository contains tooling and templates to assist in the management and daily work of the Chainguard-dev GitHub organisation.

Organization-level Octo STS policies live under `.github/chainguard/`.
`release-shadow-jbcg-e2e` lets the isolated jbcg.dev release-admission
qualification broker read mono and organization membership, with no GitHub
write permissions. Its subject pins the broker's numeric Google service-account
ID; the policy grants no credentials to the CI requester.
