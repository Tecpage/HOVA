const $ = (id) => document.getElementById(id);

function esc(s){
  if(s === undefined || s === null) return "";
  return String(s);
}

async function apiGet(path){
  const res = await fetch(path, { cache: "no-store" });
  if(!res.ok){
    const txt = await res.text().catch(() => "");
    throw new Error("HTTP " + res.status + ": " + (txt || path));
  }
  return await res.json();
}

async function apiPost(path, body){
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {})
  });
  if(!res.ok){
    const txt = await res.text().catch(() => "");
    throw new Error("HTTP " + res.status + ": " + (txt || path));
  }
  return await res.json();
}

function renderApps(apps){
  const box = $("apps");
  if(!box) return;
  box.innerHTML = "";

  (apps || []).forEach((a) => {
    const row = document.createElement("div");
    row.className = "appRow";
    row.innerHTML = `
      <div>
        <div class="appName">${esc(a.name)}</div>
        <div class="small">${esc(a.workdir)} · ${esc(a.script)} ${esc((a.args || []).join(" "))}</div>
      </div>
      <div class="rowBtns">
        <button data-act="run" data-id="${esc(a.id)}">Start</button>
      </div>
    `;
    box.appendChild(row);
  });

  box.querySelectorAll("button[data-act='run']").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-id");
      btn.disabled = true;
      const oldText = btn.textContent;
      btn.textContent = "Start…";
      try{
        $("meta").textContent = "Starte: " + id + " …";
        const out = await apiPost("/api/run", { id: id });
        if(out && out.ok){
          $("meta").textContent = "Gestartet: " + id;
        } else {
          $("meta").textContent = "Fehler: " + (out && out.error ? out.error : "unbekannt");
        }
      } catch(e){
        $("meta").textContent = "Fehler: " + (e && e.message ? e.message : e);
      } finally {
        btn.textContent = oldText;
        btn.disabled = false;
        setTimeout(() => refresh().catch(() => {}), 300);
      }
    });
  });
}

async function refresh(){
  try{
    const j = await apiGet("/api/apps");
    if(j && j.error){
      $("meta").textContent = "Fehler: " + j.error;
      renderApps([]);
      return;
    }
    const apps = (j && j.apps) ? j.apps : [];
    $("meta").textContent = "Apps geladen: " + apps.length;
    renderApps(apps);
  } catch(e){
    $("meta").textContent = "Fehler: " + (e && e.message ? e.message : e);
  }
}

refresh();
setInterval(() => refresh().catch(() => {}), 10000);
