(function () {
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function slug(s) {
    return String(s || "").split("/")[0].trim().replace(/\s+/g, "-");
  }
  var root = document.getElementById("glossary-root");
  var meta = document.getElementById("glossary-meta");
  if (!root) return;
  fetch("data/glossary.json")
    .then(function (r) { if (!r.ok) throw new Error("glossary.json " + r.status); return r.json(); })
    .then(function (data) {
      if (meta) meta.textContent = (data.count || 0) + " terms · status tags, agencies, programs, nuclear/materials, defense systems, and data sources.";
      root.innerHTML = "";
      (data.groups || []).forEach(function (g) {
        var sec = document.createElement("section");
        sec.className = "mb-12";
        var h = document.createElement("h2");
        h.className = "text-2xl font-semibold section-header mb-6";
        h.textContent = g.name || "";
        var grid = document.createElement("div");
        grid.className = "grid md:grid-cols-2 lg:grid-cols-3 gap-6";
        (g.items || []).forEach(function (it) {
          var art = document.createElement("article");
          art.className = "deco-card rounded-3xl p-6";
          art.id = slug(it.abbr);
          art.innerHTML =
            '<div class="text-xs bronze-text mb-1 tracking-wide">' + esc(it.abbr) + "</div>" +
            '<h3 class="text-xl font-semibold mb-2">' + esc(it.full) + "</h3>" +
            '<p class="text-sm text-[#E8E4D9] mb-2">' + esc(it.what) + "</p>" +
            '<p class="text-sm text-[#8A8F82]"><span class="bronze-text">Why it shows up here:</span> ' + esc(it.why) + "</p>";
          grid.appendChild(art);
        });
        sec.appendChild(h);
        sec.appendChild(grid);
        root.appendChild(sec);
      });
    })
    .catch(function () {
      root.innerHTML = '<p class="text-sm text-[#8A8F82]">Could not load data/glossary.json. Serve over HTTP.</p>';
    });
})();
