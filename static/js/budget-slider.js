/* Dual-thumb budget slider (NPR). Two stacked native range inputs gives free
   keyboard + touch support. Emits "budget:change" with {lo, hi}. */
(function () {
  "use strict";
  var M = window.Motion;

  function init(root) {
    var min = +root.dataset.min, max = +root.dataset.max, step = +root.dataset.step || 500;
    var lo = root.querySelector(".range-lo"), hi = root.querySelector(".range-hi");
    var fill = root.querySelector(".range-fill");
    var loOut = root.querySelector("[data-lo-out]"), hiOut = root.querySelector("[data-hi-out]");
    var loNum = root.querySelector("[data-lo-num]"), hiNum = root.querySelector("[data-hi-num]");
    var hidLo = root.querySelector("[data-lo-hidden]"), hidHi = root.querySelector("[data-hi-hidden]");
    var shown = { lo: +lo.value, hi: +hi.value };
    var timer = null;

    function clampPair(changed) {
      var a = +lo.value, b = +hi.value;
      if (a > b) { if (changed === "lo") { a = b; lo.value = a; } else { b = a; hi.value = b; } }
      return { lo: a, hi: b };
    }
    function paint(v) {
      var span = max - min;
      var l = (v.lo - min) / span * 100, h = (v.hi - min) / span * 100;
      fill.style.left = l + "%"; fill.style.width = Math.max(0, h - l) + "%";
      // keep the lower thumb reachable when both sit at the top end
      lo.style.zIndex = (v.lo > min + span * 0.5) ? 3 : 2; hi.style.zIndex = 2.5;
    }
    function animateOut(el, from, to) {
      if (!el) return;
      M.tween(from, to, 220, function (n) { el.textContent = M.npr(Math.round(n / step) * step); });
    }
    function sync(changed, fromNumber) {
      var v = clampPair(changed);
      paint(v);
      animateOut(loOut, shown.lo, v.lo); animateOut(hiOut, shown.hi, v.hi);
      shown = v;
      if (!fromNumber) { if (loNum) loNum.value = v.lo; if (hiNum) hiNum.value = v.hi; }
      if (hidLo) hidLo.value = v.lo; if (hidHi) hidHi.value = v.hi;
      root.querySelectorAll("[data-preset]").forEach(function (b) {
        b.classList.toggle("is-on", +b.dataset.lo === v.lo && +b.dataset.hi === v.hi);
      });
      clearTimeout(timer);
      timer = setTimeout(function () {
        root.dispatchEvent(new CustomEvent("budget:change", { bubbles: true, detail: v }));
      }, 140);
    }
    function set(a, b) {
      a = Math.max(min, Math.min(max, Number(a) || 0)); b = Math.max(min, Math.min(max, isNaN(Number(b)) ? max : Number(b)));
      if (a > b) { var t = a; a = b; b = t; }
      lo.value = a; hi.value = b; sync("lo");
    }
    lo.addEventListener("input", function () { sync("lo"); });
    hi.addEventListener("input", function () { sync("hi"); });
    if (loNum) loNum.addEventListener("change", function () { set(loNum.value, hi.value); });
    if (hiNum) hiNum.addEventListener("change", function () { set(lo.value, hiNum.value); });
    root.querySelectorAll("[data-preset]").forEach(function (b) {
      b.addEventListener("click", function () { set(b.dataset.lo, b.dataset.hi); });
    });
    root.setBudget = set;
    root.getBudget = function () { return { lo: +lo.value, hi: +hi.value, min: min, max: max }; };
    // initial paint without firing a change event
    paint(shown);
    if (loOut) loOut.textContent = M.npr(shown.lo); if (hiOut) hiOut.textContent = M.npr(shown.hi);
    root.querySelectorAll("[data-preset]").forEach(function (b) { b.classList.toggle("is-on", +b.dataset.lo === shown.lo && +b.dataset.hi === shown.hi); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-budget]").forEach(init);
  });
})();
