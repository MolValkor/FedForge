(function () {
  function prefix() {
    var path = location.pathname || "";
    if (/\/(ticker|award)\/[^/]*$/.test(path)) return "../";
    return "";
  }
  function fmtIso(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    try {
      return new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" }).format(d);
    } catch (e) { return iso; }
  }
  function fill(data) {
    var pull = data.last_usaspending_pull || "";
    var prices = data.last_price_as_of || "";
    var line = "Last USAspending pull " + fmtIso(pull) + " \u00b7 Prices as of " + prices + " (last completed close)";
    document.querySelectorAll("[data-meta-stamp]").forEach(function (el) { el.textContent = line; });
  }
  fetch(prefix() + "data/meta.json")
    .then(function (r) { if (!r.ok) throw new Error("meta"); return r.json(); })
    .then(fill)
    .catch(function () {
      document.querySelectorAll("[data-meta-stamp]").forEach(function (el) {
        if (!el.textContent) el.textContent = "Last USAspending pull and price as-of live in data/meta.json (serve over HTTP).";
      });
    });
})();
