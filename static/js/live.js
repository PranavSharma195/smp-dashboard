/* Live filtering for Explore and Budget Finder. Fetches server-rendered grid
   HTML from the JSON API (no page reload). Falls back to normal form submit
   if JavaScript is unavailable. */
(function () {
  "use strict";
  var M = window.Motion;
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector("[data-live-form]");
    var results = document.querySelector("[data-live-results]");
    if (!form || !results) return;
    var api = form.dataset.api;
    var floor = +form.dataset.floor, ceiling = +form.dataset.ceiling;
    var countEls = document.querySelectorAll("[data-result-count]");
    var avgEl = document.querySelector("[data-result-avg]");
    var controller = null, timer = null, shownCount = null;

    function skeleton() {
      var html = '<div class="product-grid" aria-hidden="true">';
      for (var i = 0; i < 6; i++) html += '<div class="sk-card"><div class="skeleton a"></div><div class="skeleton b"></div><div class="skeleton c"></div><div class="skeleton d"></div></div>';
      results.innerHTML = html + "</div>";
    }
    function params(page) {
      var p = new URLSearchParams(), fd = new FormData(form);
      fd.forEach(function (v, k) {
        if (k === "csrfmiddlewaretoken" || v === "") return;
        if (k === "budget_min" && +v <= floor) return;
        if (k === "budget_max" && +v >= ceiling) return;
        if (k === "sort" && v === (form.dataset.defaultSort || "viability")) return;
        p.append(k, v);
      });
      if (page && page > 1) p.set("page", page);
      return p;
    }
    function refresh(page) {
      var p = params(page);
      if (controller) controller.abort();
      controller = ("AbortController" in window) ? new AbortController() : null;
      skeleton();
      fetch(api + "?" + p.toString(), { headers: { "X-Requested-With": "fetch", "Accept": "application/json" }, credentials: "same-origin", signal: controller ? controller.signal : undefined })
        .then(function (r) { if (!r.ok) throw new Error("bad response"); return r.json(); })
        .then(function (d) {
          results.innerHTML = d.html;
          countEls.forEach(function (el) {
            var from = shownCount === null ? 0 : shownCount;
            M.tween(from, d.count, 450, function (n) { el.textContent = Math.round(n); });
          });
          shownCount = d.count;
          if (avgEl) avgEl.textContent = d.avg_margin.toFixed(1) + "%";
          M.reveal(results.querySelectorAll(".pcard"), { stagger: 0.04, y: 14, duration: 0.45 });
          M.progress(results);
          var qs = p.toString();
          history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
          var ev = new CustomEvent("results:updated", { detail: d }); document.dispatchEvent(ev);
        })
        .catch(function (err) {
          if (err && err.name === "AbortError") return;
          results.innerHTML = '<div class="empty"><h3>Couldn’t load products</h3><p>The server didn’t respond. Check that it is still running, then try again.</p><button class="btn btn-ghost" type="button" data-retry>Try again</button></div>';
        });
    }
    function schedule(delay) { clearTimeout(timer); timer = setTimeout(function () { refresh(); }, delay === undefined ? 220 : delay); }

    // initial count for tween baseline
    var first = document.querySelector("[data-result-count]");
    if (first) shownCount = parseInt(first.textContent, 10) || 0;

    form.addEventListener("submit", function (e) { e.preventDefault(); refresh(); });
    form.addEventListener("budget:change", function () { schedule(60); });
    form.addEventListener("input", function (e) {
      if (e.target.closest("[data-budget]")) return;
      schedule(e.target.type === "text" || e.target.type === "search" ? 280 : 120);
    });
    form.addEventListener("change", function (e) { if (!e.target.closest("[data-budget]")) schedule(60); });

    results.addEventListener("click", function (e) {
      var pg = e.target.closest("[data-page]");
      if (pg) { e.preventDefault(); refresh(+pg.dataset.page); window.scrollTo({ top: 0, behavior: M.reduce ? "auto" : "smooth" }); }
      if (e.target.closest("[data-retry]")) refresh();
      if (e.target.closest("[data-clear]")) { e.preventDefault(); reset(); }
    });

    function reset() {
      form.querySelectorAll("input[type=text], input[type=search], input[type=number]").forEach(function (i) {
        if (i.closest("[data-budget]")) return; i.value = "";
      });
      form.querySelectorAll("select").forEach(function (s) { s.selectedIndex = 0; if (s.name === "sort") s.value = form.dataset.defaultSort || "viability"; });
      var b = form.querySelector("[data-budget]");
      if (b && b.setBudget) b.setBudget(floor, ceiling);
      var top = document.querySelector("[data-live-q]"); if (top) top.value = "";
      refresh();
    }
    document.querySelectorAll("[data-reset]").forEach(function (btn) { btn.addEventListener("click", function (e) { e.preventDefault(); reset(); }); });

    var saveBtn = document.querySelector("[data-save-filters]");
    if (saveBtn) saveBtn.addEventListener("click", function () {
      var body = new URLSearchParams(params());
      fetch(saveBtn.dataset.url, { method: "POST", headers: { "X-CSRFToken": window.SMP.csrf(), "X-Requested-With": "fetch", "Content-Type": "application/x-www-form-urlencoded" }, body: body.toString(), credentials: "same-origin" })
        .then(function (r) { return r.json(); }).then(function (d) { window.SMP.toast(d.saved ? "Filters saved. They’ll load next time you open Explore." : "Saved filters cleared."); })
        .catch(function () { window.SMP.toast("Couldn’t save filters.", "warn"); });
    });

    var ft = document.querySelector("[data-filter-toggle]"), panel = document.querySelector(".filters");
    if (ft && panel) ft.addEventListener("click", function () { panel.classList.toggle("is-open"); });
  });
})();
