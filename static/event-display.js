/* Home-page hero: a simulated collision seen end-on, as in a detector event display.
   Charged particles curl in the solenoid's magnetic field: high-momentum tracks are nearly
   straight, low-momentum ones spiral. A new event is generated on every visit. */
(function () {
  "use strict";
  var svg = document.getElementById("event-display");
  if (!svg) return;
  var NS = "http://www.w3.org/2000/svg";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var COLORS = { hi: "#FFFFFF", mid: "#ABF5F9", lo: "#121256" };  // white, heritage blue, blueberry

  function rng(seed) {             // mulberry32
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  var seed = (Math.random() * 1e9) | 0;

  function el(name, attrs, parent) {
    var e = document.createElementNS(NS, name);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  function draw(animate) {
    var rand = rng(seed);
    var gauss = function () { return Math.sqrt(-2 * Math.log(rand() + 1e-9)) * Math.cos(2 * Math.PI * rand()); };
    var w = svg.clientWidth || 1200, h = svg.clientHeight || 600;
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    var narrow = w < 760;
    var cx = narrow ? w * 0.78 : w * 0.7, cy = h * 0.5;
    var R = Math.min(Math.max(h * 0.46, 180), narrow ? w * 0.75 : w * 0.34); // tracker outer radius
    var layers = [0.12, 0.2, 0.3, 0.42, 0.56, 0.7, 0.84, 1].map(function (f) { return f * R; });

    var gLayers = el("g", {}, svg);
    layers.forEach(function (r, i) {
      el("circle", { cx: cx, cy: cy, r: r, "class": "ed-layer", "stroke-width": i === layers.length - 1 ? 1.5 : 1 }, gLayers);
    });
    // calorimeter segments
    var calIn = R * 1.06, calOut = R * 1.32, nSeg = 64;
    var gCal = el("g", {}, svg);
    for (var s = 0; s < nSeg; s++) {
      var a = (s / nSeg) * 2 * Math.PI;
      el("line", {
        x1: cx + calIn * Math.cos(a), y1: cy + calIn * Math.sin(a),
        x2: cx + calOut * Math.cos(a), y2: cy + calOut * Math.sin(a), "class": "ed-layer"
      }, gCal);
    }
    el("circle", { cx: cx, cy: cy, r: calIn, "class": "ed-layer" }, gCal);
    el("circle", { cx: cx, cy: cy, r: calOut, "class": "ed-layer" }, gCal);

    // Build the event: two back-to-back jets plus soft underlying-event tracks.
    var jetPhi = rand() * 2 * Math.PI;
    var tracks = [];
    [jetPhi, jetPhi + Math.PI + gauss() * 0.15].forEach(function (phi) {
      var n = 5 + Math.floor(rand() * 4);
      for (var i = 0; i < n; i++) tracks.push({ phi: phi + gauss() * 0.16, pt: 6 + rand() * 40 });
    });
    var soft = narrow ? 10 : 16;
    for (var j = 0; j < soft; j++) tracks.push({ phi: rand() * 2 * Math.PI, pt: 0.35 + Math.pow(rand(), 2) * 4 });

    var gTracks = el("g", {}, svg), gHits = el("g", {}, svg), gCalHits = el("g", {}, svg);
    var ds = R / 160;
    tracks.forEach(function (t, idx) {
      var q = rand() < 0.5 ? -1 : 1;
      var k = q * 0.9 / (t.pt * R) * 1;      // curvature (1/px), scaled to the detector size
      var x = cx, y = cy, th = t.phi, len = 0;
      var pts = [[x, y]], lastR = 0, hits = [];
      var maxLen = R * 6;
      while (len < maxLen) {
        th += k * ds;
        x += Math.cos(th) * ds; y += Math.sin(th) * ds; len += ds;
        if (t.pt < 1.2) k *= 1.0035;          // energy loss: soft tracks spiral inwards
        pts.push([x, y]);
        var r = Math.hypot(x - cx, y - cy);
        for (var L = 0; L < layers.length; L++) {
          if ((lastR < layers[L]) !== (r < layers[L])) hits.push([x, y]);
        }
        lastR = r;
        if (r > R) break;
        if (Math.abs(k) * R > 60) break;       // tight spiral: stop
      }
      var reached = lastR > R;
      var color = t.pt > 6 ? COLORS.hi : t.pt > 1.2 ? COLORS.mid : COLORS.lo;
      var d = "M" + pts.map(function (p) { return p[0].toFixed(1) + " " + p[1].toFixed(1); }).join("L");
      var path = el("path", {
        d: d, "class": "ed-track", stroke: color,
        "stroke-width": t.pt > 6 ? 2.2 : 1.5, opacity: t.pt > 6 ? 0.95 : t.pt > 1.2 ? 0.8 : 0.6
      }, gTracks);
      var delay = (t.pt > 6 ? 0 : 0.25) + (idx % 7) * 0.04;
      if (animate) {
        var L2 = path.getTotalLength();
        path.style.strokeDasharray = L2;
        path.style.strokeDashoffset = L2;
        path.style.transition = "stroke-dashoffset " + (1.1 + rand() * 0.6).toFixed(2) + "s cubic-bezier(.2,.7,.3,1) " + delay.toFixed(2) + "s";
      }
      if (t.pt > 1.2) hits.forEach(function (p) {
        var c = el("circle", { cx: p[0].toFixed(1), cy: p[1].toFixed(1), r: 1.6, fill: "#fff", "class": "ed-hit" }, gHits);
        if (animate) { c.style.opacity = 0; c.style.transition = "opacity .4s ease " + (delay + 0.9).toFixed(2) + "s"; }
      });
      if (reached) {
        var a = Math.atan2(y - cy, x - cx);
        var depth = Math.min(calOut - calIn, (calOut - calIn) * (0.25 + t.pt / 30));
        var half = Math.PI / nSeg * 0.8;
        var r1 = calIn + 2, r2 = calIn + 2 + depth;
        var poly = [
          [r1, a - half], [r2, a - half], [r2, a + half], [r1, a + half]
        ].map(function (p) { return (cx + p[0] * Math.cos(p[1])).toFixed(1) + "," + (cy + p[0] * Math.sin(p[1])).toFixed(1); }).join(" ");
        var cell = el("polygon", { points: poly, fill: "#ABF5F9", opacity: 0.5 }, gCalHits);
        if (animate) { cell.style.opacity = 0; cell.style.transition = "opacity .5s ease " + (delay + 1.3).toFixed(2) + "s"; }
      }
    });
    el("circle", { cx: cx, cy: cy, r: 3.5, fill: "#fff" }, svg);

    if (animate) {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          gTracks.querySelectorAll("path").forEach(function (p) { p.style.strokeDashoffset = 0; });
          gHits.querySelectorAll("circle").forEach(function (c) { c.style.opacity = ""; });
          gCalHits.querySelectorAll("polygon").forEach(function (c) { c.style.opacity = ""; });
        });
      });
    }
  }

  draw(!reduce);
  var timer;
  window.addEventListener("resize", function () {
    clearTimeout(timer);
    timer = setTimeout(function () { draw(false); }, 150);
  });
})();
