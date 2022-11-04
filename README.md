# .github
Default files to be used for any public repository under the chainguard-dev organization.

This repository contains tooling and templates to assist in the management and daily work of the Chainguard-dev GitHub organisation.

---

# Labels

The org labels are defined in `labels.json`, and the Repositories to the labels to be
applied are defined in `repos.yaml`, please open a PR for any changes.

Any changes will be applied to all repos via the [Sync Org Labels workflow](https://github.com/chainguard-dev/.github/workflows/sync-org-labels.yml).

This only add new labels and update labels it does not remove labels that were created manually in a repository.

When renaming a label, use the `alias` property to specify the old name. For example:

```json
{
  "name": "type: bug",
  "alias": "bug"
}
```
