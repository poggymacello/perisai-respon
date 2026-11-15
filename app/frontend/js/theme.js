// Tema terang/gelap. Dimuat sinkron di <head> supaya tidak ada kilatan tema yang salah.
// Pilihan disimpan per peramban; tanpa pilihan, mengikuti preferensi OS.
(function () {
  var KEY = "perisai.theme";
  function read() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function write(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* mode privat */ } }
  var saved = read();
  if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
  window.perisaiTheme = {
    current: function () {
      var t = document.documentElement.getAttribute("data-theme");
      if (t) return t;
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    },
    toggle: function () {
      var next = this.current() === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      write(next);
      return next;
    },
  };
})();
