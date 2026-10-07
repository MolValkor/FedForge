/* Shared copy-to-clipboard helper + "Copy link" buttons (any element with data-copy-link). */
(function () {
  function fallback(text) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (e) { return false; }
  }
  window.FedForgeCopy = function (text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(function () { return true; }, function () { return fallback(text); });
    }
    return Promise.resolve(fallback(text));
  };
  document.addEventListener("click", function (e) {
    var btn = e.target.closest ? e.target.closest("[data-copy-link]") : null;
    if (!btn) return;
    e.preventDefault();
    var url = btn.getAttribute("data-copy-link");
    var label = btn.getAttribute("data-label-default") || btn.textContent;
    btn.setAttribute("data-label-default", label);
    window.FedForgeCopy(url).then(function (ok) {
      var live = document.getElementById("ff-live");
      if (!live) {
        live = document.createElement("div");
        live.id = "ff-live";
        live.className = "sr-only";
        live.setAttribute("aria-live", "polite");
        document.body.appendChild(live);
      }
      live.textContent = ok ? "Link copied to clipboard" : "Copy failed";
      btn.textContent = ok ? "Link copied" : "Copy failed";
      btn.classList.toggle("is-on", ok);
      setTimeout(function () { btn.textContent = label; btn.classList.remove("is-on"); }, 2000);
    });
  });
})();

/* FedForge primary navigation.
 * One source of truth for the menu on every page: the static markup in each HTML file is a
 * no-JS fallback, and this script rebuilds the desktop row and the mobile panel from ITEMS.
 *
 * Why: Netlify's "Pretty URLs" post-processing rewrites hrefs on the live site from
 * "awards.html" to "/awards". The previous script compared raw hrefs, so every
 * "is this link already present?" check failed and a second copy of the menu was appended
 * (visible at 1280px as the nav appearing twice). Links are now compared by a normalised
 * key and the menu is rebuilt, never appended to.
 */
(function () {
  var ITEMS = [
    { file: "index.html", label: "Dashboard" },
    { file: "awards.html", label: "Awards", dirs: ["award"], also: ["award.html"] },
    { file: "sectors.html", label: "Sectors", also: ["nuclear.html", "magnets.html", "chips.html"] },
    { file: "private-capital.html", label: "Private capital" },
    { file: "companies.html", label: "Companies", dirs: ["ticker"] },
    { file: "top-companies.html", label: "Top companies" },
    { file: "findings.html", label: "Findings", also: ["finding.html", "finding-red.html", "finding-loi.html"] },
    { file: "watchlist.html", label: "Watchlist" },
    { file: "follow.html", label: "Follow" }
  ];
  var MORE = [
    { file: "glossary.html", label: "Glossary" },
    { file: "guides/how-to-read-a-federal-award.html", label: "How to read an award" },
    { file: "pipeline.html", label: "Pipeline" },
    { file: "movers.html", label: "Movers" },
    { file: "international.html", label: "International" },
    { file: "historical.html", label: "Historical" },
    { file: "share.html", label: "Share pack" }
  ];
  var CTA = { file: "free-report.html", label: "Free briefing" };

  function segments(pathname) {
    return String(pathname || "").split("#")[0].split("?")[0].replace(/\/+$/, "").split("/").filter(Boolean);
  }
  var segs = segments(location.pathname);
  var inSubdir = segs.length > 1 && /^(ticker|award|guides)$/i.test(segs[segs.length - 2]);
  var P = inSubdir ? "../" : "";
  var dir = inSubdir ? segs[segs.length - 2].toLowerCase() : "";
  var page = (segs[segs.length - 1] || "index").toLowerCase();
  if (!/\.html$/.test(page)) page += ".html";
  var here = (dir ? dir + "/" : "") + page;

  function isActive(item) {
    if (item.file === here) return true;
    if (!dir && item.also && item.also.indexOf(page) !== -1) return true;
    if (dir && item.dirs && item.dirs.indexOf(dir) !== -1) return true;
    return false;
  }
  function link(item, className) {
    var a = document.createElement("a");
    a.href = P + item.file;
    a.textContent = item.label;
    if (className) a.className = className;
    if (isActive(item)) {
      a.classList.add("is-active");
      a.setAttribute("aria-current", "page");
    }
    return a;
  }

  var nav = document.querySelector("nav[aria-label='Primary']");
  if (!nav) return;
  var firstLink = nav.querySelector(".nav-link");
  var desktop = firstLink ? firstLink.parentElement : null;
  var mobile = document.getElementById("nav-mobile");

  if (desktop) {
    desktop.innerHTML = "";
    desktop.classList.remove("flex-wrap");
    desktop.classList.add("nav-desktop");
    ITEMS.forEach(function (it) { desktop.appendChild(link(it, "nav-link")); });
    var wrap = document.createElement("div");
    wrap.className = "nav-more";
    var moreBtn = document.createElement("button");
    moreBtn.type = "button";
    moreBtn.className = "nav-link nav-more-btn";
    moreBtn.setAttribute("aria-expanded", "false");
    moreBtn.setAttribute("aria-controls", "nav-more-menu");
    moreBtn.innerHTML = 'More <span aria-hidden="true">▾</span>';
    var menu = document.createElement("div");
    menu.id = "nav-more-menu";
    menu.className = "nav-more-menu";
    menu.hidden = true;
    var moreActive = false;
    MORE.forEach(function (it) {
      var a = link(it);
      if (a.classList.contains("is-active")) moreActive = true;
      menu.appendChild(a);
    });
    if (moreActive) moreBtn.classList.add("is-active");
    wrap.appendChild(moreBtn);
    wrap.appendChild(menu);
    desktop.appendChild(wrap);
    desktop.appendChild(link(CTA, "nav-link cta-outline px-4 py-2 rounded-xl text-sm"));
    function setMore(open) {
      menu.hidden = !open;
      moreBtn.setAttribute("aria-expanded", open ? "true" : "false");
    }
    moreBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      setMore(menu.hidden);
    });
    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) setMore(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !menu.hidden) { setMore(false); moreBtn.focus(); }
    });
  }

  if (mobile) {
    mobile.innerHTML = "";
    ITEMS.forEach(function (it) { mobile.appendChild(link(it)); });
    var h = document.createElement("p");
    h.className = "nav-mobile-heading";
    h.textContent = "More";
    mobile.appendChild(h);
    MORE.forEach(function (it) { mobile.appendChild(link(it)); });
    mobile.appendChild(link(CTA, "nav-mobile-cta"));
  }

  var btn = document.getElementById("nav-toggle");
  if (!btn || !mobile) return;
  function setOpen(open) {
    mobile.classList.toggle("hidden", !open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  }
  btn.addEventListener("click", function () {
    setOpen(mobile.classList.contains("hidden"));
  });
  mobile.querySelectorAll("a").forEach(function (a) {
    a.addEventListener("click", function () { setOpen(false); });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !mobile.classList.contains("hidden")) { setOpen(false); btn.focus(); }
  });
})();
