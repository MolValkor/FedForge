(function () {
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function statusClass(status) {
    var s = String(status || "").split("/")[0];
    return /^(FINAL|CONDITIONAL|LOI|UCA)$/.test(s) ? s : "";
  }
  function badges(mix) {
    return (mix || []).map(function (st) {
      var cls = statusClass(st);
      return '<span class="badge-status badge-' + esc(cls) + '">' + esc(st) + "</span>";
    }).join(" ");
  }
  function fmtScore(n) {
    n = Number(n);
    if (!isFinite(n)) return "";
    if (n >= 1e9) return (n / 1e9).toFixed(2).replace(/\.00$/, "") + "B pts";
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M pts";
    if (n >= 1e3) return Math.round(n / 1e3).toLocaleString() + "K pts";
    return Math.round(n).toLocaleString() + " pts";
  }

  function row(item) {
    var sources = (item.awards || []).map(function (a) {
      if (!a.source_url) return "";
      return '<a href="' + esc(a.source_url) + '" target="_blank" rel="noopener" class="bronze-link text-xs">' + esc(a.title || "Official source") + " →</a>";
    }).filter(Boolean).join("<br>");
    if (!sources && item.source_url) {
      sources = '<a href="' + esc(item.source_url) + '" target="_blank" rel="noopener" class="bronze-link text-xs">Official source →</a>';
    }
    var el = document.createElement("article");
    el.className = "deco-card rounded-3xl p-6";
    el.innerHTML =
      '<div class="flex justify-between items-start gap-3 mb-3">' +
        '<div class="flex items-start gap-3">' +
          '<div class="rank-num text-2xl">#' + esc(item.rank) + "</div>" +
          "<div>" +
            '<h3 class="text-xl font-semibold leading-snug">' + esc(item.company) + "</h3>" +
            '<div class="text-xs text-[#8A8F82] mt-1">' + esc(item.sector_label || "") +
              ' · <span class="bronze-text">Ticker:</span> ' + esc(item.ticker) + "</div>" +
          "</div>" +
        "</div>" +
        '<div class="text-right">' +
          '<div class="text-lg font-semibold amount-pos">' + esc(item.federal_dollars_display) + "</div>" +
          '<div class="text-xs text-[#8A8F82] mt-1">score ' + esc(fmtScore(item.rankingScore)) + "</div>" +
        "</div>" +
      "</div>" +
      '<div class="flex flex-wrap gap-2 mb-3">' + badges(item.status_mix) + "</div>" +
      '<p class="text-sm text-[#8A8F82] mb-2">' + esc(item.why) + "</p>" +
      '<p class="text-xs text-[#8A8F82] mb-3"><span class="bronze-text">Why this rank:</span> ' + esc(item.rankingScore_explanation) + "</p>" +
      '<div class="text-xs text-[#8A8F82] mb-1">Source: ' + esc(item.source || "") + "</div>" +
      "<div>" + sources + "</div>";
    return el;
  }

  function privateCard(item) {
    var el = document.createElement("article");
    el.className = "deco-card rounded-3xl p-6";
    el.innerHTML =
      '<div class="flex justify-between items-start gap-3 mb-2">' +
        "<div>" +
          '<h3 class="text-lg font-semibold">' + esc(item.company) + "</h3>" +
          '<div class="text-xs text-[#8A8F82] mt-1">' + esc(item.sector_label || "") + " · no verified ticker</div>" +
        "</div>" +
        '<div class="text-right text-sm amount-pos">' + esc(item.federal_dollars_display) + "</div>" +
      "</div>" +
      '<div class="flex flex-wrap gap-2 mb-3">' + badges(item.status_mix) + "</div>" +
      '<p class="text-sm text-[#8A8F82] mb-2">' + esc(item.why) + "</p>" +
      (item.source_url
        ? '<a href="' + esc(item.source_url) + '" target="_blank" rel="noopener" class="bronze-link text-xs">Official source →</a>'
        : "");
    return el;
  }

  var root = document.getElementById("ranked-feed");
  var priv = document.getElementById("private-feed");
  var method = document.getElementById("ranking-method");
  var heading = document.getElementById("page-heading");
  var meta = document.getElementById("ranked-meta");
  if (!root) return;

  fetch("data/top20.json")
    .then(function (r) { if (!r.ok) throw new Error("top20.json " + r.status); return r.json(); })
    .then(function (data) {
      if (heading && data.title) heading.textContent = data.title;
      if (method && data.ranking_method_plain) method.textContent = data.ranking_method_plain;
      var list = data.ranked || [];
      root.innerHTML = "";
      if (!list.length) {
        root.innerHTML = '<p class="text-sm text-[#8A8F82]">No verified public tickers in this window. Empty state — no invented names.</p>';
      } else {
        list.forEach(function (item) { root.appendChild(row(item)); });
      }
      if (meta) {
        meta.textContent = list.length + " public companies with verified tickers · window " +
          ((data.window && data.window.start) || "") + " to " + ((data.window && data.window.end) || "") +
          " · snapshot " + (data.generated_at || "") +
          ". We did not pad to 20.";
      }
      if (priv) {
        priv.innerHTML = "";
        (data.private_recipients || []).forEach(function (item) { priv.appendChild(privateCard(item)); });
      }
    })
    .catch(function () {
      root.innerHTML = '<p class="text-sm text-[#8A8F82]">Could not load data/top20.json. Serve over HTTP. Empty state — no invented companies.</p>';
    });
})();
