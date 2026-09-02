(function () {
  var root = document.getElementById("awards-feed");
  if (!root) return;
  var limit = parseInt(root.getAttribute("data-limit") || "0", 10);
  var curatedOnly = root.getAttribute("data-curated") === "true";
  var initialSector = (function () {
    var q = new URLSearchParams(location.search).get("sector");
    if (q && /^(nuclear|magnets|chips|other)$/.test(q)) return q;
    return root.getAttribute("data-sector") || "all";
  })();

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function fmtMoney(n) {
    if (n == null || n === "") return "";
    n = Number(n);
    if (!isFinite(n)) return "";
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
    return { nuclear: "NUCLEAR", magnets: "MAGNETS / RARE EARTHS", chips: "SEMICONDUCTORS", other: "DEFENSE / OTHER" }[s] || String(s).toUpperCase();
  }

  function card(a) {
    var amount = a.amount_display || fmtMoney(a.amount);
    var ticker = a.ticker
      ? '<div class="text-xs mt-2"><span class="bronze-text">Ticker:</span> ' + esc(a.ticker) + "</div>"
      : '<div class="text-xs mt-2 text-[#8A8F82]">No verified public ticker</div>';
    var title = a.title ? '<div class="text-sm bronze-text mb-1">' + esc(a.title) + "</div>" : "";
    var status = a.status
      ? '<span class="badge-status badge-' + esc(a.status) + '">' + esc(a.status) + "</span>"
      : "";
    var el = document.createElement("article");
    el.className = "deco-card rounded-3xl p-6";
    el.setAttribute("data-sector", a.sector || "other");
    el.innerHTML =
      '<div class="flex justify-between items-start mb-3 gap-3">' +
        '<div class="text-xs text-[#8A8F82]">' + esc(sectorLabel(a.sector)) + " · " + esc(a.agency || "") + "</div>" +
        '<span class="px-2 py-1 badge-green text-xs rounded whitespace-nowrap">' + esc(fmtDate(a.date)) + "</span>" +
      "</div>" +
      title +
      '<h3 class="text-xl font-semibold leading-snug">' + esc(a.recipient_name || "") + "</h3>" +
      '<div class="flex flex-wrap items-center gap-2 mt-2 mb-2">' +
        '<div class="text-lg font-semibold amount-pos">' + esc(amount) + "</div>" +
        status +
      "</div>" +
      '<p class="text-sm text-[#8A8F82] mb-2">' + esc(a.description || "") + "</p>" +
      ticker +
      (a.source_url
        ? '<a href="' + esc(a.source_url) + '" target="_blank" rel="noopener" class="inline-block mt-3 text-xs bronze-link">Official source →</a>'
        : "");
    return el;
  }

  var DATA = null;
  var current = initialSector;

  function apply(sector) {
    current = sector || "all";
    var awards = ((DATA && DATA.awards) || []).slice();
    if (curatedOnly) awards = awards.filter(function (a) { return a.curated; });
    if (current !== "all") awards = awards.filter(function (a) { return a.sector === current; });
    awards.sort(function (a, b) {
      if (a.curated && !b.curated) return -1;
      if (!a.curated && b.curated) return 1;
      return (b.date || "").localeCompare(a.date || "");
    });
    var shown = limit ? awards.slice(0, limit) : awards;
    root.innerHTML = "";
    if (!shown.length) {
      root.innerHTML = '<p class="text-sm text-[#8A8F82] col-span-full">No awards in this filter. Try another sector or reload.</p>';
    } else {
      shown.forEach(function (a) { root.appendChild(card(a)); });
    }
    var meta = document.getElementById("awards-meta");
    if (meta && DATA) {
      var extra = limit && awards.length > shown.length
        ? " Showing " + shown.length + " of " + awards.length + "."
        : "";
      meta.textContent =
        shown.length + " items · snapshot " + (DATA.generated_at || "") +
        " · window " + ((DATA.window && DATA.window.start) || "") +
        " to " + ((DATA.window && DATA.window.end) || "") + "." + extra +
        " Status tags: FINAL / CONDITIONAL / LOI / UCA. Not investment advice.";
    }
    document.querySelectorAll("[data-filter-sector]").forEach(function (btn) {
      btn.classList.toggle("is-on", btn.getAttribute("data-filter-sector") === current);
    });
  }

  document.querySelectorAll("[data-filter-sector]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var s = btn.getAttribute("data-filter-sector");
      if (history.replaceState) {
        var url = new URL(location.href);
        if (s === "all") url.searchParams.delete("sector");
        else url.searchParams.set("sector", s);
        history.replaceState({}, "", url);
      }
      apply(s);
    });
  });

  fetch("data/awards.json")
    .then(function (r) {
      if (!r.ok) throw new Error("awards.json " + r.status);
      return r.json();
    })
    .then(function (data) {
      DATA = data;
      apply(current);
    })
    .catch(function () {
      root.innerHTML =
        '<p class="text-sm text-[#8A8F82] col-span-full">Could not load <code>data/awards.json</code>. Serve these files over HTTP (or any static host). Empty state — no invented awards.</p>';
      var meta = document.getElementById("awards-meta");
      if (meta) meta.textContent = "Awards feed failed to load.";
    });
})();
