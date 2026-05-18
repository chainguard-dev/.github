#!/usr/bin/env python3
# Copyright 2026 Chainguard, Inc.
# SPDX-License-Identifier: Apache-2.0
"""OctoSTS policy detector.

Daily cron:
  1. Query BigQuery for OctoSTS identities that returned `no trust policy`
     errors in the last 24h, along with the issuer/subject claims.
  2. List existing trust-policy files in `.github/chainguard/`.
  3. For each identity active in BQ but missing from the repo, ensure a
     Linear issue exists in the DEV team (creating one if needed) with the
     `materializer:managed` + `repo:chainguard-dev/.github` + `FY27Q2` labels.

The linear-materializer (bots/linear-materializer in chainguard-dev/mono)
picks up the issue and produces a stub PR in this repo. The skill file at
`.claude/skills/octosts-policy.md` tells the materializer the stub format.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

POLICY_DIR = pathlib.Path(".github/chainguard")
LINEAR_API = "https://api.linear.app/graphql"
LINEAR_TOKEN_URL = "https://api.linear.app/oauth/token"  # noqa: S105 -- URL, not a secret
LINEAR_SCOPES = "read,write,issues:create"
LOOKBACK_HOURS = 24

# BQ query: identities returning "no trust policy" errors in the lookback window,
# with one sample row's issuer and subject claim.
BQ_QUERY = f"""
SELECT
  identity,
  ANY_VALUE(actor.iss) AS issuer,
  ANY_VALUE(actor.sub) AS subject,
  COUNT(*) AS exchanges,
  ANY_VALUE(error) AS sample_error
FROM `octo-sts.cloudevents_octo_sts_recorder.dev_octo-sts_exchange`
WHERE time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {LOOKBACK_HOURS} HOUR)
  AND error LIKE '%no trust policy%'
GROUP BY identity
ORDER BY exchanges DESC
LIMIT 200
"""


def list_existing_policies() -> set[str]:
    """Return identity names corresponding to `.sts.yaml` files in the repo."""
    if not POLICY_DIR.is_dir():
        raise SystemExit(f"missing policy directory: {POLICY_DIR}")
    return {p.name.removesuffix(".sts.yaml") for p in POLICY_DIR.glob("*.sts.yaml")}


def run_bq_query() -> list[dict]:
    """Execute the BQ query via `bq` and return parsed rows."""
    proc = subprocess.run(
        [
            "bq",
            "query",
            "--use_legacy_sql=false",
            "--format=json",
            "--max_rows=200",
            "--nouse_cache",
            BQ_QUERY,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        sys.stderr.write(f"bq query failed: {proc.stderr}\n")
        raise SystemExit(1)
    return json.loads(proc.stdout or "[]")


def mint_linear_token() -> str:
    """Mint a Linear OAuth access token via the client_credentials flow."""
    client_id = os.environ["LINEAR_CLIENT_ID"]
    client_secret = os.environ["LINEAR_CLIENT_SECRET"]
    form = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": LINEAR_SCOPES,
        }
    ).encode()
    req = urllib.request.Request(LINEAR_TOKEN_URL, data=form, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 -- fixed URL
        body = json.loads(resp.read())
    token = body.get("access_token")
    if not token:
        raise SystemExit(f"linear token response missing access_token: {body!r}")
    return token


def linear_graphql(token: str, query: str, variables: dict | None = None) -> dict:
    """Execute a Linear GraphQL query/mutation."""
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(LINEAR_API, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 -- fixed URL
        result = json.loads(resp.read())
    if "errors" in result:
        raise SystemExit(f"linear graphql error: {result['errors']}")
    return result["data"]


def find_open_issue(token: str, identity: str) -> str | None:
    """Return URL of an existing open issue for this identity, or None."""
    query = """
    query ($title: String!, $projectId: ID!) {
      issues(
        filter: {
          project: { id: { eq: $projectId } }
          title: { containsIgnoreCase: $title }
          state: { type: { nin: ["completed", "canceled"] } }
        }
        first: 5
      ) { nodes { id identifier title url } }
    }
    """
    data = linear_graphql(
        token,
        query,
        {"title": identity, "projectId": os.environ["LINEAR_PROJECT_ID"]},
    )
    for node in data.get("issues", {}).get("nodes", []):
        if identity in node.get("title", ""):
            return node["url"]
    return None


def create_issue(
    token: str,
    identity: str,
    issuer: str,
    subject: str,
    exchanges: int,
    sample_error: str,
) -> str:
    """Create a Linear issue and return its URL."""
    body = (
        f"## Detection\n\n"
        f"OctoSTS identity `{identity}` was called {exchanges} time(s) in the last "
        f"{LOOKBACK_HOURS}h, but no trust policy file exists at "
        f"`.github/chainguard/{identity}.sts.yaml` in this repo.\n\n"
        f"## Subject claim (for the stub)\n\n"
        f"- `issuer`: `{issuer}`\n"
        f"- `subject`: `{subject}`\n\n"
        f"## Sample error\n\n"
        f"```\n{sample_error}\n```\n\n"
        f"## Action\n\n"
        f"Add a trust policy at `.github/chainguard/{identity}.sts.yaml`. "
        f"See [`.claude/skills/octosts-policy.md`](.claude/skills/octosts-policy.md) "
        f"in this repo for the stub format. The linear-materializer should pick "
        f"this up automatically and open a draft PR.\n"
    )
    mutation = """
    mutation ($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { identifier title url }
      }
    }
    """
    label_ids = [s.strip() for s in os.environ["LINEAR_LABEL_IDS"].split(",") if s.strip()]
    data = linear_graphql(
        token,
        mutation,
        {
            "input": {
                "title": f"OctoSTS: trust policy missing for `{identity}`",
                "description": body,
                "teamId": os.environ["LINEAR_TEAM_ID"],
                "projectId": os.environ["LINEAR_PROJECT_ID"],
                "labelIds": label_ids,
            }
        },
    )
    create = data.get("issueCreate") or {}
    if not create.get("success"):
        raise SystemExit(f"failed to create linear issue for {identity}: {data!r}")
    return create["issue"]["url"]


def main() -> int:
    existing = list_existing_policies()
    print(f"existing trust policies in repo: {len(existing)}")

    rows = run_bq_query()
    print(f"identities with `no trust policy` errors in last {LOOKBACK_HOURS}h: {len(rows)}")

    missing = [r for r in rows if r["identity"] not in existing]
    print(f"missing trust policies: {len(missing)}")
    if not missing:
        return 0

    token = mint_linear_token()

    created = 0
    skipped = 0
    for row in missing:
        identity = row["identity"]
        if existing_url := find_open_issue(token, identity):
            print(f"  - {identity}: open issue already exists ({existing_url}), skipping")
            skipped += 1
            continue
        url = create_issue(
            token=token,
            identity=identity,
            issuer=(row.get("issuer") or "(unknown)"),
            subject=(row.get("subject") or "(unknown)"),
            exchanges=int(row.get("exchanges") or 0),
            sample_error=(row.get("sample_error") or "").replace("```", "ʼʼʼ"),
        )
        print(f"  - {identity}: created issue {url}")
        created += 1

    print(f"summary: created {created}, skipped {skipped} (deduped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
