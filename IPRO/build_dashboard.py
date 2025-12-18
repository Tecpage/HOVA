#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IPRO Dashboard Builder (stable, f-string-free)

Generates:
- dashboard/index.html (styled)  -> contains markers: healthBanner, Miet-Nr.
- dashboard/app.js (raw JS)      -> contains marker: tenant_status
- dashboard/data/*.json          -> tenants_indexation, payments_rent_roll, build_meta (with fingerprint), quality_report, index

Reads:
- tenants.yaml
- payments.yaml
- dashbord.yaml
- tenant_no_overrides.yaml (optional; format: overrides: - tenant_no: ".." names: [...])

Does NOT modify any YAML.
"""

from __future__ import annotations

import os
import json
import re
import hashlib
import datetime as dt
from typing import Any, Dict, List, Tuple

ROOT = os.path.abspath(os.path.dirname(__file__))
DASH_DIR = os.path.join(ROOT, "dashboard")
DATA_DIR = os.path.join(DASH_DIR, "data")

TENANTS_YAML = os.path.join(ROOT, "tenants.yaml")
PAYMENTS_YAML = os.path.join(ROOT, "payments.yaml")
DASH_CFG_YAML = os.path.join(ROOT, "dashbord.yaml")
TENANT_NO_OVERRIDES_YAML = os.path.join(ROOT, "tenant_no_overrides.yaml")

os.makedirs(DATA_DIR, exist_ok=True)


def _load_yaml(path: str) -> Any:
    import yaml  # type: ignore
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _sha256_file(path: str) -> str:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as bf:
            for chunk in iter(lambda: bf.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _norm_name(s: Any) -> str:
    if s is None:
        return ""
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9äöüß]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tenant_no_sort_key(no: Any) -> Tuple[int, int, str]:
    s = str(no).strip() if no is not None else ""
    if s == "" or s == "—":
        return (2, 999999, "")
    try:
        return (0, int(s), s)
    except Exception:
        return (1, 999998, s.lower())


def _num(x: Any) -> float:
    try:
        if x is None:
            return 0.0
        return float(str(x).replace(",", "."))
    except Exception:
        return 0.0


def _load_overrides(path: str) -> Dict[str, str]:
    """Return map normalized-name -> tenant_no."""
    if not os.path.exists(path):
        return {}
    doc = _load_yaml(path) or {}
    items = doc.get("overrides") or []
    out: Dict[str, str] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        tno = str(it.get("tenant_no") or "").strip()
        if not tno:
            continue
        for nm in it.get("names") or []:
            k = _norm_name(nm)
            if k:
                out[k] = tno
    return out


def _latest_period(payments: List[dict]) -> str:
    latest = ""
    for p in payments:
        if isinstance(p, dict) and p.get("period"):
            latest = max(latest, str(p.get("period")))
    return latest


def build() -> None:
    tenants_doc = _load_yaml(TENANTS_YAML) or {}
    payments_doc = _load_yaml(PAYMENTS_YAML) or {}
    dash_doc = _load_yaml(DASH_CFG_YAML) or {}

    title = ((dash_doc.get("dashboard") or {}).get("title")) or "IPRO Dashboard – Mieter & Indexierung"
    vpi_cur = (((dash_doc.get("dashboard") or {}).get("vpi") or {}).get("current") or {})
    vpi_month = vpi_cur.get("month")
    vpi_value = vpi_cur.get("value")

    tenants: List[dict] = tenants_doc.get("tenants") or []
    payments: List[dict] = payments_doc.get("payments") or []

    overrides = _load_overrides(TENANT_NO_OVERRIDES_YAML)

    tenants_by_id: Dict[str, dict] = {}
    for t in tenants:
        if isinstance(t, dict) and t.get("id"):
            tenants_by_id[str(t.get("id"))] = t

    pay_tno_by_tid: Dict[str, str] = {}
    for p in payments:
        if not isinstance(p, dict):
            continue
        tid = p.get("tenant_id")
        tno = p.get("tenant_no")
        if tid and tno:
            pay_tno_by_tid[str(tid)] = str(tno)

    # Resolve tenant_no: overrides -> tenants.yaml -> payments.yaml
    resolved_tno_by_id: Dict[str, str] = {}
    for tid, t in tenants_by_id.items():
        name = t.get("name")
        k = _norm_name(name)
        tno = t.get("tenant_no")
        if (not tno) and (k in overrides):
            tno = overrides[k]
        if (not tno) and (tid in pay_tno_by_tid):
            tno = pay_tno_by_tid[tid]
        resolved_tno_by_id[tid] = str(tno) if tno is not None else ""

    # tenants_indexation.json
    index_rows: List[dict] = []
    for tid, t in tenants_by_id.items():
        tags = t.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        tenant_status = "Beendet" if "inactive" in tags else "Aktiv"

        ix = t.get("indexation") if isinstance(t.get("indexation"), dict) else None
        status = "—" if not ix else "OK"
        delta = None
        new_net = None
        if ix and vpi_value is not None:
            base_val_f = _num(ix.get("base_index_value"))
            thr_f = _num(ix.get("threshold_percent"))
            if base_val_f > 0:
                delta = ((float(vpi_value) / base_val_f) - 1.0) * 100.0
                if thr_f > 0 and delta > thr_f:
                    status = "HANDLUNGSBEDARF"
                    base_amt = _num(ix.get("base_net_amount"))
                    if base_amt >= 0:
                        new_net = base_amt * (float(vpi_value) / base_val_f)
                else:
                    status = "OK"

        index_rows.append({
            "tenant_id": tid,
            "tenant_no": resolved_tno_by_id.get(tid, ""),
            "tenant_status": tenant_status,
            "name": t.get("name"),
            "delta_vpi_percent": delta,
            "status": status,
            "new_net_amount": new_net,
            "indexation_details": ix,
        })

    index_rows.sort(key=lambda r: (_tenant_no_sort_key(r.get("tenant_no")), _norm_name(r.get("name"))))

    tenants_view = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "tenants.yaml",
        "current_vpi": {"month": vpi_month, "value": vpi_value},
        "rows": index_rows,
    }
    _write_json(os.path.join(DATA_DIR, "tenants_indexation.json"), tenants_view)

    # payments_rent_roll.json (latest period; include all tenants; fill zeros)
    latest = _latest_period(payments)
    pay_by_tid: Dict[str, dict] = {}
    for p in payments:
        if not isinstance(p, dict):
            continue
        if latest and str(p.get("period")) != latest:
            continue
        tid = p.get("tenant_id")
        if tid:
            pay_by_tid[str(tid)] = p

    pay_rows: List[dict] = []
    for tid, t in tenants_by_id.items():
        tags = t.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        tenant_status = "Beendet" if "inactive" in tags else "Aktiv"

        p = pay_by_tid.get(tid)
        comps: Dict[str, Any] = {}
        total_net = 0.0
        total_gross = 0.0
        if isinstance(p, dict):
            comps = p.get("components") or {}
            if not isinstance(comps, dict):
                comps = {}
            total_net = _num(p.get("total_net"))
            total_gross = _num(p.get("total_gross"))

        pay_rows.append({
            "tenant_id": tid,
            "tenant_no": resolved_tno_by_id.get(tid, ""),
            "tenant_status": tenant_status,
            "name": t.get("name"),
            "period": latest,
            "base_rent_net": _num(comps.get("base_rent_net")),
            "bk_nk": _num(comps.get("bk_nk")),
            "heating": _num(comps.get("heating")),
            "storage_cellar": _num(comps.get("storage_cellar")),
            "parking": _num(comps.get("parking")),
            "cleaning": _num(comps.get("cleaning")),
            "mailroom": _num(comps.get("mailroom")),
            "management_fee": _num(comps.get("management_fee")),
            "other_services": _num(comps.get("other_services")),
            "total_net": total_net,
            "total_gross": total_gross,
        })

    pay_rows.sort(key=lambda r: (_tenant_no_sort_key(r.get("tenant_no")), _norm_name(r.get("name"))))

    payments_view = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "payments.yaml",
        "period": latest,
        "rows": pay_rows,
    }
    _write_json(os.path.join(DATA_DIR, "payments_rent_roll.json"), payments_view)

    # build_meta.json with fingerprint
    fp_inputs = {
        "schema_version": 4,
        "tenants_yaml": _sha256_file(TENANTS_YAML),
        "payments_yaml": _sha256_file(PAYMENTS_YAML),
        "dash_cfg_yaml": _sha256_file(DASH_CFG_YAML),
        "tenant_no_overrides_yaml": _sha256_file(TENANT_NO_OVERRIDES_YAML),
        "build_script": _sha256_file(os.path.abspath(__file__)),
        "vpi_month": vpi_month or "",
        "vpi_value": vpi_value if vpi_value is not None else None,
        "latest_payment_period": latest,
    }
    fp = hashlib.sha256(json.dumps(fp_inputs, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    build_meta = {
        "generated_at": tenants_view["generated_at"],
        "root": ROOT,
        "cwd": os.getcwd(),
        "build_script": os.path.abspath(__file__),
        "vpi_month": vpi_month,
        "vpi_value": vpi_value,
        "fingerprint": fp,
        "fingerprint_inputs": fp_inputs,
        "stats": {"tenants_total": len(index_rows), "payments_rows": len(pay_rows)},
    }
    _write_json(os.path.join(DATA_DIR, "build_meta.json"), build_meta)

    # quality_report.json
    warnings: List[Any] = []
    missing_no = [r["tenant_id"] for r in index_rows if not str(r.get("tenant_no") or "").strip()]
    if missing_no:
        warnings.append({"code": "TENANT_NO_MISSING", "message": str(len(missing_no)) + " tenant(s) without tenant_no", "tenant_ids": missing_no})

    mismatches = []
    for p in payments:
        if not isinstance(p, dict):
            continue
        if latest and str(p.get("period")) != latest:
            continue
        comps = p.get("components") or {}
        if not isinstance(comps, dict):
            continue
        s = round(sum(_num(v) for v in comps.values()), 2)
        tn = round(_num(p.get("total_net")), 2)
        if s != tn:
            mismatches.append({"id": p.get("id"), "tenant_id": p.get("tenant_id"), "period": p.get("period"), "stated_total_net": tn, "calc_total_net": s})
    if mismatches:
        warnings.append({"code": "PAYMENT_TOTAL_MISMATCH", "message": str(len(mismatches)) + " payment(s) with total_net != sum(components)", "details": mismatches})

    quality = {
        "generated_at": tenants_view["generated_at"],
        "source": "build_dashboard.py",
        "latest_payment_period": latest,
        "errors": [],
        "warnings": warnings,
    }
    _write_json(os.path.join(DATA_DIR, "quality_report.json"), quality)

    # index.json
    _write_json(os.path.join(DATA_DIR, "index.json"), {
        "generated_at": tenants_view["generated_at"],
        "build_meta": {"path": "dashboard/data/build_meta.json"},
        "datasets": [
            {"id": "tenants_indexation", "path": "dashboard/data/tenants_indexation.json", "source": "tenants.yaml"},
            {"id": "payments_rent_roll", "path": "dashboard/data/payments_rent_roll.json", "source": "payments.yaml"},
        ],
    })

    # index.html (NO f-string)
    html = """<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="styles.css?v=__STAMP__" />
</head>
<body>
  <header class="topbar ipro">
    <div class="title">IPRO Dashboard – Mieter &amp; Indexierung</div>
    <div class="meta" id="buildInfo">Build: …</div>
    <div class="actions">
      <button class="btn" id="btnCopyBuild" type="button">Build kopieren</button>
      <button class="btn" id="btnReload" type="button">Neu laden</button>
    </div>
  </header>

  <section class="filters">
    <div class="filtersLeft">
      <button class="btn" id="btnViewIndex" type="button">Indexierung</button>
      <button class="btn" id="btnViewPayments" type="button">Payment</button>
      <input id="q" placeholder="Suche: Name…" />
    </div>

    <div class="filtersRight">
      <span class="pill" id="kpiTotal">Mieter: —</span>
      <span class="pill" id="kpiIndexed">Indexiert: —</span>
      <span class="pill" id="kpiTriggered">Handlungsbedarf: —</span>
      <span class="muted" id="vpiInfo">VPI: —</span>
    </div>
  </section>

  <div id="healthBanner" class="healthBanner ok">
    <div id="status">Start…</div>
  </div>

  <main class="layout">
    <div class="tablewrap">
      <table class="tbl">
        <thead><tr id="theadRow"></tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>

    <aside class="panel">
      <div class="panelTitle">Info</div>
      <div class="panelHint">Hinweise und Debug.</div>
      <pre id="debugLog" class="panelBody"></pre>
    </aside>
  </main>

  <script defer src="app.js?v=__STAMP__"></script>
</body>
</html>
"""

    html = html.replace("__TITLE__", title).replace("__STAMP__", tenants_view["generated_at"])
    with open(os.path.join(DASH_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    # app.js must be raw; include marker tenant_status
    app_js = r"""// tenant_status
const TENANTS_JSON_PATH = "./data/tenants_indexation.json?v=" + Date.now();
const PAYMENTS_JSON_PATH = "./data/payments_rent_roll.json?v=" + Date.now();
const BUILD_META_PATH = "./data/build_meta.json?v=" + Date.now();
const QUALITY_PATH = "./data/quality_report.json?v=" + Date.now();

function $(id){return document.getElementById(id);}
function safe(x){return (x===null||x===undefined)?"":String(x);}
function setStatus(m){var s=$('status'); if(s) s.textContent=m;}
function banner(cls,msg){var b=$('healthBanner'); if(!b) return; b.classList.remove('ok','warn','fail'); if(cls) b.classList.add(cls); b.textContent=msg;}
function showDebug(obj){var d=$('debugLog'); if(!d) return; d.style.display='block'; d.textContent=(typeof obj==='string')?obj:JSON.stringify(obj,null,2);} 

function tenantNoKey(no){const s=safe(no).trim(); if(!s||s==='—') return [2, Number.MAX_SAFE_INTEGER, '']; const n=parseInt(s,10); if(!Number.isNaN(n)) return [0,n,s]; return [1, Number.MAX_SAFE_INTEGER-1, s.toLowerCase()];}
function sortByTenantNo(rows){return [...rows].sort((a,b)=>{const ka=tenantNoKey(a.tenant_no), kb=tenantNoKey(b.tenant_no); if(ka[0]!==kb[0]) return ka[0]-kb[0]; if(ka[1]!==kb[1]) return ka[1]-kb[1]; return safe(a.name).localeCompare(safe(b.name));});}
function fmtEUR(x){const n=Number(x); if(!Number.isFinite(n)) return '—'; return n.toLocaleString('de-DE',{minimumFractionDigits:2,maximumFractionDigits:2});}
function deltaLabel(delta){if(delta===null||delta===undefined||delta==='') return '—'; const n=Number(delta); if(!Number.isFinite(n)) return '—'; return n.toFixed(2)+'%';}

function formatIndexation(ix){
  if(!ix) return '—';

  var vpi = (TENANTS && TENANTS.current_vpi) ? TENANTS.current_vpi : {};
  var curMonth = safe(vpi.month) || '—';
  var curVal = (vpi.value===null||vpi.value===undefined) ? null : Number(vpi.value);

  var baseMonth = safe(ix.base_index_month) || '—';
  var baseVal = (ix.base_index_value===null||ix.base_index_value===undefined) ? null : Number(ix.base_index_value);
  var thr = (ix.threshold_percent===null||ix.threshold_percent===undefined) ? null : Number(ix.threshold_percent);
  var baseNet = (ix.base_net_amount===null||ix.base_net_amount===undefined) ? null : Number(ix.base_net_amount);
  var cur = safe(ix.currency) || 'EUR';

  var delta = null;
  if(curVal!==null && baseVal!==null && Number.isFinite(curVal) && Number.isFinite(baseVal) && baseVal>0){
    delta = ((curVal/baseVal)-1.0)*100.0;
  }

  var badge = '';
  if(delta===null || thr===null || !Number.isFinite(thr)){
    badge = '<div class="pill warn">Prüfung nicht möglich</div>';
  } else if(delta > thr){
    badge = '<div class="pill needs-action">Handlungsbedarf ('+delta.toFixed(2)+'%)</div>';
  } else {
    badge = '<div class="pill ok">Kein Handlungsbedarf ('+delta.toFixed(2)+'%)</div>';
  }

  var proposal = '—';
  if(delta!==null && thr!==null && Number.isFinite(thr) && delta>thr && baseNet!==null && baseVal!==null && curVal!==null && baseVal>0){
    var newNet = baseNet*(curVal/baseVal);
    if(Number.isFinite(newNet)) proposal = fmtEUR(newNet) + ' ' + cur;
  }

  var parts = [];
  parts.push(badge);
  parts.push('<div><b>Schwelle:</b> '+(thr!==null&&Number.isFinite(thr)?thr:'—')+'%</div>');
  parts.push('<div><b>Basis:</b> '+baseMonth+' = '+(baseVal!==null&&Number.isFinite(baseVal)?String(baseVal):'—')+'</div>');
  parts.push('<div><b>Basisnetto:</b> '+(baseNet!==null&&Number.isFinite(baseNet)?(fmtEUR(baseNet)+' '+cur):'—')+'</div>');
  parts.push('<div><b>Aktuell:</b> '+curMonth+' = '+(curVal!==null&&Number.isFinite(curVal)?String(curVal):'—')+'</div>');
  parts.push('<div><b>Vorschlag neu:</b> '+proposal+'</div>');
  if(ix.notes){ parts.push('<div class="muted">'+safe(ix.notes)+'</div>'); }
  return parts.join('');
}


async function loadJson(url){const r=await fetch(url,{cache:'no-store'}); if(!r.ok) throw new Error('HTTP '+r.status+' '+url); return await r.json();}

let TENANTS=null, PAYMENTS=null, META=null, QUALITY=null;
let VIEW='index';

async function loadAll(){
  try{
    setStatus('build_meta…'); META=await loadJson(BUILD_META_PATH);
    var bi=$('buildInfo'); if(bi && META){ var fp12=(META.fingerprint)?String(META.fingerprint).slice(0,12):'—'; var ga=META.generated_at?String(META.generated_at).replace('T',' ').replace('+00:00','Z'):'—'; var vm=(META.vpi_month!==undefined&&META.vpi_month!==null)?String(META.vpi_month):'—'; var vv=(META.vpi_value!==undefined&&META.vpi_value!==null)?String(META.vpi_value):'—'; bi.textContent='Build: '+fp12+' · '+ga+' · VPI '+vm+' = '+vv; }
    setStatus('tenants…'); TENANTS=await loadJson(TENANTS_JSON_PATH);
    setStatus('payments…'); PAYMENTS=await loadJson(PAYMENTS_JSON_PATH);
    setStatus('quality…'); QUALITY=await loadJson(QUALITY_PATH);
    const fp=(META&&META.fingerprint)?String(META.fingerprint).slice(0,12):'—';
    const warns=(QUALITY&&QUALITY.warnings)?QUALITY.warnings.length:0;
    var summary=[];
    if(warns>0 && QUALITY && Array.isArray(QUALITY.warnings)) {
      for(var i=0;i<QUALITY.warnings.length;i++){
        var w=QUALITY.warnings[i]||{};
        if(w.code==='TENANT_NO_MISSING') summary.push('Miet-Nr. fehlt bei '+String((w.tenant_ids||[]).length)+' Mieter(n).');
        else if(w.code==='PAYMENT_TOTAL_MISMATCH') summary.push('Zahlungen: Summe Bausteine ≠ Netto (Rundung/Erfassung prüfen).');
        else summary.push(String(w.code||'WARN')+': '+String(w.message||''));
        if(summary.length>=3) break;
      }
    }
    if(warns>0) banner('warn','OK mit Hinweisen – Build '+fp+(summary.length?('\n• '+summary.join('\n• ')):''));
    else banner('ok','OK – Build '+fp);
    showDebug({build_meta:META, quality:QUALITY});
    return true;
  } catch(e){
    banner('fail','FEHLER – siehe Debug');
    showDebug({error:(e&&e.message)?e.message:String(e), url:location.href});
    setStatus('Fehler');
    return false;
  }
}

function setHead(cols){var tr=$('theadRow'); if(!tr) return; tr.innerHTML=cols.map(c=>'<th>'+c+'</th>').join('');}

function renderIndex(){
  setHead(['Miet-Nr.','Status','Name','Δ VPI %','Index-Status','Neuer Netto-Betrag','Indexierung (Details)']);
  var tb=$('tbody'); if(!tb) return; tb.innerHTML='';
  var rows=sortByTenantNo((TENANTS&&TENANTS.rows)?TENANTS.rows:[]);
  for(var i=0;i<rows.length;i++){
    var r=rows[i];
    var idx = safe(r.status);
    var idxLabel = (idx==='OK')?'Kein Handlungsbedarf':(idx==='HANDLUNGSBEDARF')?'Handlungsbedarf':'—';
    var newNet = (r.new_net_amount===null||r.new_net_amount===undefined)?'—':(fmtEUR(r.new_net_amount)+' EUR');
    var tr=document.createElement('tr');
    tr.innerHTML='<td>'+ (safe(r.tenant_no)||'—') +'</td><td>'+safe(r.tenant_status)+'</td><td>'+safe(r.name)+'</td><td>'+deltaLabel(r.delta_vpi_percent)+'</td><td>'+idxLabel+'</td><td style="text-align:right">'+newNet+'</td><td>'+formatIndexation(r.indexation_details)+'</td>';
    tb.appendChild(tr);
  }
  var vpi=(TENANTS&&TENANTS.current_vpi)?TENANTS.current_vpi:{};
  var vi=$('vpiInfo'); if(vi) vi.textContent='VPI (2020=100) aktuell: '+(safe(vpi.month)||'—')+' = '+(vpi.value!==null&&vpi.value!==undefined?safe(vpi.value):'—');
  var kt=$('kpiTotal'); if(kt) kt.textContent='Mieter: '+rows.length;
  var ki=$('kpiIndexed'); if(ki) ki.textContent='Indexiert: '+rows.filter(x=>x.indexation_details).length;
  var kh=$('kpiTriggered'); if(kh) kh.textContent='Handlungsbedarf: '+rows.filter(x=>x.status==='HANDLUNGSBEDARF').length;
}

function renderPayments(){
  setHead(['Miet-Nr.','Status','Name','Kaltmiete','BK/NK','Heizung','Lager/Keller','Parkplatz','Reinigung','Poststelle','Verwaltergeb.','sonstige DL','netto','brutto']);
  var tb=$('tbody'); if(!tb) return; tb.innerHTML='';
  var rows=sortByTenantNo((PAYMENTS&&PAYMENTS.rows)?PAYMENTS.rows:[]);
  for(var i=0;i<rows.length;i++){
    var r=rows[i];
    var tr=document.createElement('tr');
    tr.innerHTML='<td>'+ (safe(r.tenant_no)||'—') +'</td><td>'+safe(r.tenant_status)+'</td><td>'+safe(r.name)+'</td>'+
      '<td style="text-align:right">'+fmtEUR(r.base_rent_net)+'</td>'+
      '<td style="text-align:right">'+fmtEUR(r.bk_nk)+'</td>'+
      '<td style="text-align:right">'+fmtEUR(r.heating)+'</td>'+
      '<td style="text-align:right">'+fmtEUR(r.storage_cellar)+'</td>'+
      '<td style="text-align:right">'+fmtEUR(r.parking)+'</td>'+
      '<td style="text-align:right">'+fmtEUR(r.cleaning)+'</td>'+
      '<td style="text-align:right">'+fmtEUR(r.mailroom)+'</td>'+
      '<td style="text-align:right">'+fmtEUR(r.management_fee)+'</td>'+
      '<td style="text-align:right">'+fmtEUR(r.other_services)+'</td>'+
      '<td style="text-align:right"><b>'+fmtEUR(r.total_net)+'</b></td>'+
      '<td style="text-align:right"><b>'+fmtEUR(r.total_gross)+'</b></td>';
    tb.appendChild(tr);
  }
  var vi=$('vpiInfo'); if(vi) vi.textContent='Payments (Rent Roll) – Periode: '+((PAYMENTS&&PAYMENTS.period)?PAYMENTS.period:'—');
  var kt=$('kpiTotal'); if(kt) kt.textContent='Mieter: '+rows.length;
  var ki=$('kpiIndexed'); if(ki) ki.textContent='Periode: '+((PAYMENTS&&PAYMENTS.period)?PAYMENTS.period:'—');
  var sum=rows.reduce((s,x)=>s+(Number(x.total_net)||0),0);
  var kh=$('kpiTriggered'); if(kh) kh.textContent='Summe netto: '+fmtEUR(sum)+' EUR';
}

function wire(){
  var bi=$('btnViewIndex'); if(bi) bi.onclick=function(){VIEW='index'; renderIndex();};
  var bp=$('btnViewPayments'); if(bp) bp.onclick=function(){VIEW='payments'; renderPayments();};
  var br=$('btnReload'); if(br) br.onclick=function(){location.reload();};
  var cb=$('btnCopyBuild'); if(cb) cb.onclick=async function(){ try{ var bi=$('buildInfo'); var txt=bi?bi.textContent:''; if(navigator.clipboard&&txt){ await navigator.clipboard.writeText(txt); setStatus('Build kopiert'); } else { setStatus('Clipboard nicht verfügbar'); } }catch(e){ setStatus('Copy fehlgeschlagen'); } };
}

(async function(){
  var ok = await loadAll();
  wire();
  if(ok) renderIndex();
})();
"""

    with open(os.path.join(DASH_DIR, "app.js"), "w", encoding="utf-8") as f:
        f.write(app_js)

    print("[OK] dashboard generated:")
    print(" - ", os.path.join(DASH_DIR, "index.html"))
    print(" - ", os.path.join(DASH_DIR, "app.js"))
    print(" - ", os.path.join(DATA_DIR, "tenants_indexation.json"))
    print(" - ", os.path.join(DATA_DIR, "payments_rent_roll.json"))


if __name__ == "__main__":
    build()