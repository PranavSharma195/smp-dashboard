/* Dashboard budget slider: live "products within budget" without reloading. */
(function () {
  "use strict";
  var M = window.Motion;
  document.addEventListener("DOMContentLoaded", function () {
    var hero = document.querySelector("[data-hero-budget]");
    if (!hero) return;
    var count = hero.querySelector("[data-hero-count]"), total = hero.querySelector("[data-hero-total]");
    var list = hero.querySelector("[data-pick-list]"), statEl = document.querySelector("[data-stat-budget]");
    var link = hero.querySelector("[data-hero-link]");
    var shown = parseInt(count.textContent, 10) || 0;
    var controller = null;
    function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
    hero.addEventListener("budget:change", function (e) {
      var v = e.detail;
      if (controller) controller.abort();
      controller = "AbortController" in window ? new AbortController() : null;
      fetch(hero.dataset.api + "?budget_min=" + v.lo + "&budget_max=" + v.hi, { headers: { "X-Requested-With": "fetch" }, credentials: "same-origin", signal: controller ? controller.signal : undefined })
        .then(function (r) { return r.json(); }).then(function (d) {
          M.tween(shown, d.in_budget, 500, function (n) { count.textContent = Math.round(n); });
          if (statEl) M.tween(parseFloat(statEl.textContent) || 0, d.in_budget, 500, function (n) { statEl.textContent = Math.round(n); });
          shown = d.in_budget;
          if (total) total.textContent = d.total;
          if (link) link.href = link.dataset.base + "?budget_min=" + v.lo + "&budget_max=" + v.hi;
          list.innerHTML = d.picks.length ? d.picks.map(function (p) {
            return '<li><a href="/products/' + encodeURIComponent(p.slug) + '/">' + esc(p.name) + '</a><span class="muted num">' + M.npr(p.invest) + "</span></li>";
          }).join("") : '<li class="muted">No products fit this range. Try widening it.</li>';
          M.reveal(list.children, { stagger: 0.05, y: 8, duration: 0.35 });
        }).catch(function (err) { if (!err || err.name !== "AbortError") window.SMP.toast("Couldn’t refresh the budget summary.", "warn"); });
    });
  });
})();
