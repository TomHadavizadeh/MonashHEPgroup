/* Home-page hero: a simulated collision seen end-on, as in a detector event display.
   The beams are shown in perspective along an axis tilted into the screen: one bunch flies
   into the page from the bottom left (shrinking as it moves away from the viewer), the other
   comes out of the page from the top right (growing as it approaches). Both are drawn as
   glowing spheres.
   They collide at the centre of the detector. Charged particles then curl outwards in the solenoid's magnetic
   field: high-momentum tracks are nearly straight, low-momentum ones spiral.
   A new event is generated on every visit, and the "New collision" button replays it. */
(function () {
  "use strict";
  var svg = document.getElementById("event-display");
  if (!svg) return;
  var hero = svg.closest(".hero");
  // Bunches and flash go on a layer above the text glow (but below the text) so they read clearly.
  var top = document.getElementById("event-beams") || svg;
  var NS = "http://www.w3.org/2000/svg";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  // Monash palette: white, heritage blue, blueberry
  var COLORS = { hi: "#FFFFFF", mid: "#ABF5F9", lo: "#121256" };
  var BEAM_MS = 1100;          // time for the bunches to reach the collision point
  var raf = null, timers = [], anims = [];
  var canAnimate = typeof Element !== "undefined" && "animate" in Element.prototype;
  // Web Animations with fill "both" keep each element hidden until its own start time.
  function play(node, frames, opts) {
    anims.push(node.animate(frames, Object.assign({ fill: "both" }, opts)));
  }

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
  function later(fn, ms) { timers.push(setTimeout(fn, ms)); }
  function stop() {
    if (raf) cancelAnimationFrame(raf);
    raf = null;
    timers.forEach(clearTimeout); timers = [];
    anims.forEach(function (a) { try { a.cancel(); } catch (e) { /* ignore */ } }); anims = [];
  }

  function draw(animate) {
    stop();
    var rand = rng(seed);
    var gauss = function () { return Math.sqrt(-2 * Math.log(rand() + 1e-9)) * Math.cos(2 * Math.PI * rand()); };
    var w = svg.clientWidth || 1200, h = svg.clientHeight || 600;
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    if (top !== svg) {
      top.setAttribute("viewBox", "0 0 " + w + " " + h);
      while (top.firstChild) top.removeChild(top.firstChild);
    }

    // Wide screens: detector on the left, text on the right. Narrow screens: centred.
    var wide = w >= 760;
    var cx = wide ? w * 0.3 : w / 2, cy = h / 2;
    var R = Math.min(h * 0.47, wide ? w * 0.3 : w * 0.46);  // tracker outer radius
    var layers = [0.12, 0.2, 0.3, 0.42, 0.56, 0.7, 0.84, 1].map(function (f) { return f * R; });

    var defs = el("defs", {}, top);
    // Shaded sphere for the beam bunches (highlight towards the top left) and its halo.
    var gS = el("radialGradient", { id: "ed-sphere", cx: ".38", cy: ".35", r: ".68", fx: ".32", fy: ".28" }, defs);
    el("stop", { offset: "0", "stop-color": "#FFFFFF" }, gS);
    el("stop", { offset: ".45", "stop-color": "#ABF5F9" }, gS);
    el("stop", { offset: "1", "stop-color": "#4FA3D1" }, gS);
    var gH = el("radialGradient", { id: "ed-halo" }, defs);
    el("stop", { offset: ".45", "stop-color": "#ABF5F9", "stop-opacity": ".45" }, gH);
    el("stop", { offset: "1", "stop-color": "#ABF5F9", "stop-opacity": "0" }, gH);
    var gF = el("radialGradient", { id: "ed-flash" }, defs);
    el("stop", { offset: "0", "stop-color": "#fff", "stop-opacity": "1" }, gF);
    el("stop", { offset: ".35", "stop-color": "#ABF5F9", "stop-opacity": ".7" }, gF);
    el("stop", { offset: "1", "stop-color": "#ABF5F9", "stop-opacity": "0" }, gF);

    // Detector: tracker layers and calorimeter segments (the beam pipe points out of the screen).
    var gLayers = el("g", {}, svg);
    layers.forEach(function (r, i) {
      el("circle", { cx: cx, cy: cy, r: r, "class": "ed-layer", "stroke-width": i === layers.length - 1 ? 1.5 : 1 }, gLayers);
    });
    var calIn = R * 1.06, calOut = R * 1.32, nSeg = 72;
    var gCal = el("g", {}, svg);
    for (var s = 0; s < nSeg; s++) {
      var a0 = (s / nSeg) * 2 * Math.PI;
      el("line", {
        x1: cx + calIn * Math.cos(a0), y1: cy + calIn * Math.sin(a0),
        x2: cx + calOut * Math.cos(a0), y2: cy + calOut * Math.sin(a0), "class": "ed-layer"
      }, gCal);
    }
    el("circle", { cx: cx, cy: cy, r: calIn, "class": "ed-layer" }, gCal);
    el("circle", { cx: cx, cy: cy, r: calOut, "class": "ed-layer" }, gCal);

    // The event: two back-to-back jets plus soft tracks spraying in every direction.
    var jetPhi = rand() * 2 * Math.PI;
    var tracks = [];
    [jetPhi, jetPhi + Math.PI + gauss() * 0.15].forEach(function (phi) {
      var n = 6 + Math.floor(rand() * 4);
      for (var i = 0; i < n; i++) tracks.push({ phi: phi + gauss() * 0.17, pt: 6 + rand() * 40 });
    });
    var soft = w < 760 ? 14 : 22;
    for (var j = 0; j < soft; j++) tracks.push({ phi: (j + rand()) / soft * 2 * Math.PI, pt: 0.4 + Math.pow(rand(), 2) * 4.5 });

    var gTracks = el("g", {}, svg), gHits = el("g", {}, svg), gCalHits = el("g", {}, svg);
    var ds = R / 160;
    if (!canAnimate) animate = false;
    var t0 = animate ? BEAM_MS : 0;                 // tracks start when the bunches collide (ms)
    tracks.forEach(function (t, idx) {
      var q = rand() < 0.5 ? -1 : 1;
      var k = q * 0.9 / (t.pt * R);
      var x = cx, y = cy, th = t.phi, len = 0;
      var pts = [[x, y]], lastR = 0, hits = [];
      while (len < R * 6) {
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
        if (Math.abs(k) * R > 60) break;
      }
      var reached = lastR > R;
      var color = t.pt > 6 ? COLORS.hi : t.pt > 1.2 ? COLORS.mid : COLORS.lo;
      var d = "M" + pts.map(function (p) { return p[0].toFixed(1) + " " + p[1].toFixed(1); }).join("L");
      var path = el("path", {
        d: d, "class": "ed-track", stroke: color,
        "stroke-width": t.pt > 6 ? 2.2 : 1.5, opacity: t.pt > 6 ? 0.95 : t.pt > 1.2 ? 0.8 : 0.6
      }, gTracks);
      var delay = t0 + (t.pt > 6 ? 0 : 120) + (idx % 7) * 30;
      if (animate) {
        var L2 = path.getTotalLength();
        path.style.strokeDasharray = L2 + "px";
        play(path, [{ strokeDashoffset: L2 + "px" }, { strokeDashoffset: "0px" }],
             { duration: 900 + rand() * 600, delay: delay, easing: "cubic-bezier(.15,.75,.3,1)" });
      }
      if (t.pt > 1.2) hits.forEach(function (p) {
        var c = el("circle", { cx: p[0].toFixed(1), cy: p[1].toFixed(1), r: 1.6, fill: "#fff" }, gHits);
        if (animate) play(c, [{ opacity: 0 }, { opacity: 1 }], { duration: 400, delay: delay + 700 });
      });
      if (reached) {
        var a = Math.atan2(y - cy, x - cx);
        var depth = Math.min(calOut - calIn, (calOut - calIn) * (0.25 + t.pt / 30));
        var half = Math.PI / nSeg * 0.8;
        var r1 = calIn + 2, r2 = calIn + 2 + depth;
        var poly = [[r1, a - half], [r2, a - half], [r2, a + half], [r1, a + half]]
          .map(function (p) { return (cx + p[0] * Math.cos(p[1])).toFixed(1) + "," + (cy + p[0] * Math.sin(p[1])).toFixed(1); }).join(" ");
        var cell = el("polygon", { points: poly, fill: "#ABF5F9", opacity: 0.5 }, gCalHits);
        if (animate) play(cell, [{ opacity: 0 }, { opacity: 0.5 }], { duration: 500, delay: delay + 1100 });
      }
    });

    // Vertex glow (stays) and collision flash (animated).
    el("circle", { cx: cx, cy: cy, r: 3.5, fill: "#fff" }, svg);
    var flash = el("circle", { cx: cx, cy: cy, r: R * 0.22, fill: "url(#ed-flash)", opacity: 0 }, top);
    flash.style.transformBox = "fill-box";
    flash.style.transformOrigin = "center";

    if (animate) play(flash, [
      { opacity: 0, transform: "scale(.1)" },
      { opacity: 1, transform: "scale(.7)", offset: 0.25 },
      { opacity: 0, transform: "scale(1.15)" }
    ], { duration: 1100, delay: BEAM_MS, easing: "ease-out" });

    // Incoming bunches, in perspective. The beam axis is a straight line through the vertex,
    // tilted so its near end is at the bottom left and it recedes to a vanishing point at the
    // top right. A point on the axis at depth z (z = 1 is the collision plane) projects to
    //   screen = vertex + O · (z − 1) / z      and appears with size ∝ 1 / z.
    var O = { x: 0.75 * R, y: -0.75 * R };             // vertex → vanishing point
    function at(z) { var f = (z - 1) / z; return { x: cx + O.x * f, y: cy + O.y * f }; }
    var rv = Math.max(10, R * 0.055);                  // bunch radius at the collision plane
    var Z_NEAR = 0.45, Z_FAR = 8;                      // start depths: bottom left / top right

    // Faint beam line along the axis, drawn behind the text glow.
    var nearEnd = at(0.25), farEnd = at(60);
    var gB = el("linearGradient", { id: "ed-beamline", gradientUnits: "userSpaceOnUse",
      x1: nearEnd.x, y1: nearEnd.y, x2: farEnd.x, y2: farEnd.y }, defs);
    el("stop", { offset: "0", "stop-color": "#fff", "stop-opacity": ".35" }, gB);
    el("stop", { offset: "1", "stop-color": "#fff", "stop-opacity": ".05" }, gB);
    var beamLine = el("line", { x1: nearEnd.x, y1: nearEnd.y, x2: farEnd.x, y2: farEnd.y,
      stroke: "url(#ed-beamline)", "stroke-width": 1.2 }, svg);
    if (animate) play(beamLine, [{ opacity: 0 }, { opacity: 1, offset: 0.15 }, { opacity: 1, offset: 0.7 }, { opacity: 0.35 }],
                      { duration: BEAM_MS + 900 });
    else beamLine.setAttribute("opacity", 0.35);

    if (!animate) return;

    function bunch() {
      var g = el("g", {}, top);
      // Echoes (where the bunch just was) are fainter copies of the sphere.
      var ghosts = [0, 1, 2].map(function (i) {
        return el("circle", { fill: "url(#ed-sphere)", opacity: (0.32 - i * 0.1).toFixed(2) }, g);
      });
      var halo = el("circle", { fill: "url(#ed-halo)" }, g);
      var body = el("circle", { fill: "url(#ed-sphere)" }, g);
      function place(c, z, scale) {
        var q = at(z);
        c.setAttribute("cx", q.x.toFixed(1)); c.setAttribute("cy", q.y.toFixed(1));
        c.setAttribute("r", (scale * rv / z).toFixed(2));
      }
      return {
        g: g,
        set: function (z, ghostZ, op) {
          place(body, z, 1);
          place(halo, z, 2.1);
          g.setAttribute("opacity", op.toFixed(3));
          ghosts.forEach(function (gc, i) {
            if (ghostZ[i] > 0) place(gc, ghostZ[i], 1); else gc.setAttribute("r", 0);
          });
        }
      };
    }
    var into = bunch(), outOf = bunch();
    var start = null;
    function step(now) {
      if (start === null) start = now;
      var p = Math.min(1, (now - start) / BEAM_MS);
      // Both bunches move at constant speed in depth; perspective does the rest.
      var zi = Z_NEAR + (1 - Z_NEAR) * p;             // into the page: near → collision plane
      var zo = Z_FAR - (Z_FAR - 1) * p;               // out of the page: far → collision plane
      var di = 0.05 * (1 - Z_NEAR), dO = 0.05 * (Z_FAR - 1);
      into.set(zi, [zi - di, zi - 2 * di, zi - 3 * di].map(function (z) { return z >= Z_NEAR ? z : 0; }),
               0.35 + 0.65 * p);
      outOf.set(zo, [zo + dO, zo + 2 * dO, zo + 3 * dO].map(function (z) { return z <= Z_FAR ? z : 0; }),
                0.35 + 0.65 * p);
      if (p < 1) { raf = requestAnimationFrame(step); return; }
      raf = null;
      if (into.g.parentNode) into.g.parentNode.removeChild(into.g);
      if (outOf.g.parentNode) outOf.g.parentNode.removeChild(outOf.g);
    }
    into.set(Z_NEAR, [0, 0, 0], 0.35);
    outOf.set(Z_FAR, [0, 0, 0], 0.35);
    raf = requestAnimationFrame(step);
  }

  draw(!reduce);

  // "New collision" button: generate and play a fresh event.
  if (hero) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "hero__replay";
    btn.textContent = "New collision";
    btn.addEventListener("click", function () {
      seed = (Math.random() * 1e9) | 0;
      draw(!reduce);
    });
    hero.appendChild(btn);
  }

  var timer;
  window.addEventListener("resize", function () {
    clearTimeout(timer);
    timer = setTimeout(function () { draw(false); }, 150);
  });
})();
