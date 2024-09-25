# .github
Default files to be used for any public repository under the chainguard-dev organization.

This repository contains tooling and templates to assist in the management and daily work of the Chainguard-dev GitHub organisation.

### Label syncer

If you want to sync a label to all or to a specific repository please update the file `label-syncer.yaml` and add the label
that you want to sync accross repositories or to a specific one.

It will not remove labels, but if a label that are set in this file is deleted the job will re-add that in the next time it runs.

Yaml file format:

```yaml
org: "chainguard-dev"
general:
  - name: "bugzzz"
    color: 7F3150
    description: "Something isn't working"
  - name: "featurezz"
    color: 7F3150
    description: "New feature request"
ignoreRepos:
  - repoName: "test-repo"
repos:
  - repoName: "testing-ci-providers"
    labels:
      name: "testing-label"
      color: 7F3150
      description: "Enhancements to the repo"
```

- The `general` section is to add all the labels you want to sync to all repositories in the GitHub Org.
- The `ignoreRepos` section is a list of repositories that you don't want to sync any label.
- The `repos` section is a list of reposotories that you want to add extra labels that are not in the `general` section.
