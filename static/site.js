/* Monash Particle Physics: navigation, people filter, project tabs. No dependencies. */
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  /* ---- Mobile menu ------------------------------------------------------ */
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      nav.classList.toggle("is-open", !open);
    });
  }

  /* ---- Research dropdown ------------------------------------------------ */
  var dropBtn = document.querySelector(".nav__drop-btn");
  var menu = document.getElementById("research-menu");
  function setMenu(open) {
    if (!dropBtn || !menu) return;
    dropBtn.setAttribute("aria-expanded", String(open));
    menu.hidden = !open;
  }
  if (dropBtn && menu) {
    dropBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      setMenu(dropBtn.getAttribute("aria-expanded") !== "true");
    });
    document.addEventListener("click", function (e) {
      if (!menu.hidden && !menu.contains(e.target)) setMenu(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !menu.hidden) { setMenu(false); dropBtn.focus(); }
    });
    // Close when keyboard focus leaves the dropdown.
    dropBtn.parentElement.addEventListener("focusout", function (e) {
      if (e.relatedTarget && !dropBtn.parentElement.contains(e.relatedTarget)) setMenu(false);
    });
  }

  /* ---- People: filter by research area ---------------------------------- */
  var chips = document.querySelectorAll(".chip[data-filter]");
  if (chips.length) {
    var applyFilter = function (area) {
      chips.forEach(function (c) { c.setAttribute("aria-pressed", String(c.dataset.filter === area)); });
      document.querySelectorAll(".people-group").forEach(function (group) {
        var shown = 0;
        group.querySelectorAll(".card").forEach(function (card) {
          var match = area === "all" || (" " + card.dataset.areas + " ").indexOf(" " + area + " ") !== -1;
          card.classList.toggle("is-filtered-out", !match);
          if (match) shown++;
        });
        var empty = group.querySelector(".people-group__empty");
        if (empty) empty.hidden = shown !== 0;
        // Hide a whole category if nobody matches, except when showing all.
        group.classList.toggle("is-filtered-out", shown === 0 && area !== "all" && !empty);
        var n = group.querySelector(".people-group__n");
        if (n) n.textContent = shown;
      });
    };
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () { applyFilter(chip.dataset.filter); });
    });
  }

  /* ---- Projects: tabs by level (falls back to plain anchors without JS) -- */
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab[role=tab]"));
  if (tabs.length) {
    var panels = tabs.map(function (t) { return document.getElementById(t.getAttribute("aria-controls")); });
    var select = function (i, focus) {
      tabs.forEach(function (t, j) {
        var on = i === j;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        panels[j].hidden = !on;
      });
      if (focus) tabs[i].focus();
    };
    var fromHash = function () {
      var id = decodeURIComponent(location.hash.slice(1));
      if (!id) return select(0);
      var target = document.getElementById(id);
      for (var i = 0; i < panels.length; i++) {
        if (panels[i] === target || (target && panels[i].contains(target))) {
          select(i);
          if (target !== panels[i]) target.scrollIntoView();
          return;
        }
      }
      select(0);
    };
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function (e) {
        e.preventDefault();
        select(i);
        try { history.replaceState(null, "", "#" + panels[i].id); } catch (err) { /* sandboxed */ }
      });
      t.addEventListener("keydown", function (e) {
        var k = e.key, n = tabs.length;
        if (k === "ArrowRight") { e.preventDefault(); select((i + 1) % n, true); }
        if (k === "ArrowLeft") { e.preventDefault(); select((i - 1 + n) % n, true); }
        if (k === "Home") { e.preventDefault(); select(0, true); }
        if (k === "End") { e.preventDefault(); select(n - 1, true); }
      });
    });
    window.addEventListener("hashchange", fromHash);
    fromHash();
  }
})();
