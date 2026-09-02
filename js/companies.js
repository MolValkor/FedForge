(function () {
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  var FLAGSHIP_ORDER = ["LMT", "RTX", "LEU", "USAR", "PCG", "GFS"];
  var SECTOR = {
    LMT: "Munitions / interceptors",
    RTX: "Munitions / interceptors",
    LEU: "HALEU / enrichment",
    USAR: "Mine-to-magnet / CHIPS",
    PCG: "Civil Nuclear Credit / Diablo Canyon",
    GFS: "Semiconductor manufacturing / CHIPS R&D"
  };
  var WHY = {
    LMT: "Terminal High Altitude Area Defense (THAAD) undefinitized contract action (UCA) and Patriot Advanced Capability-3 (PAC-3) Missile Segment Enhancement (MSE) Army modification. Read obligated vs face — PAC-3 mod obligated $0. Face is not cash.",
    RTX: "Tomahawk / critical munitions production acceleration (FINAL) and Advanced Medium-Range Air-to-Air Missile (AMRAAM) D4/C9 undefinitized contract action (UCA). Read obligated vs face on the UCA.",
    LEU: "American Centrifuge Operating (wholly owned) is the named recipient of the Department of Energy (DOE) high-assay low-enriched uranium (HALEU) commercial-capacity task order. Also appears as a USAspending new-prime row.",
    USAR: "Creating Helpful Incentives to Produce Semiconductors (CHIPS) program definitive agreement (DFA) for a mine-to-magnet supply chain (Jun 3). Ceilings, not a claim that every dollar is disbursed.",
    PCG: "First Civil Nuclear Credit (CNC) program payment for Diablo Canyon (Aug 14). Official DOE notice is the source of record.",
    GFS: "Named in the Jul 29 CHIPS R&D letters of intent (LOIs) (seven-company package). Verified ticker in that LOI. Not closed — stays tagged LOI until definitive documents."
  };
  var NAMES = { LMT: "Lockheed Martin", RTX: "RTX / Raytheon", LEU: "Centrus Energy", USAR: "USA Rare Earth", PCG: "PG&E", GFS: "GlobalFoundries" };

  function card(name, sector, status, layer, why, ticker, links) {
    var el = document.createElement("div");
    el.className = "deco-card rounded-3xl p-6";
    var src = (links || []).map(function (L) {
      return '<a href="' + esc(L.href) + '" target="_blank" rel="noopener" class="bronze-link">' + esc(L.label) + "</a>";
    }).join("");
    el.innerHTML =
      '<div class="flex justify-between"><div><div class="text-xl font-semibold">' + esc(name) + '</div><div class="text-xs text-[#8A8F82]">' + esc(sector) + '</div></div><div class="text-right text-sm"><div class="amount-pos">' + esc(status) + '</div><div class="text-xs text-[#8A8F82]">' + esc(layer) + "</div></div></div>" +
      '<p class="text-sm text-[#8A8F82] mt-4">' + esc(why) + "</p>" +
      '<div class="mt-3 text-xs"><span class="bronze-text">Ticker:</span> ' + esc(ticker) + "</div>" +
      (src ? '<div class="mt-3 flex flex-col gap-1 text-xs">' + src + "</div>" : "");
    return el;
  }

  var flagRoot = document.getElementById("flagship-companies");
  var ctxRoot = document.getElementById("context-companies");
  if (!flagRoot) return;

  fetch("data/curated.json")
    .then(function (r) { if (!r.ok) throw new Error("curated " + r.status); return r.json(); })
    .then(function (data) {
      var by = {};
      (data.awards || []).forEach(function (a) {
        if (!a.ticker) return;
        (by[a.ticker] = by[a.ticker] || []).push(a);
      });
      flagRoot.innerHTML = "";
      FLAGSHIP_ORDER.forEach(function (t) {
        var rows = by[t] || [];
        var statuses = [];
        var links = [];
        rows.forEach(function (a) {
          var st = a.status_label || a.status;
          if (st && statuses.indexOf(st) === -1) statuses.push(st);
          if (a.source_url) links.push({ href: a.source_url, label: (a.title || "Official source") + " →" });
        });
        var layer = t === "LEU" ? "flagship + new prime" : (t === "GFS" ? "Jul 29 package" : "flagship");
        flagRoot.appendChild(card(NAMES[t], SECTOR[t], statuses.join(" + ") || "flagship", layer, WHY[t], t, links));
      });
    })
    .catch(function () {
      flagRoot.innerHTML = '<p class="text-sm text-[#8A8F82]">Could not load data/curated.json. Serve over HTTP.</p>';
    });

  var CONTEXT = [
    { name: "MP Materials", sector: "Critical Minerals / Rare Earth Magnets", status: "DoD partnership", layer: "previously reported", why: "U.S. rare earth miner/magnet maker previously reported as receiving DoD equity, loan, offtake, and price-floor support for a domestic magnet facility. Not in this 90-day USAspending new-award snapshot.", ticker: "MP" },
    { name: "IBM", sector: "Quantum / advanced manufacturing", status: "CHIPS LOI (prior)", layer: "previously reported", why: "Previously named in Commerce quantum CHIPS letters of intent. No new IBM prime award in this USAspending window.", ticker: "IBM" },
    { name: "Oklo", sector: "Advanced Nuclear / small modular reactors (SMRs)", status: "DOE pilots (prior)", layer: "previously reported", why: "Advanced fission developer previously reported as selected for DOE reactor pilots. No Oklo prime award appeared in this 90-day USAspending pull.", ticker: "OKLO" },
    { name: "IonQ", sector: "Trapped-Ion Quantum", status: "CHIPS LOI (prior)", layer: "previously reported", why: "Previously included in Commerce quantum incentive announcements. Not sourced as a new prime award in this snapshot.", ticker: "IONQ" },
    { name: "BWX Technologies", sector: "Nuclear Components", status: "DoD / DOE (ongoing)", layer: "previously reported", why: "Naval nuclear and advanced-reactor component supplier. No new-award hit under the BWX name in this 90-day new_awards_only query.", ticker: "BWXT" },
    { name: "ABB", sector: "Magnet materials / motors", status: "In live feed", layer: "USAspending new prime", why: "ABB INC. is the named recipient of a DOE magnet-materials award in this snapshot (Mn-Bi bonded magnets). New-prime ticker only — not a flagship ticker. Dollars are on the new-primes strip.", ticker: "ABB", links: [{ href: "awards.html#new-primes", label: "New primes strip →" }] }
  ];
  if (ctxRoot) {
    ctxRoot.innerHTML = "";
    CONTEXT.forEach(function (c) { ctxRoot.appendChild(card(c.name, c.sector, c.status, c.layer, c.why, c.ticker, c.links)); });
  }
})();
