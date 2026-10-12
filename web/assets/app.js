(() => {
  const $ = (id) => document.getElementById(id);
  const TRIAGE_KEY = "fitbit-scraper-triage-v1";
  const PAGE_SIZE = 12;
  const CHART_TOP_N = 8;
  const OPS_CHIP_MAX = 5;
  const MODEL_BAR_MAX = 10;
  const SEV_ES = { alta: "Alta", media: "Media", baja: "Baja" };
  const KIND_ES = {
    reddit: "Reddit",
    youtube: "YouTube",
    tiktok: "TikTok",
    instagram: "Instagram",
    web: "Web / foros",
    news: "Noticias",
    itunes: "App Store",
    playstore: "Play Store",
    hackernews: "Hacker News",
    x: "X",
    support: "Soporte",
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
    90: "90 días",
    365: "año",
    all: "todo",
  };

  const state = {
    polarity: "mala",
    range: 30,
    sev: "",
    chartBy: "categoria",
    model: "",
    q: "",
    cat: "",
    kind: "",
    lang: "",
    rec: "",
    triage: "",
  };

  const Ops = window.FitbitOps || {};
  let lastFiltered = [];
  let visibleCount = PAGE_SIZE;
  let loaded = false;
  let renderZone = "America/Buenos_Aires";

  function clusterPolarity(c) {
    const p = c.polarity || "revisar";
    if (p === "mala" && typeof c.confidence === "number" && c.confidence < 0.25) {
      return "revisar";
    }
    return p;
  }

  function confBadge(c) {
    if (typeof c.confidence !== "number") return "";
    return `<span class="badge conf">Confianza ${Math.round(c.confidence * 100)}%</span>`;
  }

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

  function dateObj(iso) {
    if (!iso) return null;
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    const y = d.getUTCFullYear();
    if (y < 2015 || y > 2030) return null;
    if (d.getTime() > Date.now() + 86400000) return null;
    return d;
  }

  function fmtStamp(iso, zone) {
    const d = dateObj(iso);
    if (!d) return iso ? "fecha n/d" : "sin datos";
    return new Intl.DateTimeFormat("es-AR", {
      timeZone: zone || "America/Buenos_Aires",
      dateStyle: "full",
      timeStyle: "short",
    }).format(d);
  }

  function fmtShort(iso, zone) {
    const d = dateObj(iso);
    if (!d) return "";
    return new Intl.DateTimeFormat("es-AR", {
      timeZone: zone || "America/Buenos_Aires",
      dateStyle: "medium",
    }).format(d);
  }

  function pubDate(iso, zone) {
    const s = fmtShort(iso, zone);
    return s ? `Publicado: ${s}` : "Fecha: n/d";
  }

  function impactLabel(obj) {
    const label = obj && (obj.engagement_label || (obj.engagement && obj.engagement.label));
    return label ? `Impacto: ${label}` : "";
  }

  function dayKey(iso, zone) {
    const d = dateObj(iso);
    if (!d) return "sin fecha";
    return new Intl.DateTimeFormat("es-AR", {
      timeZone: zone || "America/Buenos_Aires",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
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
    if (Ops.inRange) return Ops.inRange(iso, rangeDays, Date.now());
    if (!iso) return false;
    const t = Date.parse(iso);
    if (Number.isNaN(t)) return false;
    if (t > Date.now() + 86400000) return false;
    const y = new Date(t).getUTCFullYear();
    if (y < 2015 || y > 2030) return false;
    if (rangeDays == null) return true;
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

  function metaBits(parts) {
    return parts.filter(Boolean).join(" · ");
  }

  function cardHtml(c, triage, zone) {
    const t = triage[c.id] || {};
    const quotes = c.quotes || [];
    const first = quotes[0];
    const restQuotes = quotes.slice(1);
    const quoteBlock = (qt, extraClass) => {
      const meta = metaBits([
        pubDate(qt.created_at, zone),
        impactLabel(qt),
        qt.source,
        qt.model,
        qt.language,
      ]);
      return `<blockquote class="quote ${extraClass || ""}"><a href="${escapeHtml(qt.url || "#")}" target="_blank" rel="noopener">“${escapeHtml(qt.text)}”</a>
         <footer>${escapeHtml(meta)}${qt.title ? " · " + escapeHtml(qt.title) : ""}</footer></blockquote>`;
    };
    const more = (c.reports || [])
      .map((r) => {
        const bits = metaBits([
          pubDate(r.created_at || r.published_at, zone),
          impactLabel(r),
          r.source,
          (r.models || [])[0],
          r.language_label || r.language,
        ]);
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
    const headMeta = metaBits([
      pubDate(c.last_report_at, zone),
      impactLabel(c),
      `${c.count} reporte${c.count === 1 ? "" : "s"}`,
    ]);
    const extraN = restQuotes.length + (c.reports || []).length;
    return `<article class="card ${escapeHtml(cardClass)}" data-id="${escapeHtml(c.id)}">
      <h3>${escapeHtml(c.title)}</h3>
      <p class="case-meta">${escapeHtml(headMeta)}</p>
      <div class="badges">
        ${polBadge}
        ${confBadge(c)}
        <span class="badge">${c.count} reporte${c.count === 1 ? "" : "s"}</span>
        <span class="badge">${c.recurring ? "Recurrente" : "Nuevo"}</span>
        ${(c.models || []).map((m) => `<span class="badge">${escapeHtml(m)}</span>`).join("")}
        <span class="badge">${escapeHtml(c.category_label || "")}</span>
        ${langBadges}
        ${kindBadges}
      </div>
      ${first ? quoteBlock(first, "quote-preview") : ""}
      <details class="case-more">
        <summary>${extraN ? `Ver detalle · ${extraN} enlace${extraN === 1 ? "" : "s"}` : "Veredicto y enlaces"}</summary>
        ${restQuotes.map((qt) => quoteBlock(qt)).join("")}
        <details class="more" open><summary>Enlaces a la fuente (${(c.reports || []).length})</summary>${more}</details>
        <div class="triage">
          <button type="button" data-status="real" class="${t.status === "real" ? "on" : ""}">Parece real</button>
          <button type="button" data-status="check" class="${t.status === "check" ? "on" : ""}">Hay que verificar</button>
          <button type="button" data-status="discard" class="${t.status === "discard" ? "on" : ""}">Descartar</button>
          <input data-note placeholder="Nota privada en este navegador" value="${escapeHtml(t.note || "")}">
        </div>
      </details>
    </article>`;
  }

  function renderClusterPage() {
    const triage = loadTriage();
    const slice = lastFiltered.slice(0, visibleCount);
    $("clusters").innerHTML = slice.map((c) => cardHtml(c, triage, renderZone)).join("");
    const more = $("btn-more");
    if (more) {
      const rest = lastFiltered.length - slice.length;
      more.hidden = rest <= 0;
      more.textContent = rest > 0 ? `Cargar más (${rest} restantes)` : "Cargar más";
    }
  }

  function render(data) {
    visibleCount = PAGE_SIZE;
    const triage = loadTriage();
    const summary = data.summary || {};
    const clusters = data.clusters || [];
    const zone = data.timezone || "America/Buenos_Aires";
    renderZone = zone;
    const rangeDays = state.range === "all" ? null : Number(state.range);

    $("run-stamp").dateTime = data.generated_at || "";
    $("run-stamp").textContent = fmtStamp(data.generated_at, zone);
    $("run-zone").textContent = data.scrape_window_days
      ? `${zone} · corrida ${data.run_id || "—"} · ventana scrape ${data.scrape_window_days} días`
      : `${zone} · corrida ${data.run_id || "—"}`;

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
      const p = clusterPolarity(c);
      counts[p] = (counts[p] || 0) + (c.count || 0);
      if (p === "mala" && c.severity === "alta") alta.n += c.count || 0;
    }
    const kpis = [
      [counts.mala, "Malas noticias", "mala", "Defectos con lenguaje claro en el título (no sincroniza, outage, broken…). Confianza baja sin patrón de defecto va a Revisar."],
      [counts.buena, "Buenas noticias", "buena", "Elogios, parches y arreglos en la misma ventana."],
      [counts.revisar, "Para revisar", "revisar", "Ambiguos, baja confianza o sin cue de producto. No se les asigna gravedad alta."],
      [alta.n, "Gravedad alta (malas)", "alta", "Solo malas de alta confianza con defecto abierto en el título (brick, no enciende, recall)."],
    ];
    $("kpis").innerHTML = kpis
      .map(
        ([n, label, key, tip]) =>
          `<button type="button" class="kpi ${key} ${state.polarity === key || (key === "alta" && state.sev === "alta") ? "on" : ""}" data-kpi="${key}" title="${escapeHtml(tip)}">
            <b>${n}</b><span>${label}</span></button>`
      )
      .join("") +
      `<p class="kpi-defs">Los números respetan el filtro de tiempo. Mes = últimos 30 días de <em>fecha del ítem</em>. Casos negativos ocultan solo malas con confianza &lt; 25% y sin defecto en el título. Gravedad alta exige brick/recall/no enciende en el título.</p>`;

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
    const applySel = (id, key) => {
      const el = $(id);
      if (!el) return;
      if ([...el.options].some((o) => o.value === state[key])) el.value = state[key];
      else state[key] = el.value || "";
    };
    applySel("f-model", "model");
    applySel("f-cat", "cat");
    applySel("f-kind", "kind");
    applySel("f-lang", "lang");
    if ($("q") && document.activeElement !== $("q")) $("q").value = state.q || "";
    if ($("f-rec")) $("f-rec").value = state.rec || "";
    if ($("f-triage")) $("f-triage").value = state.triage || "";
    if ($("f-chart")) $("f-chart").value = state.chartBy || "categoria";

    const modelEntries = Object.entries(summary.by_model || {}).sort((a, b) => b[1] - a[1]);
    const topModels = modelEntries.slice(0, MODEL_BAR_MAX);
    const restModels = modelEntries.slice(MODEL_BAR_MAX);
    const maxModel = Math.max(1, ...topModels.map(([, n]) => n), 1);
    let barsHtml = topModels
      .map(
        ([name, n]) =>
          `<li><div class="row"><span>${escapeHtml(name)}</span><span>${n}</span></div>
           <div class="bar"><i style="width:${Math.round((n / maxModel) * 100)}%"></i></div></li>`
      )
      .join("");
    if (restModels.length) {
      const otherN = restModels.reduce((s, [, n]) => s + n, 0);
      barsHtml += `<li><div class="row"><span>Otros (${restModels.length})</span><span>${otherN}</span></div>
           <div class="bar"><i style="width:${Math.round((otherN / maxModel) * 100)}%"></i></div></li>`;
    }
    $("model-bars").innerHTML = barsHtml;

    const src = data.sources || [];
    const nOk = src.filter((s) => s.ok).length;
    const nLim = src.filter((s) => {
      const err = String(s.error || "");
      return !s.ok && (/429|límite de peticiones|limitado|omitida:/i.test(err) || s.state === "skip");
    }).length;
    const nErr = src.filter((s) => !s.ok && s.state === "error").length;
    const latencies = src.map((s) => s.latency_ms).filter((n) => typeof n === "number");
    const p50 = latencies.length
      ? latencies.slice().sort((a, b) => a - b)[Math.floor(latencies.length / 2)]
      : null;
    const ops = $("ops-strip");
    const kindHits = {};
    for (const s of src) {
      const k = s.kind || "web";
      kindHits[k] = (kindHits[k] || 0) + (Number(s.kept) || 0);
    }
    const hitList = [
      ...Object.keys(KIND_ES)
        .filter((k) => (kindHits[k] || 0) > 0)
        .map((k) => [KIND_ES[k], kindHits[k]]),
      ...Object.keys(kindHits)
        .filter((k) => !KIND_ES[k] && kindHits[k] > 0)
        .map((k) => [k, kindHits[k]]),
    ];
    const chip = ([label, n]) =>
      `<span class="ops-chip hits" title="Ítems conservados de ${escapeHtml(label)}">${escapeHtml(label)} ${n}</span>`;
    const headChips = hitList.slice(0, OPS_CHIP_MAX).map(chip).join("");
    const tailChips = hitList.slice(OPS_CHIP_MAX).map(chip).join("");
    const extraHits = tailChips
      ? `<details class="ops-extra"><summary>+${hitList.length - OPS_CHIP_MAX} fuentes</summary>${tailChips}</details>`
      : "";
    if (ops) {
      ops.innerHTML = `
        <span class="ops-chip ok"><i class="ops-dot"></i>${nOk} ok</span>
        <span class="ops-chip skip"><i class="ops-dot"></i>${nLim} limitado</span>
        <span class="ops-chip bad"><i class="ops-dot"></i>${nErr} error</span>
        ${headChips}${extraHits}
        <span>ventana scrape ${data.scrape_window_days || "—"} d</span>
        <span>${escapeHtml(zone)}</span>
        <span>latencia mediana ${p50 == null ? "n/d" : p50 + " ms"}</span>`;
    }
    const sumEl = $("source-summary");
    if (sumEl) {
      sumEl.textContent = `${nOk} ok · ${nLim} limitada${nLim === 1 ? "" : "s"} · ${nErr} error${nErr === 1 ? "" : "es"}`;
    }
    $("source-list").innerHTML = src
      .map((s) => {
        const err = String(s.error || "");
        const limited = /429|límite de peticiones|limitado|omitida:/i.test(err);
        let st = "error";
        let cls = "bad";
        if (s.ok) {
          st = "ok";
          cls = "ok";
        } else if (limited) {
          st = "limitado";
          cls = "skip";
        } else if (s.state === "skip") {
          st = "omitida";
          cls = "skip";
        }
        const ms = typeof s.latency_ms === "number" ? ` · ${s.latency_ms} ms` : "";
        const detail = (s.ok ? `${s.kept}/${s.fetched}` : err || st) + ms;
        const kind = KIND_ES[s.kind] ? ` · ${KIND_ES[s.kind]}` : "";
        return `<li><span><span class="pill ${cls}">${escapeHtml(st)}</span>${escapeHtml((s.label || s.id) + kind)}</span><span class="${cls}">${escapeHtml(String(detail))}</span></li>`;
      })
      .join("");

    const q = ($("q") ? $("q").value : state.q || "").trim().toLowerCase();
    state.q = $("q") ? $("q").value : state.q;
    const model = $("f-model") ? $("f-model").value : state.model;
    const cat = $("f-cat") ? $("f-cat").value : state.cat;
    const sev = state.sev;
    const rec = $("f-rec") ? $("f-rec").value : state.rec;
    const tri = $("f-triage") ? $("f-triage").value : state.triage;
    const kind = $("f-kind") ? $("f-kind").value : state.kind;
    const lang = $("f-lang") ? $("f-lang").value : state.lang;
    state.model = model;
    state.cat = cat;
    state.kind = kind;
    state.lang = lang;
    state.rec = rec;
    state.triage = tri;

    const filtered = inTime.filter((c) => {
      const pol = clusterPolarity(c);
      if (pol !== state.polarity) return false;
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

    lastFiltered = filtered;
    $("list-title").textContent = POL_TITLE[state.polarity];
    const rangeTxt = RANGE_LABEL[state.range] || "mes";
    const showing = Math.min(visibleCount, filtered.length);
    $("list-count").textContent = filtered.length
      ? `${filtered.length} casos · mostrando ${showing} · ${rangeTxt} · ${inTime.length} grupos en el período · ventana scrape ${data.scrape_window_days || "—"} d`
      : `0 casos · ${rangeTxt} · ${inTime.length} grupos en el período · ventana scrape ${data.scrape_window_days || "—"} d`;
    const empty = $("empty");
    if (empty) {
      empty.hidden = !loaded || filtered.length > 0;
      if (loaded && !filtered.length) {
        empty.textContent = inTime.length
          ? `No hay ${POL_TITLE[state.polarity].toLowerCase()} con estos filtros en ${rangeTxt}. Probá otro período o limpiá la búsqueda.`
          : `No hay casos fechados en ${rangeTxt}. La corrida guarda ${data.scrape_window_days || 90} días; el filtro Mes no incluye recalls viejos.`;
      }
    }
    $("clusters").setAttribute("aria-busy", loaded ? "false" : "true");
    renderClusterPage();
    drawSevChart(filtered, zone);
    syncUrl();
  }

  let cached = null;

  function applyUrl() {
    if (!Ops.parseState) return;
    const parsed = Ops.parseState(location.search || location.hash || "");
    Object.assign(state, parsed);
  }

  function syncUrl() {
    if (!Ops.serializeState || !loaded) return;
    const qs = Ops.serializeState(state);
    const next = location.pathname + (qs ? "?" + qs : "");
    if (next !== location.pathname + location.search) {
      history.replaceState(null, "", next);
    }
    document.querySelectorAll(".polarity-tabs .tab").forEach((b) => {
      const on = b.dataset.polarity === state.polarity;
      b.classList.toggle("on", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    [...$("f-range").querySelectorAll("button")].forEach((b) => {
      const on = String(b.dataset.range) === String(state.range);
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    setSev(state.sev);
  }

  function exportCsv() {
    const csv = Ops.clustersToCsv ? Ops.clustersToCsv(lastFiltered) : "";
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "fitbit-casos.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function copyView() {
    const url = `${location.origin}${location.pathname}?${Ops.serializeState ? Ops.serializeState(state) : ""}`;
    const done = () => {
      const btn = $("btn-copy-view");
      if (!btn) return;
      const prev = btn.textContent;
      btn.textContent = "Vista copiada";
      setTimeout(() => {
        btn.textContent = prev;
      }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(done).catch(done);
    } else {
      done();
    }
  }

  function applyData(data) {
    cached = data;
    loaded = true;
    document.body.classList.remove("is-loading");
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
    applyUrl();
    const seed = window.FITBIT_SEED;
    const usable = seed && !seed.__SEED__ && (seed.clusters || seed.reports);
    if (usable) applyData(seed);
    loadJson()
      .then((data) => applyData(data))
      .catch((err) => {
        if (cached) return;
        document.body.classList.remove("is-loading");
        loaded = true;
        $("run-stamp").textContent = "No se pudo cargar data/latest.json";
        const empty = $("empty");
        empty.hidden = false;
        empty.textContent =
          "El tablero no encontró datos. Ejecutá python3 run.py o usá Ejecutar ahora. (" +
          err.message +
          ")";
        $("clusters").innerHTML = "";
        $("clusters").setAttribute("aria-busy", "false");
        const more = $("btn-more");
        if (more) more.hidden = true;
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

  function setSev(sev) {
    state.sev = sev || "";
    [...$("f-sev").querySelectorAll("button")].forEach((b) => {
      const on = (b.dataset.sev || "") === state.sev;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  function chartBuckets(filtered, zone) {
    const by = state.chartBy || "categoria";
    const map = new Map();
    for (const c of filtered) {
      if ((c.polarity || "revisar") !== "mala") continue;
      const reports = c.reports && c.reports.length ? c.reports : [c];
      for (const r of reports) {
        const sev = r.severity || c.severity || "baja";
        if (!["alta", "media", "baja"].includes(sev)) continue;
        let key;
        if (by === "modelo") {
          key = (r.models && r.models[0]) || (c.models || [])[0] || "Sin modelo";
        } else if (by === "fuente") {
          const k = r.source_kind || (c.source_kinds || [])[0] || "web";
          key = KIND_ES[k] || k;
        } else if (by === "tiempo") {
          key = dayKey(r.created_at || r.published_at || c.last_report_at, zone);
        } else {
          key = c.category_label || "Otra";
        }
        if (!map.has(key)) map.set(key, { alta: 0, media: 0, baja: 0 });
        map.get(key)[sev] += 1;
      }
    }
    const rows = [...map.entries()]
      .map(([label, sevs]) => ({ label, ...sevs, total: sevs.alta + sevs.media + sevs.baja }))
      .sort((a, b) => (state.chartBy === "tiempo" ? a.label.localeCompare(b.label) : b.total - a.total));
    if (state.chartBy === "tiempo") {
      return rows.length > CHART_TOP_N ? rows.slice(-CHART_TOP_N) : rows;
    }
    if (rows.length <= CHART_TOP_N) return rows;
    const head = rows.slice(0, CHART_TOP_N);
    const tail = rows.slice(CHART_TOP_N);
    const otros = tail.reduce(
      (acc, r) => {
        acc.alta += r.alta;
        acc.media += r.media;
        acc.baja += r.baja;
        acc.total += r.total;
        return acc;
      },
      { label: "Otros", alta: 0, media: 0, baja: 0, total: 0 }
    );
    return [...head, otros];
  }

  function fillChartTable(rows, malaView) {
    const table = $("chart-table");
    if (!table) return;
    const body = table.querySelector("tbody");
    if (!body) return;
    if (!malaView) {
      body.innerHTML = `<tr><td colspan="5">La gravedad no aplica a buenas noticias ni a Revisar.</td></tr>`;
      return;
    }
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="5">Sin casos negativos en esta vista.</td></tr>`;
      return;
    }
    body.innerHTML = rows
      .map(
        (r) =>
          `<tr><th scope="row">${escapeHtml(r.label)}</th><td>${r.alta}</td><td>${r.media}</td><td>${r.baja}</td><td>${r.total}</td></tr>`
      )
      .join("");
  }

  function wrapAxisLabel(text, max = 12) {
    const s = String(text || "").trim();
    if (s.length <= max) return [s];
    const slash = s.indexOf("/");
    if (slash > 0 && slash <= max) {
      return [s.slice(0, slash).trim(), s.slice(slash + 1).trim()].filter(Boolean);
    }
    const cut = s.lastIndexOf(" ", max);
    if (cut >= 4) {
      let rest = s.slice(cut).trim();
      if (rest.length > max) rest = rest.slice(0, max - 1) + "…";
      return [s.slice(0, cut).trim(), rest];
    }
    return [s.slice(0, max - 1) + "…"];
  }

  function axisInk() {
    try {
      return window.matchMedia("(prefers-color-scheme: light)").matches ? "#4a5560" : "#c6bfb3";
    } catch {
      return "#c6bfb3";
    }
  }

  function gridInk() {
    try {
      return window.matchMedia("(prefers-color-scheme: light)").matches
        ? "rgba(28,35,41,0.12)"
        : "rgba(236,231,220,0.12)";
    } catch {
      return "rgba(236,231,220,0.12)";
    }
  }

  function drawSevChart(filtered, zone) {
    const svg = $("sev-chart");
    const empty = $("chart-empty");
    const sub = $("chart-sub");
    if (!svg) return;
    const malaView = state.polarity === "mala";
    const rows = malaView ? chartBuckets(filtered, zone) : [];
    const labels = { categoria: "categoría", modelo: "modelo", fuente: "fuente", tiempo: "día" };
    const dim = labels[state.chartBy] || "categoría";
    sub.textContent = malaView
      ? state.chartBy === "tiempo"
        ? `Barras apiladas Alta / Media / Baja por ${dim}. Últimos ${CHART_TOP_N} días con casos.`
        : `Barras apiladas Alta / Media / Baja por ${dim}. Top ${CHART_TOP_N} + Otros. Respeta tiempo, modelo, fuente e idioma.`
      : "La gravedad no se aplica a buenas noticias ni a Revisar. Abrí Casos negativos para ver el gráfico.";
    if (empty) empty.hidden = !!(malaView && rows.length > 0);
    fillChartTable(rows, malaView);
    if (!malaView || !rows.length) {
      svg.innerHTML = "";
      return;
    }
    const W = 760;
    const H = 320;
    const padL = 40;
    const padR = 12;
    const padT = 16;
    const padB = 52;
    const max = Math.max(1, ...rows.map((r) => r.total));
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const gap = rows.length > 8 ? 8 : 12;
    const barW = Math.max(18, innerW / rows.length - gap);
    const colors = { baja: "#7a9bb8", media: "#d4a017", alta: "#e07a6a" };
    const ticks = 4;
    const ink = axisInk();
    const gridStroke = gridInk();
    let grid = "";
    for (let i = 0; i <= ticks; i++) {
      const val = Math.round((max * (ticks - i)) / ticks);
      const y = padT + (innerH * i) / ticks;
      grid += `<line x1="${padL}" x2="${W - padR}" y1="${y}" y2="${y}" stroke="${gridStroke}"/>`;
      grid += `<text x="${padL - 8}" y="${y + 4}" text-anchor="end" fill="${ink}" font-size="11">${val}</text>`;
    }
    let bars = "";
    rows.forEach((row, i) => {
      const x = padL + i * (barW + gap) + gap / 2;
      let y = padT + innerH;
      for (const sev of ["baja", "media", "alta"]) {
        const h = (row[sev] / max) * innerH;
        if (h <= 0) continue;
        y -= h;
        bars += `<rect x="${x}" y="${y}" width="${barW}" height="${h}" fill="${colors[sev]}"><title>${escapeHtml(row.label)} · ${sev} ${row[sev]}</title></rect>`;
      }
      const cx = x + barW / 2;
      const ty = padT + innerH + 16;
      const lines = wrapAxisLabel(row.label, 11);
      bars += `<text text-anchor="middle" fill="${ink}" font-size="10">`;
      lines.forEach((line, li) => {
        bars += `<tspan x="${cx}" y="${ty + li * 12}">${escapeHtml(line)}</tspan>`;
      });
      bars += `</text>`;
    });
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("overflow", "hidden");
    svg.innerHTML = grid + bars;
  }

  function bind() {
    ["q", "f-model", "f-cat", "f-rec", "f-triage", "f-kind", "f-lang", "f-chart"].forEach((id) => {
      $(id).addEventListener("input", () => cached && render(cached));
      $(id).addEventListener("change", () => {
        if (id === "f-chart") state.chartBy = $("f-chart").value;
        if (cached) render(cached);
      });
    });
    document.querySelectorAll(".polarity-tabs .tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.polarity = btn.dataset.polarity;
        document.querySelectorAll(".polarity-tabs .tab").forEach((b) => b.classList.toggle("on", b === btn));
        if (cached) render(cached);
      });
    });
    const tablist = document.querySelector(".polarity-tabs");
    if (tablist) {
      tablist.addEventListener("keydown", (ev) => {
        const tabs = [...tablist.querySelectorAll("[role='tab']")];
        const i = tabs.indexOf(document.activeElement);
        if (i < 0) return;
        if (ev.key !== "ArrowRight" && ev.key !== "ArrowLeft" && ev.key !== "Home" && ev.key !== "End") {
          return;
        }
        ev.preventDefault();
        let next = i;
        if (ev.key === "ArrowRight") next = (i + 1) % tabs.length;
        if (ev.key === "ArrowLeft") next = (i - 1 + tabs.length) % tabs.length;
        if (ev.key === "Home") next = 0;
        if (ev.key === "End") next = tabs.length - 1;
        tabs[next].focus();
        tabs[next].click();
      });
    }
    $("f-range").addEventListener("click", (ev) => {
      const btn = ev.target.closest("button[data-range]");
      if (!btn) return;
      state.range = btn.dataset.range === "all" ? "all" : Number(btn.dataset.range);
      [...$("f-range").querySelectorAll("button")].forEach((b) => b.classList.toggle("on", b === btn));
      if (cached) render(cached);
    });
    $("f-sev").addEventListener("click", (ev) => {
      const btn = ev.target.closest("button[data-sev]");
      if (!btn) return;
      setSev(btn.dataset.sev);
      if (cached) render(cached);
    });
    $("kpis").addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-kpi]");
      if (!btn) return;
      const key = btn.dataset.kpi;
      if (key === "alta") {
        state.polarity = "mala";
        setSev("alta");
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
    if ($("btn-export")) $("btn-export").addEventListener("click", exportCsv);
    if ($("btn-copy-view")) $("btn-copy-view").addEventListener("click", copyView);
    if ($("btn-more")) {
      $("btn-more").addEventListener("click", () => {
        visibleCount += PAGE_SIZE;
        const showing = Math.min(visibleCount, lastFiltered.length);
        const rangeTxt = RANGE_LABEL[state.range] || "mes";
        if ($("list-count") && lastFiltered.length) {
          const scrape = cached && cached.scrape_window_days ? cached.scrape_window_days : "—";
          $("list-count").textContent = `${lastFiltered.length} casos · mostrando ${showing} · ${rangeTxt} · ventana scrape ${scrape} d`;
        }
        renderClusterPage();
      });
    }
    $("q").addEventListener("input", () => {
      state.q = $("q").value;
    });
    $("f-model").addEventListener("change", () => {
      state.model = $("f-model").value;
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
      const openId = card.querySelector("details.case-more") && card.querySelector("details.case-more").open;
      renderClusterPage();
      if (openId) {
        const next = $("clusters").querySelector(`[data-id="${CSS.escape(id)}"] details.case-more`);
        if (next) next.open = true;
      }
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

  function bindTop() {
    const btn = $("btn-top");
    if (!btn) return;
    const sync = () => {
      btn.hidden = window.scrollY < 420;
    };
    window.addEventListener("scroll", sync, { passive: true });
    btn.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    sync();
  }

  bind();
  bindTop();
  boot();
  loadActionsStatus();
})();
