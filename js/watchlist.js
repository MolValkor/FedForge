(function (global) {
  var KEY = "fedforge-watchlist";
  function list() {
    try {
      var raw = localStorage.getItem(KEY);
      var arr = JSON.parse(raw || "[]");
      return Array.isArray(arr) ? arr.map(function (t) { return String(t).toUpperCase(); }) : [];
    } catch (e) { return []; }
  }
  function save(arr) {
    localStorage.setItem(KEY, JSON.stringify(arr));
    document.dispatchEvent(new CustomEvent("fedforge-watchlist-change", { detail: arr.slice() }));
  }
  function has(t) { return list().indexOf(String(t || "").toUpperCase()) !== -1; }
  function toggle(t) {
    t = String(t || "").toUpperCase();
    if (!t) return list();
    var arr = list();
    var i = arr.indexOf(t);
    if (i === -1) arr.push(t); else arr.splice(i, 1);
    save(arr);
    return arr;
  }
  function label(t) { return has(t) ? "Watching " + t : "Watch " + t; }
  function bind(root) {
    (root || document).querySelectorAll("[data-watch-ticker]").forEach(function (btn) {
      var t = btn.getAttribute("data-watch-ticker");
      function paint() {
        btn.textContent = label(t);
        btn.classList.toggle("is-on", has(t));
        btn.setAttribute("aria-pressed", has(t) ? "true" : "false");
      }
      paint();
      btn.addEventListener("click", function () { toggle(t); paint(); });
    });
  }
  global.FedForgeWatch = { KEY: KEY, list: list, has: has, toggle: toggle, bind: bind, label: label };
  document.addEventListener("DOMContentLoaded", function () { bind(document); });
})(window);
