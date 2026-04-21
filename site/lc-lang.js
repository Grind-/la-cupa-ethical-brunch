(function () {
  var LANGS = [
    { code: 'it', label: 'IT', name: 'Italiano', flag: '🇮🇹' },
    { code: 'en', label: 'EN', name: 'English',  flag: '🇬🇧' },
    { code: 'de', label: 'DE', name: 'Deutsch',  flag: '🇩🇪' },
    { code: 'fr', label: 'FR', name: 'Français', flag: '🇫🇷' },
    { code: 'es', label: 'ES', name: 'Español',  flag: '🇪🇸' },
  ];

  var DEFAULT_LANG = 'it';
  var currentLang = localStorage.getItem('lc-lang') || DEFAULT_LANG;
  var translations = null;

  /* ── Protect brand/place names from being overwritten ── */
  var BRAND_RE = /La\s+Cupa|LA\s+CUPA|Lecce|LECCE/gi;

  function fixBrand(text) {
    return text
      .replace(/\b(LA\s+)?(SOMBRE|OSCURIDAD|DUNKEL|TASSE|LA TASSE|LA COUPE|DARK)\b/gi, 'LA CUPA')
      .replace(/\bCUPA\b/g, 'CUPA'); // keep existing
  }

  /* ── Apply a language to the page ── */
  function applyLang(lang) {
    if (!translations) return;
    currentLang = lang;
    localStorage.setItem('lc-lang', lang);

    // Update button label
    var btn = document.getElementById('lc-lang-btn');
    if (btn) {
      var info = LANGS.find(function(l){ return l.code === lang; });
      btn.querySelector('.lc-lang-label').textContent = info ? info.label : lang.toUpperCase();
    }
    // Mark active in dropdown
    document.querySelectorAll('.lc-lang-option').forEach(function(a) {
      a.classList.toggle('lc-current', a.dataset.code === lang);
    });

    // Apply translations to all spectra elements
    document.querySelectorAll('[data-spectra-id]').forEach(function(el) {
      var sid = el.getAttribute('data-spectra-id');
      var entry = translations[sid];
      if (!entry || !entry[lang]) return;

      // Skip container elements that have spectra-id children
      // (their children will handle their own text)
      var spectraChildren = el.querySelectorAll('[data-spectra-id]');
      if (spectraChildren.length > 0) return;

      var newText = fixBrand(entry[lang]);

      // Preserve inner markup (<strong>, <em>, <a>) when possible
      // by only replacing direct text nodes
      var hasMarkup = el.querySelector('strong, em, a, br');
      if (hasMarkup) {
        // Replace only direct text nodes
        el.childNodes.forEach(function(node) {
          if (node.nodeType === 3 && node.textContent.trim()) {
            node.textContent = newText;
          }
        });
      } else {
        el.textContent = newText;
      }
    });
  }

  /* ── Build the UI button ── */
  function buildUI() {
    var mobileHeader = document.getElementById('ast-mobile-header');
    if (!mobileHeader) return;
    var right = mobileHeader.querySelector('.ast-grid-right-section');
    if (!right) return;

    var wrap = document.createElement('div');
    wrap.id = 'lc-lang-switcher';

    var btn = document.createElement('button');
    btn.id = 'lc-lang-btn';
    btn.setAttribute('aria-label', 'Select language');

    var info = LANGS.find(function(l){ return l.code === currentLang; }) || LANGS[0];
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z' +
        'm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z' +
        'm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2' +
        'c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>' +
      '</svg>' +
      '<span class="lc-lang-label">' + info.label + '</span>';

    var dd = document.createElement('div');
    dd.id = 'lc-lang-dropdown';
    dd.hidden = true;

    LANGS.forEach(function(l) {
      var a = document.createElement('a');
      a.href = '#';
      a.className = 'lc-lang-option' + (l.code === currentLang ? ' lc-current' : '');
      a.dataset.code = l.code;
      a.innerHTML = '<span>' + l.flag + '</span><span>' + l.name + '</span>';
      a.addEventListener('click', function(e) {
        e.preventDefault();
        dd.hidden = true;
        if (translations) {
          applyLang(l.code);
        } else {
          fetch('/lc-translations.json')
            .then(function(r){ return r.json(); })
            .then(function(data){
              translations = data;
              applyLang(l.code);
            });
        }
      });
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

    // Auto-apply saved language on load
    if (currentLang !== DEFAULT_LANG) {
      fetch('/lc-translations.json')
        .then(function(r){ return r.json(); })
        .then(function(data){
          translations = data;
          applyLang(currentLang);
        });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildUI);
  } else {
    buildUI();
  }
})();
