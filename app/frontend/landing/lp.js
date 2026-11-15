// Landing PERISAI-RESPON: header lengket, menu ponsel, dan animasi muncul saat di-scroll.
// Tanpa JS halaman tetap utuh: kelas `js` baru dipasang di sini, dan .reveal hanya disembunyikan bila kelas itu ada.
(function () {
  var root = document.documentElement;
  root.classList.add("js");

  document.addEventListener("DOMContentLoaded", function () {
    var header = document.getElementById("lp-header");
    var menu = document.getElementById("lp-menu");
    var mobile = document.getElementById("lp-mobile");

    function onScroll() {
      var solid = window.scrollY > 24 || !mobile.hidden;
      if (solid) header.setAttribute("data-solid", ""); else header.removeAttribute("data-solid");
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    function setMenu(open) {
      mobile.hidden = !open;
      menu.setAttribute("aria-expanded", open ? "true" : "false");
      menu.setAttribute("aria-label", open ? "Tutup menu" : "Buka menu");
      onScroll();
    }
    menu.addEventListener("click", function () { setMenu(mobile.hidden); });
    mobile.addEventListener("click", function (e) { if (e.target.tagName === "A") setMenu(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") setMenu(false); });

    var items = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.setAttribute("data-shown", ""); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.setAttribute("data-shown", ""); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    items.forEach(function (el, i) {
      // jeda kecil berurutan untuk kartu yang bersebelahan
      var sib = Array.prototype.indexOf.call(el.parentElement.children, el);
      el.style.transitionDelay = Math.min(sib, 6) * 70 + "ms";
      io.observe(el);
    });
  });
})();
