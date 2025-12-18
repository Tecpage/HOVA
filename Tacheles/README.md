Tacheles – Mängel (SSOT: Tacheles.yaml)
=================

Enthält nur das, was gebraucht wird:

- `Tacheles.yaml` (Single Source of Truth)
- `start_dashboard.command` (Start)
- `dashboard_server.py` (lokaler Server)
- `dashboard/` (index.html + app.js + styles.css)

Start:
  chmod +x start_dashboard.command
  ./start_dashboard.command 8010

Excel Export:
  Button "Excel" im Dashboard (benötigt openpyxl):
  python3 -m pip install --user pyyaml openpyxl
