(function () {
  function depthPrefix() {
    var path = location.pathname || "";
    if (/\/(ticker|award|guides)\/[^/]*$/.test(path)) return "../";
    return "";
  }
  var P = depthPrefix();
  function pageFile() {
    var p = (location.pathname.split("/").pop() || "");
    if (!p || p.indexOf(".") === -1) {
      if (/\/nuclear\/?$/.test(location.pathname)) return "nuclear.html";
      if (/\/magnets\/?$/.test(location.pathname)) return "magnets.html";
      if (/\/chips\/?$/.test(location.pathname)) return "chips.html";
      if (/\/watchlist\/?$/.test(location.pathname)) return "watchlist.html";
      if (/\/finding\/?$/.test(location.pathname)) return "finding.html";
      if (/\/findings\/?$/.test(location.pathname)) return "findings.html";
      if (/\/share\/?$/.test(location.pathname)) return "share.html";
      p = "index.html";
    }
    return p;
  }
  function hrefOf(a) {
    return (a.getAttribute("href") || "").replace(/^\.\.\//, "");
  }
  function ensureLink(container, file, label, opts) {
    opts = opts || {};
    if (!container) return;
    var exists = false;
    container.querySelectorAll("a").forEach(function (a) {
      if (hrefOf(a) === file) exists = true;
    });
    if (exists) return;
    var a = document.createElement("a");
    a.href = P + file;
    a.textContent = label;
    if (opts.className) a.className = opts.className;
    if (pageFile() === file) {
      a.classList.add("is-active");
      a.setAttribute("aria-current", "page");
    }
    var after = null;
    if (opts.afterFile) {
      container.querySelectorAll("a").forEach(function (x) {
        if (hrefOf(x) === opts.afterFile) after = x;
      });
    }
    var briefing = null;
    container.querySelectorAll("a").forEach(function (x) {
      if (hrefOf(x) === "free-report.html") briefing = x;
    });
    if (opts.beforeBriefing && briefing) container.insertBefore(a, briefing);
    else if (after && after.nextSibling) container.insertBefore(a, after.nextSibling);
    else if (after) container.appendChild(a);
    else if (briefing) container.insertBefore(a, briefing);
    else container.appendChild(a);
  }
  var desktop = document.querySelector("nav[aria-label='Primary'] .nav-link");
  desktop = desktop ? desktop.parentElement : null;
  var mobile = document.getElementById("nav-mobile");
  ensureLink(desktop, "top-companies.html", "Top companies", { className: "nav-link", afterFile: "companies.html" });
  ensureLink(desktop, "findings.html", "Findings", { className: "nav-link", afterFile: "top-companies.html" });
  ensureLink(desktop, "share.html", "Share", { className: "nav-link", afterFile: "findings.html" });
  ensureLink(desktop, "glossary.html", "Glossary", { className: "nav-link", afterFile: "share.html" });
  ensureLink(desktop, "watchlist.html", "Watchlist", { className: "nav-link", beforeBriefing: true });
  ensureLink(mobile, "top-companies.html", "Top companies", { afterFile: "companies.html" });
  ensureLink(mobile, "findings.html", "Findings", { afterFile: "top-companies.html" });
  ensureLink(mobile, "share.html", "Share", { afterFile: "findings.html" });
  ensureLink(mobile, "glossary.html", "Glossary", { afterFile: "share.html" });
  ensureLink(mobile, "watchlist.html", "Watchlist", { beforeBriefing: true });
  var pf = pageFile();
  var sectorPages = { "nuclear.html": 1, "magnets.html": 1, "chips.html": 1, "sectors.html": 1 };
  if (sectorPages[pf]) {
    document.querySelectorAll("a").forEach(function (a) {
      if (hrefOf(a) === "sectors.html") {
        a.classList.add("is-active");
        a.setAttribute("aria-current", "page");
      }
    });
  }
  ["watchlist.html", "findings.html", "share.html", "finding.html", "finding-red.html", "finding-loi.html"].forEach(function (f) {
    if (pf === f || (f === "findings.html" && /finding/.test(pf))) {
      document.querySelectorAll("a").forEach(function (a) {
        var h = hrefOf(a);
        if (h === f || (f === "findings.html" && (h === "findings.html" || h === "finding.html"))) {
          if (h === "findings.html" || h === f) {
            a.classList.add("is-active");
            a.setAttribute("aria-current", "page");
          }
        }
      });
    }
  });
  var btn = document.getElementById("nav-toggle");
  var menu = document.getElementById("nav-mobile");
  if (!btn || !menu) return;
  function setOpen(open) {
    menu.classList.toggle("hidden", !open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  }
  btn.addEventListener("click", function () {
    setOpen(menu.classList.contains("hidden"));
  });
  menu.querySelectorAll("a").forEach(function (a) {
    a.addEventListener("click", function () { setOpen(false); });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") setOpen(false);
  });
})();
