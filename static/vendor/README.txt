Optional vendored libraries (setup scripts download these when online):
  gsap.min.js          https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js
  chart.umd.min.js     https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js
If absent, pages fall back to the CDN, and if that is offline too, to CSS/JS animations
and plain bar charts. Login, filters, and calculations never depend on them.
