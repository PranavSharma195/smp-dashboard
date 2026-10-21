/* App shell: sidebar, menus, page transitions, toasts, watchlist/compare actions. */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var csrf = function () { var m = $('meta[name="csrf-token"]'); return m ? m.content : ""; };
  window.SMP = window.SMP || {};
  window.SMP.csrf = csrf;

  /* ---------- Toasts ---------- */
  var toastBox = $("#toasts");
  function toast(msg, kind) {
    if (!toastBox) return;
    var t = document.createElement("div");
    t.className = "toast" + (kind === "warn" ? " warn" : "");
    t.setAttribute("role", "status");
    t.textContent = msg;
    toastBox.appendChild(t);
    setTimeout(function () { t.classList.add("out"); setTimeout(function () { t.remove(); }, 320); }, 3200);
  }
  window.SMP.toast = toast;

  /* ---------- Sidebar ---------- */
  var app = $(".app");
  var STORE = "smp.sidebar";
  try { if (app && localStorage.getItem(STORE) === "collapsed") app.classList.add("is-collapsed"); } catch (e) {}
  var toggle = $("[data-side-toggle]");
  if (toggle) toggle.addEventListener("click", function () {
    app.classList.toggle("is-collapsed");
    try { localStorage.setItem(STORE, app.classList.contains("is-collapsed") ? "collapsed" : "open"); } catch (e) {}
    setTimeout(placeIndicator, 380);
  });
  var menuBtn = $("[data-menu-btn]");
  if (menuBtn) menuBtn.addEventListener("click", function () { app.classList.toggle("nav-open"); });
  var scrim = $(".scrim");
  if (scrim) scrim.addEventListener("click", function () { app.classList.remove("nav-open"); });

  // Sliding active indicator
  var indicator = $(".nav-indicator");
  function placeIndicator() {
    var active = $(".nav-link.is-active");
    if (!indicator || !active) return;
    var nav = active.closest(".nav");
    indicator.style.height = active.offsetHeight + "px";
    indicator.style.transform = "translateY(" + (active.offsetTop) + "px)";
    indicator.classList.add("ready");
  }
  placeIndicator();
  window.addEventListener("resize", placeIndicator);

  /* ---------- User menu ---------- */
  var um = $(".user-menu");
  if (um) {
    $(".avatar-btn", um).addEventListener("click", function (e) { e.stopPropagation(); um.classList.toggle("is-open"); });
    document.addEventListener("click", function () { um.classList.remove("is-open"); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") um.classList.remove("is-open"); });
  }

  /* ---------- Page transitions ---------- */
  var reduce = window.Motion && window.Motion.reduce;
  document.addEventListener("click", function (e) {
    if (reduce || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest("a[href]");
    if (!a || a.target === "_blank" || a.hasAttribute("download") || a.hasAttribute("data-no-transition")) return;
    var url;
    try { url = new URL(a.href, location.href); } catch (err) { return; }
    if (url.origin !== location.origin || (url.pathname === location.pathname && url.search === location.search) || url.pathname.indexOf("/admin/") === 0) return;
    e.preventDefault();
    document.body.classList.add("is-leaving");
    setTimeout(function () { location.href = a.href; }, 150);
  });
  window.addEventListener("pageshow", function () { document.body.classList.remove("is-leaving"); });

  /* ---------- Watchlist & compare buttons (event delegation) ---------- */
  function post(url) {
    return fetch(url, { method: "POST", headers: { "X-CSRFToken": csrf(), "X-Requested-With": "fetch", "Accept": "application/json" }, credentials: "same-origin" });
  }
  function setPressed(selector, id, on) {
    $$(selector + '[data-id="' + id + '"]').forEach(function (b) {
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.classList.remove("pop"); void b.offsetWidth; b.classList.add("pop");
    });
  }
  function updateWatchCount(n) {
    var c = $("[data-watch-count]");
    if (!c) return;
    c.textContent = n; c.style.display = n ? "" : "none";
  }

  /* compare drawer */
  var drawer = $("#compare-drawer");
  function renderDrawer(items) {
    if (!drawer) return;
    var chips = $(".drawer-chips", drawer);
    chips.innerHTML = "";
    items.forEach(function (it) {
      var c = document.createElement("span");
      c.className = "drawer-chip";
      var label = document.createElement("span"); label.textContent = it.name;
      var btn = document.createElement("button");
      btn.type = "button"; btn.setAttribute("aria-label", "Remove " + it.name + " from comparison");
      btn.setAttribute("data-compare-remove", it.id); btn.textContent = "×";
      c.appendChild(label); c.appendChild(btn); chips.appendChild(c);
    });
    var go = $("[data-compare-go]", drawer);
    if (go) go.textContent = "Compare (" + items.length + ")";
    drawer.classList.toggle("is-open", items.length > 0);
    drawer.setAttribute("aria-hidden", items.length ? "false" : "true");
    $$("[data-compare]").forEach(function (b) {
      var on = items.some(function (i) { return String(i.id) === b.dataset.id; });
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }
  if (drawer) {
    var initial = $("#compare-initial");
    if (initial) { try { renderDrawer(JSON.parse(initial.textContent)); } catch (e) {} }
    drawer.addEventListener("click", function (e) {
      var rm = e.target.closest("[data-compare-remove]");
      if (rm) { toggleCompare(rm.getAttribute("data-compare-remove")); }
      if (e.target.closest("[data-compare-clear]")) {
        post(drawer.dataset.clearUrl).then(function (r) { return r.json(); }).then(function (d) { renderDrawer(d.items); if (d.items.length === 0 && location.pathname.indexOf("/compare") === 0) location.reload(); });
      }
    });
  }
  function toggleCompare(id) {
    return post("/compare/toggle/" + id + "/").then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); }).then(function (res) {
      if (res.d.error) toast(res.d.error, "warn");
      renderDrawer(res.d.items || []);
      if (location.pathname.indexOf("/compare") === 0 && res.ok) location.reload();
    }).catch(function () { toast("Couldn't update comparison. Is the server still running?", "warn"); });
  }

  document.addEventListener("click", function (e) {
    var w = e.target.closest("[data-watch]");
    if (w) {
      e.preventDefault(); e.stopPropagation();
      var id = w.dataset.id;
      post("/watchlist/toggle/" + id + "/").then(function (r) { return r.json(); }).then(function (d) {
        setPressed("[data-watch]", id, d.watching);
        updateWatchCount(d.count);
        toast((d.watching ? "Added to watchlist: " : "Removed from watchlist: ") + d.product);
        var row = w.closest("[data-watch-row]");
        if (row && !d.watching) { row.style.transition = "opacity .25s, transform .25s"; row.style.opacity = 0; row.style.transform = "scale(.97)"; setTimeout(function () { row.remove(); if (!$("[data-watch-row]")) location.reload(); }, 260); }
      }).catch(function () { toast("Couldn't update watchlist.", "warn"); });
      return;
    }
    var c = e.target.closest("[data-compare]");
    if (c) { e.preventDefault(); e.stopPropagation(); toggleCompare(c.dataset.id); }
  });

  /* ---------- Entrance choreography ---------- */
  document.addEventListener("DOMContentLoaded", function () {
    if (!window.Motion) return;
    Motion.observe(document);
    Motion.counters(document);
    Motion.progress(document);
    var head = $(".page-head");
    if (head) Motion.reveal([head], { y: 10, duration: .5 });
  });
})();
