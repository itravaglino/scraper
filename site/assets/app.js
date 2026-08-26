(() => {
  const $ = (id) => document.getElementById(id);
  const TRIAGE_KEY = "fitbit-scraper-triage-v1";
  const SEV_ES = { alta: "Alta", media: "Media", baja: "Baja" };
  const KIND_ES = {
    reddit: "Reddit",
    youtube: "YouTube",
    tiktok: "TikTok",
    instagram: "Instagram",
    web: "Web / foros",
    news: "Noticias",
    itunes: "App Store",
    hackernews: "Hacker News",
  };
  const POL_TITLE = {
    mala: "Casos negativos",
    buena: "Buenas noticias",
    revisar: "Para revisar",
  };
  const RANGE_LABEL = {
    1: "día",
    7: "semana",
    30: "mes",
    90: "trimestre",
    365: "año",
    all: "todo",
  };

  const state = {
    polarity: "mala",
    range: 30,
  };

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

  function fmtShort(iso, zone) {
    if (!iso) return "sin fecha";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return new Intl.DateTimeFormat("es-AR", {
      timeZone: zone || "America/Buenos_Aires",
      dateStyle: "medium",
    }).format(d);
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fillSelect(sel, values, labels) {
    const current = sel.value;
    const keep = sel.querySelector("option[value='']");
    sel.innerHTML = "";
    sel.appendChild(keep);
    for (const v of values) {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = (labels && labels[v]) || v;
      sel.appendChild(o);
    }
    if ([...sel.options].some((o) => o.value === current)) sel.value = current;
  }

  function inRange(iso, rangeDays) {
    if (rangeDays == null) return true;
    if (!iso) return rangeDays >= 365;
    const t = Date.parse(iso);
    if (Number.isNaN(t)) return rangeDays >= 365;
    return Date.now() - t <= rangeDays * 86400000;
  }

  function filterClusterReports(cluster, rangeDays) {
    const reports = (cluster.reports || []).filter((r) => inRange(r.created_at, rangeDays));
    const quotes = (cluster.quotes || []).filter(
      (q) => !q.created_at || inRange(q.created_at, rangeDays)
    );
    if (!reports.length && !inRange(cluster.last_report_at, rangeDays)) {
      if (cluster.last_report_at || (cluster.reports || []).some((r) => r.created_at)) {
        return null;
      }
      if (rangeDays != null && rangeDays < 365) return null;
    }
    if ((cluster.reports || []).length && !reports.length) return null;
    return {
      ...cluster,
      reports: reports.length ? reports : cluster.reports || [],
      quotes: quotes.length ? quotes : cluster.quotes || [],
      count: reports.length || cluster.count,
    };
  }

  function render(data) {
    const triage = loadTriage();
    const summary = data.summary || {};
    const clusters = data.clusters || [];
    const zone = data.timezone || "America/Buenos_Aires";
    const rangeDays = state.range === "all" ? null : Number(state.range);

    $("run-stamp").dateTime = data.generated_at || "";
    $("run-stamp").textContent = fmtStamp(data.generated_at, zone);
    $("run-zone").textContent = `${zone} · corrida ${data.run_id || "—"}`;

    const runUrl =
      data.run_workflow_url ||
      `https://github.com/${document.body.dataset.repo}/actions/workflows/${document.body.dataset.workflow}`;
    $("btn-run").href = runUrl;

    const inTime = clusters
      .map((c) => filterClusterReports(c, rangeDays))
      .filter(Boolean);

    const counts = { mala: 0, buena: 0, revisar: 0 };
    const alta = { n: 0 };
    for (const c of inTime) {
      const p = c.polarity || "revisar";
      counts[p] = (counts[p] || 0) + (c.count || 0);
      if (p === "mala" && c.severity === "alta") alta.n += c.count || 0;
    }
    // Prefer report-level polarity counts when the payload still has summary.
    const pol = summary.by_polarity || {};
    const kpis = [
      [counts.mala || pol.mala || 0, "Malas noticias", "mala"],
      [counts.buena || pol.buena || 0, "Buenas noticias", "buena"],
      [counts.revisar || pol.revisar || 0, "Para revisar", "revisar"],
      [alta.n || summary.by_severity?.alta || 0, "Gravedad alta (malas)", "alta"],
    ];
    $("kpis").innerHTML = kpis
      .map(
        ([n, label, key]) =>
          `<button type="button" class="kpi ${key} ${state.polarity === key ? "on" : ""}" data-kpi="${key}">
            <b>${n}</b><span>${label}</span></button>`
      )
      .join("");

    $("sev-wrap").classList.toggle("hidden", state.polarity !== "mala");

    const models = Object.keys(summary.by_model || {});
    const cats = [...new Set(clusters.map((c) => c.category_label).filter(Boolean))].sort();
    const kinds = [
      ...new Set(
        clusters.flatMap((c) => c.source_kinds || []).filter(Boolean)
      ),
    ].sort();
    const langs = [
      ...new Set(clusters.flatMap((c) => c.languages || []).filter(Boolean)),
    ].sort();
    const langLabels = {};
    for (const c of clusters) {
      (c.languages || []).forEach((code, i) => {
        langLabels[code] = (c.language_labels || [])[i] || code;
      });
    }
    fillSelect($("f-model"), models);
    fillSelect($("f-cat"), cats);
    fillSelect($("f-kind"), kinds, KIND_ES);
    fillSelect($("f-lang"), langs, langLabels);

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
        const st = s.state || (s.ok ? "ok" : "error");
        const cls = st === "ok" ? "ok" : st === "skip" ? "skip" : "bad";
        const detail = s.ok
          ? `${s.kept}/${s.fetched}`
          : s.error || st;
        const kind = KIND_ES[s.kind] ? ` · ${KIND_ES[s.kind]}` : "";
        return `<li><span><span class="pill ${cls}">${escapeHtml(st)}</span>${escapeHtml((s.label || s.id) + kind)}</span><span class="${cls}">${escapeHtml(String(detail))}</span></li>`;
      })
      .join("");

    const q = $("q").value.trim().toLowerCase();
    const model = $("f-model").value;
    const cat = $("f-cat").value;
    const sev = $("f-sev").value;
    const rec = $("f-rec").value;
    const tri = $("f-triage").value;
    const kind = $("f-kind").value;
    const lang = $("f-lang").value;

    const filtered = inTime.filter((c) => {
      if ((c.polarity || "revisar") !== state.polarity) return false;
      if (model && !(c.models || []).includes(model)) return false;
      if (cat && c.category_label !== cat) return false;
      if (state.polarity === "mala" && sev && c.severity !== sev) return false;
      if (kind && !(c.source_kinds || []).includes(kind)) return false;
      if (lang && !(c.languages || []).includes(lang)) return false;
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

    $("list-title").textContent = POL_TITLE[state.polarity];
    const rangeTxt = RANGE_LABEL[state.range] || "mes";
    $("list-count").textContent = `${filtered.length} casos · filtro ${rangeTxt} · ${inTime.length} grupos en el período`;
    $("empty").classList.toggle("hidden", filtered.length > 0);
    $("empty").textContent =
      "No hay casos en esta vista con los filtros actuales. Probá otro período, otra pestaña (Buenas / Revisar) o limpiá la búsqueda.";

    $("clusters").innerHTML = filtered
      .map((c) => {
        const t = triage[c.id] || {};
        const quotes = (c.quotes || [])
          .map((qt) => {
            const meta = [
              qt.source,
              qt.created_at ? fmtShort(qt.created_at, zone) : "",
              qt.model,
              qt.language,
            ]
              .filter(Boolean)
              .join(" · ");
            return `<blockquote class="quote"><a href="${escapeHtml(qt.url || "#")}" target="_blank" rel="noopener">“${escapeHtml(qt.text)}”</a>
               <footer>${escapeHtml(meta)}${qt.title ? " · " + escapeHtml(qt.title) : ""}</footer></blockquote>`;
          })
          .join("");
        const more = (c.reports || [])
          .map((r) => {
            const bits = [
              r.source,
              r.created_at ? fmtShort(r.created_at, zone) : "",
              (r.models || [])[0],
              r.language_label || r.language,
            ]
              .filter(Boolean)
              .join(" · ");
            return `<a href="${escapeHtml(r.url || "#")}" target="_blank" rel="noopener">${escapeHtml(r.title || r.url || "fuente")}<small> · ${escapeHtml(bits)}</small></a>`;
          })
          .join("");
        const pol = c.polarity || "revisar";
        const cardClass = pol === "mala" ? c.severity || "baja" : pol;
        const polBadge =
          pol === "buena"
            ? `<span class="badge pol-buena">Buena noticia</span>`
            : pol === "revisar"
              ? `<span class="badge pol-revisar">Revisar</span>`
              : `<span class="badge sev-${escapeHtml(c.severity || "baja")}">Gravedad ${SEV_ES[c.severity] || c.severity || ""}</span>`;
        const langBadges = (c.language_labels || c.languages || [])
          .map((lb) => `<span class="badge">${escapeHtml(lb)}</span>`)
          .join("");
        const kindBadges = (c.source_kinds || [])
          .map((k) => `<span class="badge">${escapeHtml(KIND_ES[k] || k)}</span>`)
          .join("");
        return `<article class="card ${escapeHtml(cardClass)}" data-id="${escapeHtml(c.id)}">
          <h3>${escapeHtml(c.title)}</h3>
          <div class="badges">
            ${polBadge}
            <span class="badge">${c.count} reporte${c.count === 1 ? "" : "s"}</span>
            <span class="badge">${c.recurring ? "Recurrente" : "Nuevo"}</span>
            ${(c.models || []).map((m) => `<span class="badge">${escapeHtml(m)}</span>`).join("")}
            <span class="badge">${escapeHtml(c.category_label || "")}</span>
            ${langBadges}
            ${kindBadges}
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

  function applyData(data) {
    cached = data;
    render(data);
  }

  function loadJson() {
    return fetch("data/latest.json", { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
  }

  function boot() {
    const seed = window.FITBIT_SEED;
    const usable = seed && !seed.__SEED__ && (seed.clusters || seed.reports);
    if (usable) applyData(seed);
    loadJson()
      .then((data) => applyData(data))
      .catch((err) => {
        if (cached) return;
        $("run-stamp").textContent = "No se pudo cargar data/latest.json";
        $("empty").classList.remove("hidden");
        $("empty").textContent =
          "El tablero no encontró datos. Ejecutá python3 run.py o usá Ejecutar ahora. (" +
          err.message +
          ")";
      });
  }

  function loadActionsStatus() {
    const repo = document.body.dataset.repo;
    const wf = document.body.dataset.workflow;
    const el = $("actions-status");
    if (!repo || !el) return;
    const url = `https://api.github.com/repos/${repo}/actions/workflows/${wf}/runs?per_page=1`;
    fetch(url, { headers: { Accept: "application/vnd.github+json" } })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data) => {
        const run = (data.workflow_runs || [])[0];
        if (!run) {
          el.textContent = "Aún no hay corridas de Actions en el historial público.";
          return;
        }
        const when = fmtStamp(run.updated_at || run.created_at, "America/Buenos_Aires");
        const st = run.status === "completed" ? run.conclusion || "completed" : run.status;
        const label =
          st === "success"
            ? "éxito"
            : st === "in_progress" || st === "queued"
              ? "en curso"
              : st;
        el.innerHTML = `Actions: <a href="${escapeHtml(run.html_url)}" target="_blank" rel="noopener">${escapeHtml(label)}</a> · ${escapeHtml(when)}`;
      })
      .catch(() => {
        el.textContent = "No se pudo leer el estado de Actions (repo público, sin token). Usá Ejecutar ahora.";
      });
  }

  function bind() {
    ["q", "f-model", "f-cat", "f-sev", "f-rec", "f-triage", "f-kind", "f-lang"].forEach((id) => {
      $(id).addEventListener("input", () => cached && render(cached));
      $(id).addEventListener("change", () => cached && render(cached));
    });
    document.querySelectorAll(".polarity-tabs .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.polarity = btn.dataset.polarity;
        document.querySelectorAll(".polarity-tabs .tab").forEach((b) => b.classList.toggle("on", b === btn));
        if (cached) render(cached);
      });
    });
    $("f-range").addEventListener("click", (ev) => {
      const btn = ev.target.closest("button[data-range]");
      if (!btn) return;
      state.range = btn.dataset.range === "all" ? "all" : Number(btn.dataset.range);
      [...$("f-range").querySelectorAll("button")].forEach((b) => b.classList.toggle("on", b === btn));
      if (cached) render(cached);
    });
    $("kpis").addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-kpi]");
      if (!btn) return;
      const key = btn.dataset.kpi;
      if (key === "alta") {
        state.polarity = "mala";
        $("f-sev").value = "alta";
      } else if (key === "mala" || key === "buena" || key === "revisar") {
        state.polarity = key;
      }
      document.querySelectorAll(".polarity-tabs .tab").forEach((b) => {
        b.classList.toggle("on", b.dataset.polarity === state.polarity);
      });
      if (cached) render(cached);
    });
    $("btn-refresh").addEventListener("click", () => {
      $("btn-refresh").textContent = "Actualizando…";
      loadJson()
        .then((data) => {
          applyData(data);
          loadActionsStatus();
        })
        .catch(() => {})
        .finally(() => {
          $("btn-refresh").textContent = "Actualizar datos";
        });
    });
    $("btn-run").addEventListener("click", () => {
      $("run-help").textContent =
        "Se abrió GitHub Actions. Tocá Run workflow (arriba a la derecha) y confirmá. Cuando el job termine y Pages despliegue, volvé y usá Actualizar datos.";
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
  boot();
  loadActionsStatus();
})();
