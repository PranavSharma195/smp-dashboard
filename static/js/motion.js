/* Motion helpers. Uses GSAP when it loaded; otherwise falls back to the Web
   Animations API / requestAnimationFrame. Honors prefers-reduced-motion. */
(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hasGsap = function () { return typeof window.gsap !== "undefined"; };

  function groupNepali(s) {
    if (s.length <= 3) return s;
    var head = s.slice(0, -3), tail = s.slice(-3), parts = [];
    while (head.length > 2) { parts.unshift(head.slice(-2)); head = head.slice(0, -2); }
    if (head) parts.unshift(head);
    return parts.join(",") + "," + tail;
  }
  function npr(n, decimals) {
    if (n === null || n === undefined || isNaN(n)) return "—";
    var neg = n < 0, v = Math.abs(Number(n)).toFixed(decimals || 0).split(".");
    return (neg ? "-" : "") + "Rs. " + groupNepali(v[0]) + (v[1] ? "." + v[1] : "");
  }
  function fmt(n, kind) {
    if (kind === "npr") return npr(Math.round(n));
    if (kind === "pct") return n.toFixed(1) + "%";
    if (kind === "dec1") return n.toFixed(1);
    return String(Math.round(n));
  }

  function tween(from, to, ms, onUpdate, done) {
    if (reduce || ms <= 0) { onUpdate(to); if (done) done(); return; }
    var start = null;
    function step(ts) {
      if (start === null) start = ts;
      var t = Math.min(1, (ts - start) / ms), e = 1 - Math.pow(1 - t, 3);
      onUpdate(from + (to - from) * e);
      if (t < 1) requestAnimationFrame(step); else if (done) done();
    }
    requestAnimationFrame(step);
  }

  var Motion = {
    reduce: reduce,
    npr: npr,
    fmt: fmt,
    tween: tween,

    reveal: function (targets, opts) {
      var els = Array.prototype.slice.call(targets || []);
      if (!els.length) return;
      opts = opts || {};
      if (reduce) { els.forEach(function (e) { e.style.opacity = 1; }); return; }
      var y = opts.y === undefined ? 16 : opts.y, dur = opts.duration || 0.55, st = opts.stagger === undefined ? 0.06 : opts.stagger, delay = opts.delay || 0;
      if (hasGsap()) {
        window.gsap.fromTo(els, { opacity: 0, y: y }, { opacity: 1, y: 0, duration: dur, delay: delay, stagger: st, ease: "power3.out", clearProps: "transform" });
      } else {
        els.forEach(function (el, i) {
          el.style.opacity = 1;
          if (el.animate) el.animate([{ opacity: 0, transform: "translateY(" + y + "px)" }, { opacity: 1, transform: "none" }],
            { duration: dur * 1000, delay: (delay + i * st) * 1000, easing: "cubic-bezier(.2,.7,.2,1)", fill: "backwards" });
        });
      }
    },

    // Reveal [data-reveal] elements as they scroll into view.
    observe: function (root) {
      var els = Array.prototype.slice.call((root || document).querySelectorAll("[data-reveal]"));
      if (!els.length) return;
      if (reduce || !("IntersectionObserver" in window)) { els.forEach(function (e) { e.style.opacity = 1; }); return; }
      var pending = [], timer = null;
      var flush = function () { Motion.reveal(pending, { stagger: 0.07 }); pending = []; timer = null; };
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) { pending.push(en.target); io.unobserve(en.target); }
        });
        if (pending.length && !timer) timer = setTimeout(flush, 30);
      }, { threshold: 0.08 });
      els.forEach(function (e) { io.observe(e); });
    },

    count: function (el, to, kind, ms) {
      kind = kind || el.dataset.format || "int";
      tween(0, to, ms === undefined ? 1100 : ms, function (v) { el.textContent = fmt(v, kind); });
    },

    counters: function (root) {
      (root || document).querySelectorAll("[data-count]").forEach(function (el) {
        var to = parseFloat(el.dataset.count);
        if (isNaN(to)) return;
        Motion.count(el, to);
      });
    },

    // Animate bars (width) and rings (stroke-dasharray) from 0 to their target.
    progress: function (root) {
      var scope = root || document;
      var bars = scope.querySelectorAll("[data-bar]");
      var rings = scope.querySelectorAll("[data-ring]");
      bars.forEach(function (b) {
        var w = parseFloat(b.dataset.bar) || 0;
        if (reduce) { b.style.width = w + "%"; return; }
        b.style.width = "0%";
        requestAnimationFrame(function () { requestAnimationFrame(function () { b.style.width = w + "%"; }); });
      });
      rings.forEach(function (r) {
        var v = parseFloat(r.dataset.ring) || 0;
        if (reduce) { r.style.strokeDasharray = v + " 100"; return; }
        r.style.strokeDasharray = "0 100";
        requestAnimationFrame(function () { requestAnimationFrame(function () { r.style.strokeDasharray = v + " 100"; }); });
      });
    }
  };
  window.Motion = Motion;
})();
