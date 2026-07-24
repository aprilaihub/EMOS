/* ============================================================
   EMOS marketing — progressive UX enhancements.
   Scroll-reveal on entering the viewport + a subtle nav shadow
   once the page is scrolled. Everything here is additive: with
   JS off, nothing is hidden and the page reads exactly as before.
   ============================================================ */
(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* --- nav gains a hairline shadow once you leave the very top --- */
  var nav = document.querySelector(".home-nav");
  if (nav) {
    var onScroll = function () { nav.classList.toggle("scrolled", window.scrollY > 6); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  if (reduce) return; // honour reduced-motion: no reveal choreography

  /* --- scroll reveal: fade + rise section blocks as they enter --- */
  var selector = [
    ".section .split",
    ".section .editorial",
    ".intro-prose",
    ".acc",
    ".role-cols",
    ".stat-band",
    ".about-statement",
    ".team-grid",
    ".partners",
    ".cta-band .wrap",
    ".section > .wrap > .section-title"
  ].join(",");

  var els = Array.prototype.slice.call(document.querySelectorAll(selector));
  if (!els.length) return;

  // add the reveal hook via JS so no-JS users never see hidden content
  els.forEach(function (el) { el.classList.add("reveal"); });

  if (!("IntersectionObserver" in window)) {
    els.forEach(function (el) { el.classList.add("in"); });
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add("in");
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -7% 0px" });

  els.forEach(function (el) { io.observe(el); });
})();
