(function () {
  var btn = document.getElementById("nav-toggle");
  var menu = document.getElementById("nav-mobile");
  if (!btn || !menu) return;
  btn.addEventListener("click", function () {
    var willOpen = menu.classList.contains("hidden");
    menu.classList.toggle("hidden", !willOpen);
    btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
  });
})();
