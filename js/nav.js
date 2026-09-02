(function () {
  function pageFile() {
    var p = (location.pathname.split("/").pop() || "");
    if (!p || p.indexOf(".") === -1) p = "index.html";
    return p;
  }

  function ensureLink(container, href, label, opts) {
    opts = opts || {};
    if (!container) return;
    if (container.querySelector('a[href="' + href + '"]')) return;
    var a = document.createElement("a");
    a.href = href;
    a.textContent = label;
    if (opts.className) a.className = opts.className;
    if (pageFile() === href) {
      a.classList.add("is-active");
      a.setAttribute("aria-current", "page");
    }
    var after = opts.afterHref && container.querySelector('a[href="' + opts.afterHref + '"]');
    if (after && after.nextSibling) container.insertBefore(a, after.nextSibling);
    else if (after) container.appendChild(a);
    else {
      var briefing = container.querySelector('a[href="free-report.html"]');
      if (briefing) container.insertBefore(a, briefing);
      else container.appendChild(a);
    }
  }

  var desktop = document.querySelector("nav[aria-label='Primary'] .nav-link");
  desktop = desktop ? desktop.parentElement : null;
  var mobile = document.getElementById("nav-mobile");

  ensureLink(desktop, "top-companies.html", "Top companies", { className: "nav-link", afterHref: "companies.html" });
  ensureLink(desktop, "glossary.html", "Glossary", { className: "nav-link", afterHref: "top-companies.html" });
  ensureLink(mobile, "top-companies.html", "Top companies", { afterHref: "companies.html" });
  ensureLink(mobile, "glossary.html", "Glossary", { afterHref: "top-companies.html" });

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
