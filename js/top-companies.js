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
  function awardHref(a) {
    if (!a || !a.id) return "";
    if (String(a.id).indexOf("-20") !== -1 || /^(war|doe|chips|osc)-/.test(a.id)) return "award/" + encodeURIComponent(a.id) + ".html";
    return "award.html?id=" + encodeURIComponent(a.id);
  }
  var RETURNS = {};
  function returnFor(ticker, id) {
    return RETURNS[ticker + "|" + id] || null;
  }
  function returnHtml(ticker, awards) {
    var bits = [];
    (awards || []).forEach(function (a) {
      var rec = returnFor(ticker, a.id);
      if (!rec || rec.return_pct == null) return;
      var cls = rec.return_pct >= 0 ? "ret-pos" : "ret-neg";
      bits.push("If you bought " + esc(ticker) + " at the " + esc(rec.announce_date) + " close after " + esc(a.title || "this deal") + " was announced, the return to " + esc(rec.as_of_date) + ' would have been <span class="' + cls + '">' + rec.return_pct + "%</span>.");
    });
    if (!bits.length) return '<p class="text-xs text-[#8A8F82] mt-2">No reliable close for a return on these rows — we will not invent one.</p>';
    return '<div class="text-xs mt-3 space-y-2 return-block">' + bits.map(function (b) { return "<p>" + b + "</p>"; }).join("") + "</div>";
  }
  function row(item) {
    var sources = (item.awards || []).map(function (a) {
      var href = a.source_url || "";
      var perma = awardHref(a);
      var title = a.title || "Official source";
      var line = "";
      if (perma) line += '<a href="' + esc(perma) + '" class="bronze-link text-xs">' + esc(title) + " permalink</a> ";
      if (href) line += '<a href="' + esc(href) + '" target="_blank" rel="noopener" class="bronze-link text-xs">Official source →</a>';
      return line;
    }).filter(Boolean).join("<br>");
    var el = document.createElement("article");
    el.className = "deco-card rounded-3xl p-6";
    el.innerHTML =
      '<div class="flex justify-between items-start gap-3 mb-3">' +
        '<div class="flex items-start gap-3">' +
          '<div class="rank-num text-2xl">#' + esc(item.rank) + "</div>" +
          "<div>" +
            '<h3 class="text-xl font-semibold leading-snug"><a href="ticker/' + esc(item.ticker) + '.html">' + esc(item.company) + "</a></h3>" +
            '<div class="text-xs text-[#8A8F82] mt-1">' + esc(item.sector_label || "") +
              ' · <span class="bronze-text">Ticker:</span> <a class="bronze-link" href="ticker/' + esc(item.ticker) + '.html">' + esc(item.ticker) + "</a>" +
              ' · <button type="button" class="watch-btn text-xs px-3 py-1" data-watch-ticker="' + esc(item.ticker) + '">Watch ' + esc(item.ticker) + "</button></div>" +
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
      returnHtml(item.ticker, item.awards) +
      '<div class="text-xs text-[#8A8F82] mb-1 mt-3">Source: ' + esc(item.source || "") + "</div>" +
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
          '<div class="text-xs text-[#8A8F82] mt-1">' + esc(item.sector_label || "") + " · no verified ticker · no return</div>" +
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
  Promise.all([
    fetch("data/top20.json").then(function (r) { if (!r.ok) throw new Error("top20.json " + r.status); return r.json(); }),
    fetch("data/returns.json").then(function (r) { return r.ok ? r.json() : { returns: [] }; }).catch(function () { return { returns: [] }; })
  ]).then(function (pair) {
    var data = pair[0];
    (pair[1].returns || []).forEach(function (r) {
      if (r.award_id) RETURNS[r.ticker + "|" + r.award_id] = r;
    });
    if (heading && data.title) heading.textContent = data.title;
    if (method && data.ranking_method_plain) method.textContent = data.ranking_method_plain;
    var list = data.ranked || [];
    root.innerHTML = "";
    if (!list.length) {
      root.innerHTML = '<p class="text-sm text-[#8A8F82]">No verified public tickers in this window. Empty state — no invented names.</p>';
    } else {
      list.forEach(function (item) { root.appendChild(row(item)); });
      if (window.FedForgeWatch) window.FedForgeWatch.bind(root);
    }
    if (meta) {
      meta.textContent = list.length + " public companies with verified tickers · flagship window " +
        ((data.window && data.window.start) || "") + " to " + ((data.window && data.window.end) || "") +
        " · snapshot " + (data.generated_at || "") +
        ". We did not pad to 20.";
    }
    if (priv) {
      priv.innerHTML = "";
      (data.private_recipients || []).forEach(function (item) { priv.appendChild(privateCard(item)); });
    }
  }).catch(function () {
    root.innerHTML = '<p class="text-sm text-[#8A8F82]">Could not load data/top20.json. Serve over HTTP. Empty state — no invented companies.</p>';
  });
})();
