(function () {
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function fmtMoney(n) {
    if (n == null || n === "") return "—";
    n = Number(n);
    if (!isFinite(n)) return "—";
    if (n >= 1e9) return "$" + (n / 1e9).toFixed(n >= 1e10 ? 1 : 2).replace(/\.00$/, "") + "B";
    if (n >= 1e6) return "$" + (n / 1e6).toFixed(n >= 1e8 ? 0 : 1).replace(/\.0$/, "") + "M";
    return "$" + Math.round(n).toLocaleString();
  }
  function awardHref(a, flagship) {
    if (flagship && a.id) return "award/" + encodeURIComponent(a.id) + ".html";
    if (a.id) return "award.html?id=" + encodeURIComponent(a.id);
    return "awards.html";
  }
  var root = document.getElementById("public-window");
  if (!root) return;
  var watchOnly = false;
  Promise.all([
    fetch("data/curated.json").then(function (r) { return r.json(); }),
    fetch("data/awards.json").then(function (r) { return r.json(); }).catch(function () { return { awards: [] }; }),
    fetch("data/public-primes.json").then(function (r) { return r.json(); }).catch(function () { return { awards: [] }; }),
    fetch("data/returns.json").then(function (r) { return r.json(); }).catch(function () { return { returns: [] }; })
  ]).then(function (pack) {
    var curated = pack[0], primes = pack[1], pub = pack[2], retFile = pack[3];
    var RET = {};
    (retFile.returns || []).forEach(function (r) { if (r.award_id) RET[r.ticker + "|" + r.award_id] = r; });
    var rows = [];
    (curated.awards || []).forEach(function (a) {
      if (!a.ticker) return;
      rows.push({ a: a, flagship: true, layer: "flagship" });
    });
    (primes.awards || []).forEach(function (a) {
      if (!a.ticker || a.ticker === "LEU") return;
      rows.push({ a: a, flagship: false, layer: "new prime" });
    });
    (pub.awards || []).forEach(function (a) {
      rows.push({ a: a, flagship: false, layer: "12-month public prime" });
    });
    rows.sort(function (x, y) { return (y.a.date || "").localeCompare(x.a.date || ""); });
    function render() {
      var shown = rows;
      if (watchOnly && window.FedForgeWatch) {
        var w = window.FedForgeWatch.list();
        shown = rows.filter(function (r) { return w.indexOf(r.a.ticker) !== -1; });
      }
      var html = '<div class="pub-scroll"><table class="pub-table"><thead><tr>' +
        "<th>Ticker</th><th>Deal</th><th>Status</th><th>Sourced $</th><th>Announcement-to-now</th></tr></thead><tbody>";
      shown.forEach(function (r) {
        var a = r.a;
        var rec = RET[a.ticker + "|" + a.id];
        var retCell = "—";
        if (rec && rec.return_pct != null) {
          var cls = rec.return_pct >= 0 ? "ret-pos" : "ret-neg";
          retCell = '<span class="' + cls + '">' + rec.return_pct + "%</span>";
        } else if (a.ticker) {
          retCell = '<span class="ret-na">no reliable close</span>';
        }
        var st = a.status_label || a.status || (r.layer === "new prime" ? "NEW PRIME" : "");
        html += "<tr data-ticker=\"" + esc(a.ticker) + "\">" +
          '<td><a href="ticker/' + esc(a.ticker) + '.html"><strong>' + esc(a.ticker) + "</strong></a></td>" +
          '<td><a href="' + esc(awardHref(a, r.flagship)) + '">' + esc(a.title || a.recipient_name) + "</a>" +
            '<div class="text-xs text-[#8A8F82]">' + esc(a.recipient_name || "") + " · " + esc(a.date || "") + " · " + esc(r.layer) + "</div></td>" +
          '<td><span class="badge-status badge-' + esc(String(a.status || "FINAL").split("/")[0]) + '">' + esc(st) + "</span></td>" +
          "<td class=\"amount-pos\">" + esc(a.amount_display || fmtMoney(a.amount)) + "</td>" +
          "<td>" + retCell + "</td></tr>";
      });
      if (!shown.length) html += '<tr><td colspan="5" class="text-[#8A8F82]">No watched public awards. Watch a ticker first.</td></tr>';
      html += "</tbody></table></div>";
      root.innerHTML = html;
    }
    render();
    var btn = document.getElementById("filter-watchlist");
    if (btn) {
      btn.addEventListener("click", function () {
        watchOnly = !watchOnly;
        btn.classList.toggle("is-on", watchOnly);
        btn.setAttribute("aria-pressed", watchOnly ? "true" : "false");
        render();
      });
    }
    document.addEventListener("fedforge-watchlist-change", render);
  }).catch(function () {
    root.innerHTML = '<p class="text-sm text-[#8A8F82]">Could not load public awards. Serve over HTTP. Empty state — no invented deals.</p>';
  });
})();
