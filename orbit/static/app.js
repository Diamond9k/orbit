/* Small page behaviour shared by every page. Kept in a file, not in the pages, so the
   content security policy can forbid inline script altogether. */
(function () {
  'use strict';
  // <form data-confirm="..."> asks before it is sent. The question is read as text, never as code.
  document.addEventListener('submit', function (e) {
    var q = e.target.getAttribute && e.target.getAttribute('data-confirm');
    if (q && !window.confirm(q)) e.preventDefault();
  });
  // A form sent once: the button shows it is working and cannot be pressed twice.
  document.addEventListener('submit', function (e) {
    if (e.defaultPrevented) return;
    var b = e.target.querySelector && e.target.querySelector('button[data-busy]');
    if (b) { b.disabled = true; b.textContent = b.getAttribute('data-busy'); }
  });
  // [data-copy="#id"] copies that element's text.
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-copy]');
    if (!b || !navigator.clipboard) return;
    var el = document.querySelector(b.getAttribute('data-copy'));
    if (el) navigator.clipboard.writeText(el.textContent.trim()).then(function () { b.textContent = 'Copied'; });
  });
})();
