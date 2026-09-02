(function () {
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function fmtMoney(n) {
    if (n == null || n === "") return "";
    n = Number(n);
    if (!isFinite(n)) return "";
    if (n >= 1e9) return "$" + (n / 1e9).toFixed(2).replace(/\.00$/, "") + "B";
    if (n >= 1e6) return "$" + (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
    return "$" + Math.round(n).toLocaleString();
  }
  var id = new URLSearchParams(location.search).get("id");
  var root = document.getElementById("award-query-root");
  if (!root) return;
  if (!id) {
    root.innerHTML = '<p class="text-sm text-[#8A8F82]">Add <code>?id=</code> for a new-prime award (for example <a class="bronze-link" href="award.html?id=DEEE0011721">DEEE0011721</a>). Flagship deals have static pages under <code>award/</code>.</p>';
    return;
  }
  Promise.all([
    fetch("data/awards.json").then(function (r) { return r.json(); }),
    fetch("data/public-primes.json").then(function (r) { return r.json(); }).catch(function () { return { awards: [] }; }),
    fetch("data/returns.json").then(function (r) { return r.json(); }).catch(function () { return { returns: [] }; })
  ]).then(function (pack) {
    var all = (pack[0].awards || []).concat(pack[1].awards || []);
    var a = null;
    all.forEach(function (x) { if (String(x.id) === String(id)) a = x; });
    if (!a) {
      root.innerHTML = '<p class="text-sm text-[#8A8F82]">No prime with id ' + esc(id) + ". We will not invent one.</p>";
      return;
    }
    document.title = (a.title || a.recipient_name || id) + " · FedForge";
    var rec = null;
    (pack[2].returns || []).forEach(function (r) { if (r.award_id === a.id) rec = r; });
    var ret = "";
    if (!a.ticker) ret = "<p class=\"text-sm text-[#8A8F82]\">Private recipient — no announcement-to-now return.</p>";
    else if (!rec || rec.return_pct == null) ret = "<p class=\"text-sm text-[#8A8F82]\">If you bought " + esc(a.ticker) + " after this deal was announced, there is no reliable close for a return — we will not invent one.</p>";
    else {
      var cls = rec.return_pct >= 0 ? "ret-pos" : "ret-neg";
      ret = '<p class="return-block">If you bought ' + esc(a.ticker) + " at the " + esc(rec.announce_date) + " close after this deal was announced, the return to " + esc(rec.as_of_date) + ' would have been <span class="' + cls + '">' + rec.return_pct + "%</span>.</p>";
    }
    var obl = "";
    if (a.status === "UCA" || a.status === "UCA/mod") {
      obl = '<p class="text-sm"><span class="bronze-text">Obligated vs face:</span> ' + esc(fmtMoney(a.amount_obligated)) + " obligated / " + esc(fmtMoney(a.amount_face != null ? a.amount_face : a.amount)) + ' face. <a class="bronze-link" href="glossary.html#UCA">UCA</a></p>';
    }
    root.innerHTML =
      '<p class="text-sm bronze-text mb-2">New prime permalink</p>' +
      "<h1 class=\"text-4xl font-semibold mb-2\">" + esc(a.title || a.recipient_name) + "</h1>" +
      '<p class="text-[#8A8F82] mb-6">' + esc(a.recipient_name || "") + (a.ticker ? ' · <a class="bronze-link" href="ticker/' + esc(a.ticker) + '.html">' + esc(a.ticker) + "</a>" : " · no verified ticker") + " · " + esc(a.date || "") + "</p>" +
      '<div class="deco-card rounded-3xl p-6 md:p-8">' +
        '<div class="flex flex-wrap gap-2 mb-4"><span class="badge-status badge-FINAL">' + esc(a.status || "NEW PRIME") + "</span>" +
        '<span class="text-lg font-semibold amount-pos">' + esc(a.amount_display || fmtMoney(a.amount)) + "</span></div>" +
        obl +
        '<p class="text-sm text-[#8A8F82] mb-4">' + esc(a.description || "") + "</p>" + ret +
        (a.ticker ? '<p class="mt-4"><button type="button" class="watch-btn" data-watch-ticker="' + esc(a.ticker) + '">Watch ' + esc(a.ticker) + "</button></p>" : "") +
        (a.source_url ? '<p class="mt-4"><a class="bronze-link" href="' + esc(a.source_url) + '" target="_blank" rel="noopener">Official source →</a></p>' : "") +
      "</div>" +
      '<p class="text-xs text-[#8A8F82] mt-6">Close-to-close only. Ignores spreads, taxes, whether you could fill. Not a forecast. Past ≠ future. A UCA/LOI announcement is not cash in the company. Not investment advice.</p>';
    if (window.FedForgeWatch) window.FedForgeWatch.bind(root);
  }).catch(function () {
    root.innerHTML = '<p class="text-sm text-[#8A8F82]">Could not load award JSON. Serve over HTTP.</p>';
  });
})();
