/* Import cost calculator. The Python API is authoritative; if it can't be
   reached, a local JavaScript mirror of the same formulas is used. */
(function () {
  "use strict";
  var M = window.Motion;
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector("[data-calc-form]");
    if (!form) return;
    var out = document.querySelector("[data-calc-out]");
    var errBox = document.querySelector("[data-calc-errors]");
    var note = document.querySelector("[data-calc-offline]");
    var timer = null, controller = null;
    var FIELDS = ["unit_price_cny", "fx_rate", "quantity", "shipping_npr", "insurance_handling_npr", "duty_rate_pct", "other_expenses_npr", "selling_price_npr"];

    function num(v) { if (v === null || v === undefined || String(v).trim() === "") return null; var n = Number(String(v).replace(/,/g, "")); return isFinite(n) ? n : null; }
    function localCalc(p) {
      var errors = [], price = num(p.unit_price_cny), fx = num(p.fx_rate), qty = num(p.quantity);
      var ship = num(p.shipping_npr) || 0, hand = num(p.insurance_handling_npr) || 0, duty = num(p.duty_rate_pct) || 0, other = num(p.other_expenses_npr) || 0, sell = num(p.selling_price_npr);
      if (price === null || price < 0) errors.push("Supplier price must be zero or more.");
      if (fx === null || fx <= 0) errors.push("Exchange rate must be greater than zero.");
      if (qty === null || qty < 1 || Math.floor(qty) !== qty) errors.push("Quantity must be a whole number of at least 1.");
      [["Shipping", ship], ["Insurance and handling", hand], ["Duty rate", duty], ["Other expenses", other]].forEach(function (x) { if (x[1] < 0) errors.push(x[0] + " cannot be negative."); });
      if (sell !== null && sell < 0) errors.push("Selling price cannot be negative.");
      if (errors.length) return { valid: false, errors: errors };
      var purchase = price * fx * qty, cif = purchase + ship + hand, duties = cif * duty / 100, imp = ship + hand + duties + other, landed = purchase + imp, unit = landed / qty;
      var r = { valid: true, errors: [], unit_price_npr: price * fx, purchase_cost: purchase, shipping: ship, insurance_handling: hand, duties_taxes: duties, other_expenses: other, import_expenses_total: imp, landed_total: landed, landed_per_unit: unit, quantity: qty };
      if (sell !== null && sell > 0) { var pu = sell - unit; r.profit_per_unit = pu; r.profit_per_order = pu * qty; r.margin_pct = pu / sell * 100; r.revenue_per_order = sell * qty; }
      return r;
    }

    function collect() { var p = {}; FIELDS.forEach(function (f) { var el = form.elements[f]; p[f] = el ? el.value : ""; }); return p; }
    function show(r, offline) {
      if (note) note.hidden = !offline;
      if (errBox) {
        if (!r.valid) { errBox.hidden = false; errBox.innerHTML = "<strong>Check your inputs</strong><ul>" + r.errors.map(function (e) { return "<li>" + e.replace(/</g, "&lt;") + "</li>"; }).join("") + "</ul>"; }
        else errBox.hidden = true;
      }
      out.classList.toggle("is-stale", !r.valid);
      out.querySelectorAll("[data-out]").forEach(function (el) {
        var key = el.dataset.out, v = r.valid ? r[key] : null;
        var n = (v === null || v === undefined) ? null : Number(v);
        if (n === null || isNaN(n)) { el.textContent = "—"; el.dataset.val = ""; return; }
        var kind = el.dataset.kind || "npr", prev = parseFloat(el.dataset.val);
        if (isNaN(prev)) prev = 0;
        M.tween(prev, n, 350, function (x) { el.textContent = kind === "pct" ? x.toFixed(1) + "%" : (kind === "npr2" ? M.npr(x, 2) : M.npr(Math.round(x))); });
        el.dataset.val = n;
        if (el.dataset.tone) el.classList.toggle("neg", n < 0);
      });
      // composition bar
      if (r.valid && r.landed_total > 0) {
        var parts = [r.purchase_cost, r.shipping + r.insurance_handling, r.duties_taxes, r.other_expenses];
        out.querySelectorAll("[data-seg]").forEach(function (s, i) { s.style.width = (parts[i] / r.landed_total * 100) + "%"; });
      }
    }
    function run() {
      var p = collect();
      if (controller) controller.abort();
      controller = "AbortController" in window ? new AbortController() : null;
      var qs = new URLSearchParams(p).toString();
      history.replaceState(null, "", location.pathname + "?" + qs);
      fetch(form.dataset.api + "?" + qs, { credentials: "same-origin", headers: { "Accept": "application/json" }, signal: controller ? controller.signal : undefined })
        .then(function (r) { if (!r.ok) throw new Error("bad"); return r.json(); })
        .then(function (d) { ["unit_price_npr", "purchase_cost", "shipping", "insurance_handling", "duties_taxes", "other_expenses", "import_expenses_total", "landed_total", "landed_per_unit", "profit_per_unit", "profit_per_order", "margin_pct", "revenue_per_order"].forEach(function (k) { if (d[k] !== null && d[k] !== undefined) d[k] = Number(d[k]); }); d.shipping = d.shipping || 0; d.insurance_handling = d.insurance_handling || 0; d.duties_taxes = d.duties_taxes || 0; d.other_expenses = d.other_expenses || 0; show(d, false); })
        .catch(function (err) { if (err && err.name === "AbortError") return; show(localCalc(p), true); });
    }
    form.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(run, 140); });
    form.addEventListener("submit", function (e) { e.preventDefault(); run(); });
    var resetBtn = document.querySelector("[data-calc-reset]");
    if (resetBtn) resetBtn.addEventListener("click", function (e) {
      e.preventDefault();
      FIELDS.forEach(function (f) { var el = form.elements[f]; if (el && el.dataset.default !== undefined) el.value = el.dataset.default; });
      run();
    });
    run();
  });
})();
