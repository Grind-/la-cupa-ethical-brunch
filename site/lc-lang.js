(function () {
  var langs = [
    { code: 'en', label: 'EN', name: 'English',  flag: '🇬🇧', href: '/' },
    { code: 'it', label: 'IT', name: 'Italiano', flag: '🇮🇹', href: '/it/' },
    { code: 'de', label: 'DE', name: 'Deutsch',  flag: '🇩🇪', href: '/de/' },
    { code: 'fr', label: 'FR', name: 'Français', flag: '🇫🇷', href: '/fr/' },
    { code: 'es', label: 'ES', name: 'Español',  flag: '🇪🇸', href: '/es/' },
  ];

  var path = window.location.pathname;
  var m = path.match(/^\/(it|de|fr|es)\//);
  var current = m ? m[1] : 'en';

  function build() {
    var mobileHeader = document.getElementById('ast-mobile-header');
    if (!mobileHeader) return;
    var right = mobileHeader.querySelector('.ast-grid-right-section');
    if (!right) return;

    var wrap = document.createElement('div');
    wrap.id = 'lc-lang-switcher';

    var btn = document.createElement('button');
    btn.id = 'lc-lang-btn';
    btn.setAttribute('aria-label', 'Select language');
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z' +
        'm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z' +
        'm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2' +
        'c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>' +
      '</svg>' +
      langs.find(function(l){ return l.code === current; }).label;

    var dd = document.createElement('div');
    dd.id = 'lc-lang-dropdown';
    dd.hidden = true;

    langs.forEach(function(l) {
      var a = document.createElement('a');
      a.href = l.href;
      a.className = 'lc-lang-option' + (l.code === current ? ' lc-current' : '');
      a.innerHTML = '<span>' + l.flag + '</span><span>' + l.name + '</span>';
      dd.appendChild(a);
    });

    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      dd.hidden = !dd.hidden;
    });
    document.addEventListener('click', function() { dd.hidden = true; });

    wrap.appendChild(btn);
    wrap.appendChild(dd);
    right.insertBefore(wrap, right.firstChild);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', build);
  } else {
    build();
  }
})();
