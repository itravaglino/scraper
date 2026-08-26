(() => {
  const $ = (id) => document.getElementById(id);
  const TRIAGE_KEY = "fitbit-scraper-triage-v1";

  const SEV_ES = { alta: "Alta", media: "Media", baja: "Baja", info: "Info" };

  function loadTriage() {
    try {
      return JSON.parse(localStorage.getItem(TRIAGE_KEY) || "{}");
    } catch {
      return {};
    }
  }
  function saveTriage(map) {
    localStorage.setItem(TRIAGE_KEY, JSON.stringify(map));
  }

  function fmtStamp(iso, zone) {
    if (!iso) return "sin datos";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return new Intl.DateTimeFormat("es-AR", {
      timeZone: zone || "America/Buenos_Aires",
      dateStyle: "full",
      timeStyle: "short",
    }).format(d);
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fillSelect(sel, values) {
    const current = sel.value;
    const keep = sel.querySelector("option[value='']");
    sel.innerHTML = "";
    sel.appendChild(keep);
    for (const v of values) {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = v;
      sel.appendChild(o);
    }
    if ([...sel.options].some((o) => o.value === current)) sel.value = current;
  }

  function render(data) {
    const triage = loadTriage();
    const summary = data.summary || {};
    const clusters = data.clusters || [];
    const zone = data.timezone || "America/Buenos_Aires";

    $("run-stamp").dateTime = data.generated_at || "";
    $("run-stamp").textContent = fmtStamp(data.generated_at, zone);
    $("run-zone").textContent = `${zone} · corrida ${data.run_id || "—"}`;

    const kpis = [
      [summary.reports ?? 0, "Reportes reunidos"],
      [summary.new_clusters ?? 0, "Grupos nuevos"],
      [summary.recurring_clusters ?? 0, "Grupos recurrentes"],
      [summary.by_severity?.alta ?? 0, "Reportes de gravedad alta"],
    ];
    $("kpis").innerHTML = kpis
      .map(([n, label]) => `<article class="kpi"><b>${n}</b><span>${label}</span></article>`)
      .join("");

    const models = Object.keys(summary.by_model || {});
    const cats = [...new Set(clusters.map((c) => c.category_label).filter(Boolean))].sort();
    fillSelect($("f-model"), models);
    fillSelect($("f-cat"), cats);

    const maxModel = Math.max(1, ...Object.values(summary.by_model || { x: 1 }));
    $("model-bars").innerHTML = Object.entries(summary.by_model || {})
      .map(
        ([name, n]) =>
          `<li><div class="row"><span>${escapeHtml(name)}</span><span>${n}</span></div>
           <div class="bar"><i style="width:${Math.round((n / maxModel) * 100)}%"></i></div></li>`
      )
      .join("");

    $("source-list").innerHTML = (data.sources || [])
      .map((s) => {
        const cls = s.ok ? "ok" : "bad";
        const detail = s.ok ? `${s.kept}/${s.fetched}` : s.error || "error";
        return `<li><span>${escapeHtml(s.label || s.id)}</span><span class="${cls}">${escapeHtml(String(detail))}</span></li>`;
      })
      .join("");

    const q = $("q").value.trim().toLowerCase();
    const model = $("f-model").value;
    const cat = $("f-cat").value;
    const sev = $("f-sev").value;
    const rec = $("f-rec").value;
    const tri = $("f-triage").value;

    const filtered = clusters.filter((c) => {
      if (model && !(c.models || []).includes(model)) return false;
      if (cat && c.category_label !== cat) return false;
      if (sev && c.severity !== sev) return false;
      if (rec === "new" && c.recurring) return false;
      if (rec === "recurring" && !c.recurring) return false;
      const t = triage[c.id] || {};
      if (tri === "unset" && t.status) return false;
      if (tri && tri !== "unset" && t.status !== tri) return false;
      if (q) {
        const blob = [
          c.title,
          c.category_label,
          ...(c.models || []),
          ...(c.quotes || []).map((x) => x.text),
          ...(c.reports || []).map((x) => x.title),
        ]
          .join(" ")
          .toLowerCase();
        if (!blob.includes(q)) return false;
      }
      return true;
    });

    $("list-count").textContent = `${filtered.length} grupos visibles · ${summary.clusters || 0} en total`;
    $("empty").classList.toggle("hidden", filtered.length > 0);

    $("clusters").innerHTML = filtered
      .map((c) => {
        const t = triage[c.id] || {};
        const quotes = (c.quotes || [])
          .map(
            (qt) =>
              `<blockquote class="quote"><a href="${escapeHtml(qt.url || "#")}" target="_blank" rel="noopener">“${escapeHtml(qt.text)}”</a>
               <footer>${escapeHtml(qt.source || "")}${qt.title ? " · " + escapeHtml(qt.title) : ""}</footer></blockquote>`
          )
          .join("");
        const more = (c.reports || [])
          .map(
            (r) =>
              `<a href="${escapeHtml(r.url || "#")}" target="_blank" rel="noopener">${escapeHtml(r.title || r.url || "fuente")}</a>`
          )
          .join("");
        return `<article class="card ${escapeHtml(c.severity)}" data-id="${escapeHtml(c.id)}">
          <h3>${escapeHtml(c.title)}</h3>
          <div class="badges">
            <span class="badge sev-${escapeHtml(c.severity)}">Gravedad ${SEV_ES[c.severity] || c.severity}</span>
            <span class="badge">${c.count} reporte${c.count === 1 ? "" : "s"}</span>
            <span class="badge">${c.recurring ? "Recurrente" : "Nuevo"}</span>
            ${(c.models || []).map((m) => `<span class="badge">${escapeHtml(m)}</span>`).join("")}
            <span class="badge">${escapeHtml(c.category_label || "")}</span>
          </div>
          ${quotes}
          <details class="more"><summary>Enlaces a la fuente (${(c.reports || []).length})</summary>${more}</details>
          <div class="triage">
            <button data-status="real" class="${t.status === "real" ? "on" : ""}">Parece real</button>
            <button data-status="check" class="${t.status === "check" ? "on" : ""}">Hay que verificar</button>
            <button data-status="discard" class="${t.status === "discard" ? "on" : ""}">Descartar</button>
            <input data-note placeholder="Nota privada en este navegador" value="${escapeHtml(t.note || "")}">
          </div>
        </article>`;
      })
      .join("");
  }

  let cached = null;

  function bind() {
    ["q", "f-model", "f-cat", "f-sev", "f-rec", "f-triage"].forEach((id) => {
      $(id).addEventListener("input", () => cached && render(cached));
      $(id).addEventListener("change", () => cached && render(cached));
    });
    $("clusters").addEventListener("click", (ev) => {
      const btn = ev.target.closest("button[data-status]");
      if (!btn || !cached) return;
      const card = btn.closest("[data-id]");
      const map = loadTriage();
      const id = card.dataset.id;
      const cur = map[id] || {};
      cur.status = cur.status === btn.dataset.status ? "" : btn.dataset.status;
      map[id] = cur;
      saveTriage(map);
      render(cached);
    });
    $("clusters").addEventListener("change", (ev) => {
      if (!(ev.target instanceof HTMLInputElement) || !ev.target.matches("[data-note]")) return;
      const card = ev.target.closest("[data-id]");
      const map = loadTriage();
      const id = card.dataset.id;
      map[id] = { ...(map[id] || {}), note: ev.target.value };
      saveTriage(map);
    });
  }

  bind();
  fetch("data/latest.json", { cache: "no-store" })
    .then((r) => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then((data) => {
      cached = data;
      render(data);
    })
    .catch((err) => {
      $("run-stamp").textContent = "No se pudo cargar data/latest.json";
      $("empty").classList.remove("hidden");
      $("empty").textContent =
        "El tablero no encontró datos. Si acabás de clonar el repo, ejecutá python3 run.py o dispará el workflow de GitHub Actions. (" +
        err.message +
        ")";
    });
})();
