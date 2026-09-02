(function () {
  var root = document.getElementById("awards-feed");
  if (!root) return;

  function fmtMoney(n) {
    if (n >= 1e9) return "$" + (n / 1e9).toFixed(n >= 1e10 ? 1 : 2).replace(/\.00$/, "") + "B";
    if (n >= 1e6) return "$" + (n / 1e6).toFixed(n >= 1e8 ? 0 : 1).replace(/\.0$/, "") + "M";
    if (n >= 1e3) return "$" + Math.round(n / 1e3).toLocaleString() + "K";
    return "$" + Math.round(n).toLocaleString();
  }
  function fmtDate(iso) {
    if (!iso) return "";
    var p = iso.split("-");
    var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return months[parseInt(p[1], 10) - 1] + " " + parseInt(p[2], 10) + ", " + p[0];
  }
  function sectorLabel(s) {
    return { nuclear: "NUCLEAR", magnets: "MAGNETS / RARE EARTHS", chips: "SEMICONDUCTORS", other: "OTHER" }[s] || s.toUpperCase();
  }

  function card(a) {
    var ticker = a.ticker
      ? '<div class="text-xs"><span class="bronze-text">Ticker:</span> ' + a.ticker + "</div>"
      : "";
    var el = document.createElement("div");
    el.className = "deco-card rounded-3xl p-6";
    el.innerHTML =
      '<div class="flex justify-between items-start mb-4 gap-3">' +
        '<div>' +
          '<div class="text-xs text-[#8A8F82]">' + sectorLabel(a.sector) + "</div>" +
          '<div class="text-xl font-semibold">' + (a.recipient_name || "") + "</div>" +
        "</div>" +
        '<span class="px-2 py-1 badge-green text-xs rounded whitespace-nowrap">' + fmtDate(a.date) + "</span>" +
      "</div>" +
      '<div class="text-lg font-semibold amount-pos mb-2">' + fmtMoney(a.amount) + "</div>" +
      '<p class="text-sm text-[#8A8F82] mb-4">' + (a.description || "") + "</p>" +
      ticker +
      (a.source_url
        ? '<a href="' + a.source_url + '" target="_blank" rel="noopener" class="inline-block mt-3 text-xs bronze-link">USAspending source →</a>'
        : "");
    return el;
  }

  function render(data) {
    var awards = (data && data.awards) || [];
    root.innerHTML = "";
    if (!awards.length) {
      root.innerHTML = '<p class="text-sm text-[#8A8F82]">No awards in this snapshot.</p>';
      return;
    }
    awards.forEach(function (a) { root.appendChild(card(a)); });
    var meta = document.getElementById("awards-meta");
    if (meta) {
      meta.textContent =
        awards.length + " prime awards · USAspending snapshot " + (data.generated_at || "") +
        " · window " + ((data.window && data.window.start) || "") + " to " + ((data.window && data.window.end) || "");
    }
  }

  fetch("data/awards.json")
    .then(function (r) { if (!r.ok) throw new Error("awards.json " + r.status); return r.json(); })
    .then(render)
    .catch(function () {
      root.innerHTML =
        '<p class="text-sm text-[#8A8F82]">Could not load <code>data/awards.json</code>. Open this site via a local or static host so the snapshot file is reachable.</p>';
    });
})();
