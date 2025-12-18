# Reporting Dashboard Suite (Portal + IPRO + Tacheles)

This repository is structured for a **single-repo GitHub Pages deployment** (Portal + IPRO + Tacheles + Project H placeholder).

## Structure

- **Portal/** → Landing page (links to the dashboards + Project H)
- **IPRO/** → Source data (YAML) + generator (`build_dashboard.py`) → outputs `IPRO/dashboard/`
- **Tacheles/** → Source data (`Tacheles.yaml`) + dashboard frontend (`dashboard/`)
  - `Tacheles/build_static.py` exports `Tacheles.yaml` to `Tacheles/dashboard/data.json`
  - Frontend tries `/api/data` first (local server mode) and falls back to `data.json` (static / read-only online)
- **H/** → Placeholder page for the next project (uses white “H” on Holiday-Inn green in the Portal icon)

## Deployment (GitHub Pages)

A GitHub Actions workflow is included:

- `.github/workflows/pages.yml`

On every push to `main`, it will:

1. Install Python dependencies (`pyyaml`)
2. Run `python IPRO/build_dashboard.py`
3. Run `python Tacheles/build_static.py`
4. Assemble a `public/` folder:
   - `public/`       ← Portal root
   - `public/ipro/`  ← IPRO dashboard
   - `public/tacheles/` ← Tacheles dashboard (read-only online)
   - `public/h/`     ← Project H placeholder
5. Deploy to GitHub Pages.

To enable Pages:
- Repository → **Settings → Pages → Build and deployment → Source: GitHub Actions**

## Security note (important)

GitHub Pages sites are **public by default**, even when the repository is private, unless you use GitHub Enterprise Cloud with Pages access control.

Do NOT publish sensitive YAML data to a publicly accessible Pages site.
