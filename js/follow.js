/* Follow page: copy-to-clipboard for the feed URL, and the (disabled) email placeholder. */
(function () {
  var status = document.getElementById("copy-status");
  document.querySelectorAll("[data-copy-target]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var el = document.getElementById(btn.getAttribute("data-copy-target"));
      if (!el) return;
      var text = el.textContent.trim();
      window.FedForgeCopy(text).then(function (ok) {
        if (status) status.textContent = ok ? "Copied: " + text : "Copy failed. Select the address and copy it manually.";
      });
    });
  });
  // Email signup stays hidden until a provider endpoint is configured in follow.html.
  var box = document.getElementById("email-signup");
  var endpoint = box && (box.getAttribute("data-endpoint") || "").trim();
  if (box && endpoint && /^https:\/\//.test(endpoint)) {
    box.querySelector("form").setAttribute("action", endpoint);
    box.hidden = false;
  }
})();
