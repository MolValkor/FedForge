(function () {
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
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
    return { nuclear: "NUCLEAR", magnets: "MAGNETS / RARE EARTHS", chips: "SEMICONDUCTORS", other: "DEFENSE / OTHER" }[s] || String(s || "").toUpperCase();
  }
  function statusClass(status) {
    var s = String(status || "").split("/")[0];
    return /^(FINAL|CONDITIONAL|LOI|UCA)$/.test(s) ? s : "";
  }
  function obligatedNote(a) {
    if (a.status !== "UCA" && a.status !== "UCA/mod") return "";
    if (a.amount_obligated == null && a.amount_face == null) return "";
    var obl = a.amount_obligated != null ? fmtMoney(a.amount_obligated) : "n/a";
    var face = a.amount_face != null ? fmtMoney(a.amount_face) : fmtMoney(a.amount);
    return '<p class="text-xs text-[#8A8F82] mb-2"><span class="bronze-text">Obligated vs face:</span> ' + esc(obl) + ' obligated / ' + esc(face) + ' face. <a href="glossary.html#UCA" class="bronze-link">UCA</a></p>';
  }
  function awardHref(a, kind) {
    if (kind === "flagship" && a.id) return "award/" + encodeURIComponent(a.id) + ".html";
    if (a.id) return "award.html?id=" + encodeURIComponent(a.id);
    return "awards.html";
  }
  function tickerHref(t) { return "ticker/" + encodeURIComponent(t) + ".html"; }
  var RETURNS = {};
  function returnLine(a) {
    if (!a.ticker) return '<p class="text-xs text-[#8A8F82] mt-2">Private recipient — no announcement-to-now return.</p>';
    var rec = RETURNS[a.ticker + "|" + a.id] || RETURNS[a.ticker];
    if (!rec || rec.return_pct == null) {
      return '<p class="text-xs text-[#8A8F82] mt-2">If you bought ' + esc(a.ticker) + " after this deal was announced, there is no reliable close for a return — we will not invent one.</p>";
    }
    var cls = rec.return_pct >= 0 ? "ret-pos" : "ret-neg";
    return '<p class="text-xs mt-2 return-block">If you bought ' + esc(a.ticker) + " at the " + esc(rec.announce_date) + " close after this deal was announced, the return to " + esc(rec.as_of_date) + ' would have been <span class="' + cls + '">' + rec.return_pct + "%</span>.</p>";
  }
  function card(a, kind) {
    var amount = a.amount_display || fmtMoney(a.amount);
    var ticker = a.ticker
      ? '<div class="text-xs mt-2"><span class="bronze-text">Ticker:</span> <a class="bronze-link" href="' + esc(tickerHref(a.ticker)) + '">' + esc(a.ticker) + "</a> · <button type=\"button\" class=\"watch-btn text-xs px-3 py-1\" data-watch-ticker=\"" + esc(a.ticker) + "\">Watch " + esc(a.ticker) + "</button></div>"
      : (kind === "flagship" ? '<div class="text-xs mt-2 text-[#8A8F82]">No verified public ticker</div>' : "");
    var titleText = a.title || "Award";
    var title = '<div class="text-sm bronze-text mb-1"><a class="bronze-link" href="' + esc(awardHref(a, kind)) + '">' + esc(titleText) + "</a></div>";
    var shownStatus = a.status_label || a.status;
    var stClass = statusClass(a.status);
    var status = shownStatus && kind === "flagship"
      ? '<span class="badge-status badge-' + esc(stClass) + '">' + esc(shownStatus) + "</span>"
      : (kind === "primes" ? '<span class="badge-status badge-FINAL">NEW PRIME</span>' : "");
    var sourceLabel = kind === "primes" ? "USAspending source →" : "Official source →";
    var el = document.createElement("article");
    el.className = "deco-card rounded-3xl p-6";
    el.setAttribute("data-sector", a.sector || "");
    if (a.ticker) el.setAttribute("data-ticker", a.ticker);
    el.innerHTML =
      '<div class="flex justify-between items-start mb-3 gap-3">' +
        '<div class="text-xs text-[#8A8F82]">' + esc(sectorLabel(a.sector)) + (a.agency ? " · " + esc(a.agency) : "") + "</div>" +
        '<span class="px-2 py-1 badge-green text-xs rounded whitespace-nowrap">' + esc(fmtDate(a.date)) + "</span>" +
      "</div>" + title +
      '<h3 class="text-xl font-semibold leading-snug"><a href="' + esc(awardHref(a, kind)) + '">' + esc(a.recipient_name || "") + "</a></h3>" +
      '<div class="flex flex-wrap items-center gap-2 mt-2 mb-2">' +
        '<div class="text-lg font-semibold amount-pos">' + esc(amount) + "</div>" + status +
      "</div>" +
      obligatedNote(a) +
      '<p class="text-sm text-[#8A8F82] mb-2">' + esc(a.description || "") + "</p>" + ticker +
      returnLine(a) +
      (a.source_url ? '<a href="' + esc(a.source_url) + '" target="_blank" rel="noopener" class="inline-block mt-3 text-xs bronze-link">' + sourceLabel + "</a>" : "");
    return el;
  }
  var feeds = [];
  var currentSector = (function () {
    var q = new URLSearchParams(location.search).get("sector");
    if (q && /^(nuclear|magnets|chips|other)$/.test(q)) return q;
    var preset = document.body.getAttribute("data-sector-page");
    if (preset && /^(nuclear|magnets|chips|other)$/.test(preset)) return preset;
    return "all";
  })();
  var watchOnly = false;
  function bind(rootId, metaId, url, kind, bake) {
    var root = document.getElementById(rootId);
    if (!root) return;
    var limit = parseInt(root.getAttribute("data-limit") || "0", 10);
    var DATA = null;
    function apply(sector) {
      var awards = ((DATA && DATA.awards) || []).slice();
      if (sector && sector !== "all") awards = awards.filter(function (a) { return a.sector === sector; });
      if (watchOnly && window.FedForgeWatch) {
        var w = window.FedForgeWatch.list();
        awards = awards.filter(function (a) { return a.ticker && w.indexOf(a.ticker) !== -1; });
      }
      awards.sort(function (a, b) { return (b.date || "").localeCompare(a.date || ""); });
      var shown = limit ? awards.slice(0, limit) : awards;
      root.innerHTML = "";
      if (!shown.length) {
        root.innerHTML = '<p class="text-sm text-[#8A8F82] col-span-full">No ' + (kind === "primes" ? "new primes" : "flagship deals") + " in this filter.</p>";
      } else {
        shown.forEach(function (a) { root.appendChild(card(a, kind)); });
        if (window.FedForgeWatch) window.FedForgeWatch.bind(root);
      }
      var meta = document.getElementById(metaId);
      if (meta && DATA) {
        var windowBits = (DATA.window && DATA.window.start)
          ? " · window " + DATA.window.start + " to " + DATA.window.end
          : "";
        if (kind === "flagship") {
          meta.textContent = shown.length + " flagship deals · curated.json count " + (DATA.count || awards.length) +
            " · snapshot " + (DATA.generated_at || "") + windowBits +
            ". Status: FINAL / CONDITIONAL / LOI / UCA. Not megadeals mixed with university grants.";
        } else {
          meta.textContent = shown.length + " new primes (university / SBIR / USAspending) · snapshot " +
            (DATA.generated_at || "") + windowBits +
            ". These are new primes, not flagship megadeals.";
        }
      }
    }
    feeds.push(apply);
    function use(data) {
      if (!data || !Array.isArray(data.awards)) {
        root.innerHTML = '<p class="text-sm text-[#8A8F82]">Feed file is a stub (awards is not an array). Empty state — no invented awards.</p>';
        return;
      }
      DATA = data;
      apply(currentSector);
    }
    if (bake && Array.isArray(bake.awards) && bake.awards.length) use(bake);
    fetch(url)
      .then(function (r) { if (!r.ok) throw new Error(url + " " + r.status); return r.json(); })
      .then(function (data) {
        if (data && Array.isArray(data.awards) && data.awards.length) use(data);
      })
      .catch(function () {
        if (DATA) return;
        root.innerHTML = '<p class="text-sm text-[#8A8F82] col-span-full">Could not load ' + esc(url) + ". Serve over HTTP. Empty state — no invented awards.</p>";
        var meta = document.getElementById(metaId);
        if (meta) meta.textContent = (kind === "flagship" ? "Flagship" : "New primes") + " feed failed to load.";
      });
  }
  fetch("data/returns.json")
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      ((data && data.returns) || []).forEach(function (r) {
        if (r.award_id) RETURNS[r.ticker + "|" + r.award_id] = r;
        if (!RETURNS[r.ticker]) RETURNS[r.ticker] = r;
      });
    })
    .catch(function () {})
    .then(function () {
      bind("flagship-feed", "flagship-meta", "data/curated.json", "flagship", window.FEDFORGE_CURATED);
      bind("primes-feed", "primes-meta", "data/awards.json", "primes", window.FEDFORGE_AWARDS);
    });
  document.querySelectorAll("[data-filter-sector]").forEach(function (btn) {
    btn.classList.toggle("is-on", btn.getAttribute("data-filter-sector") === currentSector);
    btn.addEventListener("click", function () {
      currentSector = btn.getAttribute("data-filter-sector") || "all";
      if (history.replaceState) {
        var u = new URL(location.href);
        if (currentSector === "all") u.searchParams.delete("sector");
        else u.searchParams.set("sector", currentSector);
        history.replaceState({}, "", u);
      }
      document.querySelectorAll("[data-filter-sector]").forEach(function (b) {
        b.classList.toggle("is-on", b.getAttribute("data-filter-sector") === currentSector);
      });
      feeds.forEach(function (fn) { fn(currentSector); });
    });
  });
  var watchBtn = document.getElementById("filter-watchlist");
  if (watchBtn) {
    watchBtn.addEventListener("click", function () {
      watchOnly = !watchOnly;
      watchBtn.classList.toggle("is-on", watchOnly);
      watchBtn.setAttribute("aria-pressed", watchOnly ? "true" : "false");
      feeds.forEach(function (fn) { fn(currentSector); });
    });
  }
})();
