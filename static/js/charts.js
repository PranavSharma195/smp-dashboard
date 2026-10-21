/* Dashboard charts. Uses Chart.js when available; otherwise renders simple
   accessible bar fallbacks so the page never shows an empty hole. */
(function () {
  "use strict";
  var PALETTE = ["#0d6b5e", "#e39a2d", "#3949a3", "#b3261e", "#6a4c93", "#4d6b2f", "#a34a5f", "#c9772a", "#2fa28d", "#6d7fd6", "#8a8a99", "#d9808f"];
  var M = window.Motion;

  function fallbackBars(box, labels, series) {
    box.classList.remove("chart-box"); box.style.height = "auto";
    var max = 0; series.forEach(function (s) { s.values.forEach(function (v) { if (v > max) max = v; }); });
    var html = '<div class="fallback-bars">';
    labels.forEach(function (l, i) {
      html += '<div class="fb-row"><span>' + l.replace(/</g, "&lt;") + "</span>";
      series.forEach(function (s, si) {
        var w = max ? (s.values[i] / max * 100) : 0;
        html += '<div class="fb-track" title="' + s.name + ": " + s.values[i] + '"><div class="fb-fill ' + (si ? "alt" : "") + '" data-w="' + w + '"></div></div>';
      });
      html += "</div>";
    });
    box.innerHTML = html + "</div>";
    requestAnimationFrame(function () { requestAnimationFrame(function () { box.querySelectorAll(".fb-fill").forEach(function (f) { f.style.width = f.dataset.w + "%"; }); }); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var node = document.getElementById("chart-data");
    if (!node) return;
    var data = JSON.parse(node.textContent);
    var catBox = document.getElementById("chart-categories"), costBox = document.getElementById("chart-costs");
    var hasChart = typeof window.Chart !== "undefined";
    var reduce = M && M.reduce;

    if (catBox) {
      if (hasChart) {
        var canvas = catBox.querySelector("canvas");
        new window.Chart(canvas, {
          type: "doughnut",
          data: { labels: data.categories.labels, datasets: [{ data: data.categories.values, backgroundColor: PALETTE, borderColor: "#fffdf9", borderWidth: 3, hoverOffset: 8 }] },
          options: { responsive: true, maintainAspectRatio: false, cutout: "66%", animation: reduce ? false : { duration: 1100, easing: "easeOutQuart" }, plugins: { legend: { display: false } } }
        });
      } else {
        fallbackBars(catBox, data.categories.labels, [{ name: "Products", values: data.categories.values }]);
      }
    }
    if (costBox) {
      if (hasChart) {
        var c2 = costBox.querySelector("canvas");
        new window.Chart(c2, {
          type: "bar",
          data: {
            labels: data.costs.labels.map(function (l) { return l.length > 26 ? l.slice(0, 25) + "…" : l; }),
            datasets: [
              { label: "Landed cost per unit", data: data.costs.cost, backgroundColor: "#c9c0ab", borderRadius: 6 },
              { label: "Est. selling price per unit", data: data.costs.price, backgroundColor: "#0d6b5e", borderRadius: 6 }
            ]
          },
          options: {
            indexAxis: "y", responsive: true, maintainAspectRatio: false,
            animation: reduce ? false : { duration: 1000, easing: "easeOutQuart" },
            plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8, font: { size: 12 } } }, tooltip: { callbacks: { label: function (ctx) { return ctx.dataset.label + ": " + M.npr(ctx.parsed.x); } } } },
            scales: { x: { grid: { color: "rgba(29,35,48,.06)" }, ticks: { callback: function (v) { return v >= 1000 ? (v / 1000) + "k" : v; } } }, y: { grid: { display: false }, ticks: { font: { size: 12 } } } }
          }
        });
      } else {
        fallbackBars(costBox, data.costs.labels, [{ name: "Landed cost per unit", values: data.costs.cost }, { name: "Est. selling price per unit", values: data.costs.price }]);
      }
    }
  });
})();
