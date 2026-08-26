/**
 * Shareable view state and CSV export. Loaded in the browser and in Node tests.
 * No secrets. Filter keys: p polarity, t days, s severity, m model, q search.
 */
(function (root) {
  "use strict";

  var CSV_COLUMNS = [
    "id",
    "polarity",
    "severity",
    "models",
    "category",
    "published_at",
    "source",
    "title",
    "url",
    "count",
    "language",
    "impact",
  ];

  function parseState(search) {
    var raw = String(search || "");
    if (raw.charAt(0) === "?" || raw.charAt(0) === "#") raw = raw.slice(1);
    var p = new URLSearchParams(raw);
    var tRaw = p.get("t");
    var range = 30;
    if (tRaw === "all") range = "all";
    else if (tRaw && Number(tRaw) > 0) range = Number(tRaw);
    var pol = p.get("p");
    var sev = p.get("s");
    var g = p.get("g");
    return {
      polarity: ["mala", "buena", "revisar"].indexOf(pol) >= 0 ? pol : "mala",
      range: range,
      sev: ["alta", "media", "baja"].indexOf(sev) >= 0 ? sev : "",
      model: p.get("m") || "",
      q: p.get("q") || "",
      cat: p.get("c") || "",
      kind: p.get("k") || "",
      lang: p.get("lang") || "",
      chartBy: ["categoria", "modelo", "fuente", "tiempo"].indexOf(g) >= 0 ? g : "categoria",
    };
  }

  function serializeState(state) {
    state = state || {};
    var p = new URLSearchParams();
    p.set("p", state.polarity || "mala");
    p.set("t", String(state.range == null ? "all" : state.range));
    if (state.sev) p.set("s", state.sev);
    if (state.model) p.set("m", state.model);
    if (state.q) p.set("q", state.q);
    if (state.cat) p.set("c", state.cat);
    if (state.kind) p.set("k", state.kind);
    if (state.lang) p.set("lang", state.lang);
    if (state.chartBy && state.chartBy !== "categoria") p.set("g", state.chartBy);
    return p.toString();
  }

  function csvEscape(v) {
    var s = v == null ? "" : String(v);
    if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  function clustersToCsv(clusters) {
    var lines = [CSV_COLUMNS.join(",")];
    (clusters || []).forEach(function (c) {
      var url = "";
      if (c.reports && c.reports[0] && c.reports[0].url) url = c.reports[0].url;
      var row = {
        id: c.id || "",
        polarity: c.polarity || "",
        severity: c.severity || "",
        models: (c.models || []).join("; "),
        category: c.category_label || c.category || "",
        published_at: c.last_report_at || "",
        source: (c.sources || []).join("; "),
        title: c.title || "",
        url: url,
        count: c.count == null ? "" : c.count,
        language: (c.language_labels || c.languages || []).join("; "),
        impact: c.engagement_label || "",
      };
      lines.push(
        CSV_COLUMNS.map(function (k) {
          return csvEscape(row[k]);
        }).join(",")
      );
    });
    return lines.join("\n");
  }

  function inRange(iso, rangeDays, nowMs) {
    nowMs = nowMs || Date.now();
    if (rangeDays == null) return !!iso && !Number.isNaN(Date.parse(iso));
    if (!iso) return false;
    var t = Date.parse(iso);
    if (Number.isNaN(t)) return false;
    return nowMs - t <= rangeDays * 86400000;
  }

  root.FitbitOps = {
    CSV_COLUMNS: CSV_COLUMNS,
    parseState: parseState,
    serializeState: serializeState,
    csvEscape: csvEscape,
    clustersToCsv: clustersToCsv,
    inRange: inRange,
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
