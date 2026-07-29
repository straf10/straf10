# Agent notes

This repository is a **GitHub profile README** (`straf10/straf10`). There is no application server, database, package.json, or test suite.

## Cursor Cloud specific instructions

### What this repo is

- `README.md` is the product — rendered by GitHub on [github.com/straf10](https://github.com/straf10).
- All graphics are **self-hosted SVGs** (no third-party badge/stats CDNs). The whole page makes **zero** third-party image requests.
- Stat graphics + section headings: `scripts/generate_stats.py` (Python **stdlib only** + GitHub GraphQL).
- ASCII portrait: `scripts/generate_portrait.py` + `scripts/embed_portrait_font.py` (needs deps in `scripts/requirements.txt`; first rembg run downloads a ~176 MB u2net model into `~/.u2net/`).
- Stats refresh: `.github/workflows/stats.yml` (`workflow_dispatch` or cron). **No `push` trigger** — the job commits, and a push trigger would loop.
- Portrait refresh: `.github/workflows/portrait.yml` — runs on **Actions → refresh portrait → Run workflow**, or automatically when `scripts/source/portrait.jpg` (also `.jpeg` / `.png`) is pushed to `main`. First CI run downloads the ~176 MB rembg model.

### Useful local commands

```bash
# Refresh stats / heading SVGs (stdlib only; needs any GitHub token)
GITHUB_TOKEN="$(gh auth token)" GH_LOGIN=straf10 python3 scripts/generate_stats.py

# Rebuild the portrait locally (or use Actions → refresh portrait online)
python3 -m pip install --user -q -r scripts/requirements.txt
python3 scripts/generate_portrait.py   # reads portrait.jpg / .jpeg / .png
python3 scripts/embed_portrait_font.py

# Preview README (GitHub-flavoured). Prefer a tall viewport and wait ~5s —
# fullPage screenshots restart SMIL and leave animated SVGs blank.
export PATH="$HOME/.local/bin:$PATH"
grip README.md 0.0.0.0:6419
```

### Portrait photo requirements

ASCII has ~13 brightness levels and draws with **shadow**, not detail. A usable source photo:

- Side light (~45°), face filling the frame (chin to hair), 1200px+ crop
- Plain background; slight angle, not dead-on
- Do **not** use a back-view / landscape / night city shot — it will not resolve as a face at 90 columns

### Gotchas

- GitHub strips `<style>`, inline SVG, and most presentation attributes from README markdown. Motion must be SMIL inside committed SVG files; custom typeface → image.
- Prefer `<samp>` over backticks for stack/meta rows (monospace without the grey chip).
- Hard-wrap body lines with `<br>` around ~76 characters — full-width paragraphs are ~110 chars.
- Language totals cover **public** repos only (`privacy: PUBLIC`) so personal tokens and workflow tokens agree.
- Pin the contribution window to whole UTC days in the generator (already done) or nightly commits will thrash the sparkline.
- Let the Actions job own generated stats SVGs when possible — regenerating locally with a different token/clock can cause merge noise.
- Do not reintroduce third-party README widgets (shields.io, vercel stats, contribution snake, etc.).
- There is nothing to lint/test/build in the usual app sense; validate by regenerating SVGs and previewing the README.
