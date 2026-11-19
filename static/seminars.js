/* Seminars page: loads data/seminars.json when the page opens and splits the talks into
   upcoming and past using the visitor's current time. Times are shown in Melbourne time.
   The JSON is refreshed from the School's talks page each time the site is rebuilt. */
(function () {
  "use strict";
  var box = document.getElementById("seminars");
  if (!box) return;
  var TZ = "Australia/Melbourne";
  var statusEl = box.querySelector(".sem-status");
  var upEl = document.getElementById("sem-upcoming");
  var pastEl = document.getElementById("sem-past");
  var moreBtn = box.querySelector(".sem-more");
  var sourceUrl = box.dataset.sourceUrl;
  var pastLimit = parseInt(box.dataset.pastLimit, 10) || 12;

  function fmt(opts) {
    try { return new Intl.DateTimeFormat("en-AU", Object.assign({ timeZone: TZ }, opts)); }
    catch (e) { return new Intl.DateTimeFormat("en-AU", opts); }
  }
  var fDay = fmt({ day: "numeric" }), fMon = fmt({ month: "short" }), fYear = fmt({ year: "numeric" });
  var fLong = fmt({ weekday: "long", day: "numeric", month: "long", year: "numeric" });
  var fTime = fmt({ hour: "numeric", minute: "2-digit", hour12: true });
  var fStamp = fmt({ day: "numeric", month: "long", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true });

  function node(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || "") ? u : null; }
  function time(d) { return fTime.format(d).replace(/\s?([ap])\.?m\.?/i, function (_, x) { return " " + x.toLowerCase() + "m"; }); }

  // Calendar feed: offer webcal:// so the calendar app subscribes (and keeps updating).
  var sub = document.getElementById("sem-subscribe");
  if (sub) {
    try {
      var abs = new URL(sub.getAttribute("href"), location.href);
      if (/^https?:$/.test(abs.protocol)) sub.href = "webcal://" + abs.host + abs.pathname;
    } catch (e) { /* keep the plain link */ }
  }

  function seminarItem(e, isNext) {
    var art = node("article", "seminar" + (isNext ? " seminar--next" : "") + (e.past ? " seminar--past" : ""));
    var tile = node("div", "seminar__date");
    tile.setAttribute("aria-hidden", "true");
    tile.appendChild(node("span", "seminar__day", fDay.format(e.s)));
    tile.appendChild(node("span", "seminar__mon", fMon.format(e.s)));
    tile.appendChild(node("span", "seminar__yr", fYear.format(e.s)));
    art.appendChild(tile);

    var body = node("div", "seminar__body");
    if (isNext) body.appendChild(node("p", "seminar__flag", "Next seminar"));
    body.appendChild(node("h3", "seminar__title", e.title || "Title to be announced"));
    if (e.speaker) {
      var who = node("p", "seminar__speaker");
      who.appendChild(node("strong", null, e.speaker));
      if (e.affiliation) who.appendChild(document.createTextNode(", " + e.affiliation));
      body.appendChild(who);
    }
    var when = fLong.format(e.s);
    if (!e.all_day) when += ", " + time(e.s) + (e.en > e.s ? " – " + time(e.en) : "");
    var meta = node("p", "seminar__meta");
    var t = node("time", null, when);
    t.setAttribute("datetime", e.start);
    meta.appendChild(t);
    if (e.location) { meta.appendChild(node("br")); meta.appendChild(document.createTextNode(e.location)); }
    body.appendChild(meta);

    var links = (e.links || []).filter(function (l) { return safeUrl(l.url); });
    if (links.length) {
      var ul = node("ul", "seminar__links");
      links.forEach(function (l) {
        var li = node("li"), a = node("a", null, l.label || "Link");
        a.href = l.url;
        li.appendChild(a); ul.appendChild(li);
      });
      body.appendChild(ul);
    }
    art.appendChild(body);
    return art;
  }

  function render(data) {
    var now = Date.now();
    var events = (data.events || []).map(function (e) {
      var o = Object.assign({}, e);
      o.s = new Date(e.start); o.en = new Date(e.end || e.start);
      o.past = o.en.getTime() < now;
      return o;
    }).filter(function (e) { return !isNaN(e.s); });

    var upcoming = events.filter(function (e) { return !e.past; }).sort(function (a, b) { return a.s - b.s; });
    var past = events.filter(function (e) { return e.past; }).sort(function (a, b) { return b.s - a.s; });

    upEl.textContent = "";
    if (upcoming.length) {
      upcoming.forEach(function (e, i) { upEl.appendChild(seminarItem(e, i === 0)); });
    } else {
      var p = node("p", "empty", "No upcoming particle physics seminars are listed yet. New talks appear here automatically once they are announced on the ");
      var a = node("a", null, "School's talks page"); a.href = sourceUrl;
      p.appendChild(a); p.appendChild(document.createTextNode("."));
      upEl.appendChild(p);
    }

    pastEl.textContent = "";
    if (past.length) {
      past.forEach(function (e, i) {
        var item = seminarItem(e, false);
        if (i >= pastLimit) { item.hidden = true; item.classList.add("is-extra"); }
        pastEl.appendChild(item);
      });
      if (past.length > pastLimit) {
        moreBtn.hidden = false;
        moreBtn.textContent = "Show all " + past.length + " past seminars";
        moreBtn.onclick = function () {
          pastEl.querySelectorAll(".is-extra").forEach(function (el) { el.hidden = false; });
          moreBtn.hidden = true;
        };
      }
    } else {
      pastEl.appendChild(node("p", "empty", "No past seminars are listed."));
    }

    // Status line: when the list was last refreshed, and the time-zone note.
    statusEl.textContent = "";
    var stamp = data.generated ? fStamp.format(new Date(data.generated)) : null;
    if (data.status === "ok" && data.origin === "file") {
      statusEl.textContent = "Sample list built from a saved copy of the School's talks page. The published site refreshes it automatically.";
    } else if (data.status === "ok") {
      statusEl.textContent = "Updated " + (stamp || "recently") + " from the School's talks page.";
    } else if (data.status === "stale") {
      statusEl.textContent = "The School's talks page couldn't be read at the last update, so this is the list from " + (stamp || "an earlier update") + ".";
    } else {
      statusEl.appendChild(document.createTextNode("The seminar list couldn't be read from the School's talks page. See the "));
      var l = node("a", null, "Seminars and Colloquia page"); l.href = sourceUrl;
      statusEl.appendChild(l); statusEl.appendChild(document.createTextNode(" instead."));
    }
    var localTz = (Intl.DateTimeFormat().resolvedOptions() || {}).timeZone;
    if (localTz && localTz !== TZ && events.length) {
      statusEl.appendChild(document.createTextNode(" Times are Melbourne time."));
    }
  }

  function fail() {
    statusEl.textContent = "";
    statusEl.appendChild(document.createTextNode("The seminar list couldn't be loaded. See the School's "));
    var a = node("a", null, "Seminars and Colloquia page"); a.href = sourceUrl;
    statusEl.appendChild(a); statusEl.appendChild(document.createTextNode("."));
  }

  fetch(box.dataset.src, { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(render)
    .catch(fail);
})();
