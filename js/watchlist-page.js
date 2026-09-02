(function () {
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  var root = document.getElementById("watchlist-root");
  if (!root) return;
  function loadAll() {
    return Promise.all([
      fetch("data/curated.json").then(function (r) { return r.json(); }),
      fetch("data/awards.json").then(function (r) { return r.json(); }).catch(function () { return { awards: [] }; }),
      fetch("data/public-primes.json").then(function (r) { return r.json(); }).catch(function () { return { awards: [] }; }),
      fetch("data/returns.json").then(function (r) { return r.json(); }).catch(function () { return { returns: [] }; })
    ]);
  }
  function render(pack) {
    var watched = (window.FedForgeWatch && window.FedForgeWatch.list()) || [];
    if (!watched.length) {
      root.innerHTML = '<p class="text-sm text-[#8A8F82]">Nothing saved yet. Open a <a class="bronze-link" href="top-companies.html">ticker page</a> and tap Watch. This list lives in your browser (localStorage key <code>fedforge-watchlist</code>) — we do not have an account for you.</p>';
      return;
    }
    var RET = {};
    (pack[3].returns || []).forEach(function (r) { if (r.award_id) RET[r.ticker + "|" + r.award_id] = r; });
    var awards = (pack[0].awards || []).concat(pack[1].awards || []).concat(pack[2].awards || []);
    var html = "";
    watched.forEach(function (t) {
      var mine = awards.filter(function (a) { return a.ticker === t; });
      html += '<section class="deco-card rounded-3xl p-6 mb-6"><div class="flex justify-between gap-3"><h2 class="text-2xl font-semibold"><a class="bronze-link" href="ticker/' + esc(t) + '.html">' + esc(t) + "</a></h2>" +
        '<button type="button" class="watch-btn" data-watch-ticker="' + esc(t) + '">Watch ' + esc(t) + "</button></div>";
      if (!mine.length) html += '<p class="text-sm text-[#8A8F82] mt-3">No sourced awards for this ticker in the loaded files.</p>';
      mine.forEach(function (a) {
        var rec = RET[t + "|" + a.id];
        var ret = "—";
        if (rec && rec.return_pct != null) {
          var cls = rec.return_pct >= 0 ? "ret-pos" : "ret-neg";
          ret = "If you bought " + esc(t) + " at the " + esc(rec.announce_date) + " close after this deal was announced, the return to " + esc(rec.as_of_date) + ' would have been <span class="' + cls + '">' + rec.return_pct + "%</span>.";
        } else {
          ret = "No reliable close for a return — we will not invent one.";
        }
        var href = (String(a.id).indexOf("-20") !== -1 || /^(war|doe|chips|osc)-/.test(a.id || "")) ? ("award/" + a.id + ".html") : ("award.html?id=" + encodeURIComponent(a.id));
        html += '<div class="mt-4 border-t border-[#2C382E] pt-4"><a class="bronze-link" href="' + esc(href) + '">' + esc(a.title || a.recipient_name) + "</a>" +
          '<div class="text-xs text-[#8A8F82]">' + esc(a.date || "") + " · " + esc(a.amount_display || "") + "</div>" +
          '<p class="text-sm mt-2">' + ret + "</p></div>";
      });
      html += "</section>";
    });
    root.innerHTML = html;
    if (window.FedForgeWatch) window.FedForgeWatch.bind(root);
  }
  loadAll().then(function (pack) {
    render(pack);
    document.addEventListener("fedforge-watchlist-change", function () { render(pack); });
  }).catch(function () {
    root.innerHTML = '<p class="text-sm text-[#8A8F82]">Could not load award JSON. Serve over HTTP.</p>';
  });
  var nbtn = document.getElementById("notify-demo");
  if (nbtn) {
    nbtn.addEventListener("click", function () {
      var note = document.getElementById("notify-note");
      if (!("Notification" in window)) {
        if (note) note.textContent = "This browser has no Notification API. Live email pings are not wired yet. Use the RSS feed if you want a reader app to poll.";
        return;
      }
      function fire() {
        new Notification("FedForge demo", { body: "You would get a ping when we add a new award for LEU. This is a local demo — live email pings are not wired yet." });
        if (note) note.textContent = "Demo notification fired locally. Live email pings are not wired yet. Subscribe to feed.xml in a reader if you want to poll.";
      }
      if (Notification.permission === "granted") fire();
      else Notification.requestPermission().then(function (p) {
        if (p === "granted") fire();
        else if (note) note.textContent = "Permission was not granted. Live email pings are not wired yet. feed.xml is the honest polling option.";
      });
    });
  }
})();
