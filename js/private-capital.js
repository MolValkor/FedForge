/* Private capital section: renders data/private-capital.json with category and beneficiary filters.
 * Every number shown comes straight from the data file; nothing is summed or estimated here. */
(function () {
  var SITE = "https://thefedforge.com";
  var LANE = {
    nuclear: { label: "Nuclear", href: "nuclear.html" },
    magnets: { label: "Magnets / rare earths", href: "magnets.html" },
    chips: { label: "Semiconductors / CHIPS", href: "chips.html" },
    other: { label: "Defense", href: "awards.html?sector=other" }
  };
  // Tickers that already have a FedForge ticker page (ticker/*.html).
  var TICKER_PAGES = { ABB: 1, BWXT: 1, GFS: 1, LEU: 1, LMT: 1, PCG: 1, RTX: 1, USAR: 1 };
  var STATUS_CLASS = { "announced": "pc-st-announced", "under construction": "pc-st-building", "operating": "pc-st-operating" };
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  var feed = document.getElementById("pc-feed");
  if (!feed) return;
  var catBox = document.getElementById("pc-cat");
  var benBox = document.getElementById("pc-ben");
  var countEl = document.getElementById("pc-count");
  var statsEl = document.getElementById("pc-stats");
  var state = { cat: "all", ben: "all" };
  var DATA = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function fmtDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    return m ? MONTHS[Number(m[2]) - 1] + " " + Number(m[3]) + ", " + m[1] : esc(iso);
  }
  function host(url) {
    try { return new URL(url).hostname.replace(/^www\./, ""); } catch (e) { return "source"; }
  }
  function ext(url, text, cls) {
    return '<a href="' + esc(url) + '" target="_blank" rel="noopener" class="' + (cls || "bronze-link") + '">' + text + "</a>";
  }
  function ownershipHtml(e) {
    if (e.ticker) {
      var t = TICKER_PAGES[e.ticker] ? '<a class="bronze-link" href="ticker/' + esc(e.ticker) + '.html">' + esc(e.ticker) + "</a>" : esc(e.ticker);
      return '<span class="pc-own pc-own-public">Listed · ' + t + "</span>";
    }
    var label = { "private": "Private · no ticker", "subsidiary": "Subsidiary · no U.S. ticker", "joint-venture": "Joint venture · no ticker" }[e.ownership] || esc(e.ownership);
    return '<span class="pc-own">' + label + "</span>";
  }

  function card(e) {
    var cats = DATA.categories || {};
    var bens = DATA.beneficiaries || {};
    var lane = LANE[e.lane] || LANE.other;
    var st = e.status ? '<span class="badge-status ' + (STATUS_CLASS[e.status] || "") + '">' + esc(e.status.toUpperCase()) + "</span>" : "";
    var amount = e.amount_usd != null
      ? '<p class="pc-amount amount-pos">' + esc(e.amount_display) + ' <span class="pc-cite">' + ext(e.amount_source_url, "source", "share-anchor") + "</span></p>"
      : '<p class="pc-amount pc-undisclosed">' + esc(e.amount_display) + "</p>";
    var benChips = (e.beneficiaries || []).map(function (b) { return '<span class="pc-chip">' + esc(bens[b] || b) + "</span>"; }).join(" ");
    var fed = e.federal_link
      ? '<div class="pc-fed"><p class="pc-k">Linked federal money</p><p>' + esc(e.federal_link.text) + " " + ext(e.federal_link.source_url, "source", "share-anchor") + "</p></div>"
      : '<div class="pc-fed pc-fed-none"><p class="pc-k">Linked federal money</p><p>None cited in our sources.</p></div>';
    var partners = (e.public_partners || []).map(function (p) {
      return esc(p.name) + " (" + esc(p.ticker) + ")";
    }).join(", ");
    var sources = (e.sources || []).map(function (s) {
      return "<li>" + ext(s.url, esc(s.label || host(s.url)) + ' <span aria-hidden="true">→</span>') + ' <span class="pc-host">' + esc(host(s.url)) + "</span></li>";
    }).join("");
    var permalink = SITE + "/private-capital.html#" + encodeURIComponent(e.id);

    var el = document.createElement("article");
    el.className = "deco-card award-card pc-card rounded-3xl p-6";
    el.id = e.id;
    el.innerHTML =
      '<div class="pc-top"><span class="pc-cat">' + esc(cats[e.category] || e.category) + "</span>" + st + "</div>" +
      '<h3 class="pc-title">' + esc(e.company) + ' <span class="pc-project">· ' + esc(e.project) + "</span></h3>" +
      '<p class="pc-meta">' + ownershipHtml(e) + ' <span aria-hidden="true">·</span> ' + esc(e.location) + "</p>" +
      '<p class="pc-meta"><time datetime="' + esc(e.date) + '">' + fmtDate(e.date) + "</time> · " + esc(e.date_event || "announced") + "</p>" +
      amount +
      '<p class="pc-what">' + esc(e.what) + "</p>" +
      '<div class="pc-ben"><p class="pc-k">Federal beneficiary</p><p>' + benChips + '</p><p class="pc-detail">' + esc(e.beneficiary_detail) + "</p></div>" +
      fed +
      (partners ? '<p class="pc-detail mt-2">Listed partner named in the source: ' + partners + "</p>" : "") +
      (e.listing_note ? '<p class="pc-detail mt-2">' + esc(e.listing_note) + "</p>" : "") +
      '<details class="pc-sources"><summary>Sources (' + (e.sources || []).length + ")</summary><ul>" + sources + "</ul></details>" +
      '<div class="award-actions"><a class="bronze-link text-sm" href="' + esc(lane.href) + '">FedForge lane: ' + esc(lane.label) + "</a>" +
      '<button type="button" class="share-btn" data-copy-link="' + esc(permalink) + '">Copy link</button></div>';
    return el;
  }

  function matches(e) {
    if (state.cat !== "all" && e.category !== state.cat) return false;
    if (state.ben !== "all" && (e.beneficiaries || []).indexOf(state.ben) === -1) return false;
    return true;
  }

  function render() {
    var list = DATA.entries.filter(matches);
    feed.innerHTML = "";
    list.forEach(function (e) { feed.appendChild(card(e)); });
    if (!list.length) feed.innerHTML = '<p class="text-[#8A8F82]">No entries match these filters.</p>';
    countEl.textContent = "Showing " + list.length + " of " + DATA.entries.length + " entries, newest first.";
    [catBox, benBox].forEach(function (box) {
      box.querySelectorAll("button").forEach(function (b) {
        var on = b.getAttribute("data-value") === state[box === catBox ? "cat" : "ben"];
        b.classList.toggle("is-on", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
    });
    var q = [];
    if (state.cat !== "all") q.push("category=" + encodeURIComponent(state.cat));
    if (state.ben !== "all") q.push("benefits=" + encodeURIComponent(state.ben));
    if (history.replaceState) history.replaceState(null, "", location.pathname + (q.length ? "?" + q.join("&") : "") + location.hash);
  }

  function buttons(box, key, options, used) {
    var html = '<button type="button" class="filter-btn" data-value="all">All</button>';
    Object.keys(options).forEach(function (k) {
      if (!used[k]) return; // only offer filters that have entries
      html += '<button type="button" class="filter-btn" data-value="' + esc(k) + '">' + esc(options[k]) + " <span class=\"pc-n\">" + used[k] + "</span></button>";
    });
    box.innerHTML = html;
    box.addEventListener("click", function (ev) {
      var b = ev.target.closest ? ev.target.closest("button[data-value]") : null;
      if (!b) return;
      state[key] = b.getAttribute("data-value");
      render();
    });
  }

  function stats() {
    var e = DATA.entries;
    var withAmt = e.filter(function (x) { return x.amount_usd != null; }).length;
    var priv = e.filter(function (x) { return x.ownership !== "public"; }).length;
    var fed = e.filter(function (x) { return !!x.federal_link; }).length;
    function s(n, label) { return '<div class="pc-stat"><span class="pc-stat-n">' + n + '</span><span class="pc-stat-l">' + label + "</span></div>"; }
    statsEl.innerHTML = s(e.length, "entries") + s(withAmt, "with a sourced amount") + s(priv, "not U.S.-listed") + s(fed, "with linked federal money");
  }

  function init(data) {
    DATA = data;
    DATA.entries.sort(function (a, b) { return a.date < b.date ? 1 : a.date > b.date ? -1 : a.company.localeCompare(b.company); });
    var catUsed = {}, benUsed = {};
    DATA.entries.forEach(function (e) {
      catUsed[e.category] = (catUsed[e.category] || 0) + 1;
      (e.beneficiaries || []).forEach(function (b) { benUsed[b] = (benUsed[b] || 0) + 1; });
    });
    var params = new URLSearchParams(location.search);
    if (catUsed[params.get("category")]) state.cat = params.get("category");
    if (benUsed[params.get("benefits")]) state.ben = params.get("benefits");
    buttons(catBox, "cat", DATA.categories || {}, catUsed);
    buttons(benBox, "ben", DATA.beneficiaries || {}, benUsed);
    stats();
    render();
    if (location.hash) {
      var t = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (t) { t.classList.add("is-target"); t.scrollIntoView(); }
    }
  }

  fetch("data/private-capital.json")
    .then(function (r) { if (!r.ok) throw new Error("data"); return r.json(); })
    .then(init)
    .catch(function () {
      countEl.textContent = "Could not load data/private-capital.json (serve the site over HTTP).";
    });
})();
