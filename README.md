# `.github` — organization meta repository

This is GitHub's **special `.github` repository** for the ScamAI organization. It isn't a
product — it holds the org's public profile page, the default community-health files that
every other repo inherits, and a small bit of profile automation. If you landed here
wondering "what is this repo for?", this README explains each piece and how GitHub uses it.

## What's in here

| Path | What it is | How GitHub uses it |
|---|---|---|
| `profile/README.md` | The **org profile page** | Rendered at **https://github.com/scamai** (the public landing page for the org). Editing this changes what the world sees. |
| `profile/*.svg` | Logos + generated contribution-wall images | Referenced by `profile/README.md`. |
| `SECURITY.md` | Security policy | Shown as the default **Security** policy for any org repo that doesn't define its own. |
| `SUPPORT.md` | How to get help | Shown as the default **Support** link for any org repo without its own. |
| `.github/workflows/contribution-wall.yml` | Scheduled workflow | Regenerates the contribution-wall SVGs on the profile. |
| `scripts/contribution_wall.py` | Generator script | Builds the contribution-wall images the workflow commits. |

## Why a repo named `.github`?

GitHub gives every org one repo named `.github` with special powers:

- **Profile** — `profile/README.md` is published on the org's public page.
- **Default community health files** — `SECURITY.md`, `SUPPORT.md`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, and issue/PR templates placed here become the **org-wide defaults**.
  Any repo that doesn't ship its own falls back to the ones here, so you maintain them once.

## Common edits

- **Update the public org page** → edit `profile/README.md`. ⚠️ This is **public** — it's the
  first thing visitors and customers see. Review wording/links before merging.
- **Add an org-wide default** (e.g. `CONTRIBUTING.md`, an issue template under
  `.github/ISSUE_TEMPLATE/`) → add the file here; every repo without its own inherits it.
- **Change the contribution wall** → edit `scripts/contribution_wall.py`; the workflow
  refreshes the SVGs.

## Related

- **`scamai/meta`** — the org **governance** hub (repo catalog, policy-as-code, audit
  reports, consolidation tooling). That's the engineering source of truth for *how the org's
  repos are organized*; this `.github` repo is just the GitHub-rendered profile + defaults.

---

> ℹ️ Note: this repository is **public**. Keep anything added here non-confidential.
