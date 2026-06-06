/* InsightBridge Strategy & AI Research — App Logic v4 (Mobile + 4-Language) */
(function () {
  'use strict';

  var root = document.documentElement;

  /* ===== DARK / LIGHT MODE (with localStorage) ===== */
  var savedTheme = localStorage.getItem('ib-theme');
  var currentTheme = savedTheme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  root.setAttribute('data-theme', currentTheme);

  var themeToggle = document.getElementById('theme-toggle');
  updateThemeIcon();

  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', currentTheme);
      localStorage.setItem('ib-theme', currentTheme);
      updateThemeIcon();
    });
  }

  function updateThemeIcon() {
    if (!themeToggle) return;
    themeToggle.setAttribute('aria-label', 'Switch to ' + (currentTheme === 'dark' ? 'light' : 'dark') + ' mode');
    themeToggle.innerHTML = currentTheme === 'dark'
      ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
      : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  }

  /* ===== 4-LANGUAGE SYSTEM ===== */
  /*
   * EN / CN  — native span-based system (data-lang attribute on <html>)
   * TH / AR  — Google Translate Element (loaded on demand)
   * AR       — also sets dir="rtl" on <html>
   */

  var LANG_LABELS = { en: 'EN', cn: '中文', th: 'TH', ar: 'AR', vi: 'VI', ms: 'MS', id: 'ID' };

  var savedLang = localStorage.getItem('ib-lang') || 'en';
  var currentLang = savedLang;

  var langBtn     = document.getElementById('lang-btn');
  var langBtnLbl  = document.getElementById('lang-btn-label');
  var langMenu    = document.getElementById('lang-menu');

  /* Apply language on init */
  applyLang(currentLang, false);

  /* Toggle dropdown */
  if (langBtn) {
    langBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = langMenu.classList.toggle('open');
      langBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  /* Close on outside click */
  document.addEventListener('click', function () {
    if (langMenu) {
      langMenu.classList.remove('open');
      if (langBtn) langBtn.setAttribute('aria-expanded', 'false');
    }
  });

  /* Language option click */
  if (langMenu) {
    langMenu.querySelectorAll('[data-lang]').forEach(function (opt) {
      opt.addEventListener('click', function (e) {
        e.stopPropagation();
        var lang = this.getAttribute('data-lang');
        applyLang(lang, true);
        langMenu.classList.remove('open');
        if (langBtn) langBtn.setAttribute('aria-expanded', 'false');
      });
    });
  }

  function applyLang(lang, persist) {
    var prev = currentLang;
    currentLang = lang;

    /* Update label */
    if (langBtnLbl) langBtnLbl.textContent = LANG_LABELS[lang] || lang.toUpperCase();

    /* Mark active option */
    if (langMenu) {
      langMenu.querySelectorAll('[data-lang]').forEach(function (opt) {
        opt.classList.toggle('active', opt.getAttribute('data-lang') === lang);
      });
    }

    if (persist) localStorage.setItem('ib-lang', lang);

    var GT_LANGS = { th: true, ar: true, vi: true, ms: true, id: true };

    if (lang === 'en' || lang === 'cn') {
      /* --- Native system --- */
      /* If coming from a GT language, clear GT and reload */
      if (GT_LANGS[prev]) {
        resetGoogleTranslate(lang);
        return; /* page will reload */
      }
      root.setAttribute('data-lang', lang);
      root.setAttribute('lang', lang === 'en' ? 'en' : 'zh-CN');
      root.removeAttribute('dir');
    } else if (GT_LANGS[lang]) {
      /* --- Google Translate system --- */
      /* Always show English source to GT */
      root.setAttribute('data-lang', 'en');
      root.setAttribute('lang', 'en');

      /* Arabic is RTL; all other GT langs are LTR */
      if (lang === 'ar') {
        root.setAttribute('dir', 'rtl');
      } else {
        root.removeAttribute('dir');
      }

      loadGoogleTranslate(lang);
    }
  }

  /* Load Google Translate widget and select language */
  window.googleTranslateElementInit = function () {
    new google.translate.TranslateElement({
      pageLanguage: 'en',
      includedLanguages: 'th,ar,vi,ms,id',
      autoDisplay: false
    }, 'google_translate_element');

    /* Start polling for the combo box after widget init */
    pollForGTSelect(window._gtTargetLang, 0);
  };

  function loadGoogleTranslate(targetLang) {
    window._gtTargetLang = targetLang;

    if (window._gtLoaded) {
      /* Widget already initialised — poll for the select box */
      pollForGTSelect(targetLang, 0);
      return;
    }

    window._gtLoaded = true;
    var s = document.createElement('script');
    s.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
    s.async = true;
    document.head.appendChild(s);
  }

  /* Poll up to 20 times (every 300 ms = 6 s total) for .goog-te-combo */
  function pollForGTSelect(lang, attempt) {
    if (attempt > 20) return; /* give up after 6 s */
    var select = document.querySelector('.goog-te-combo');
    if (select) {
      select.value = lang;
      select.dispatchEvent(new Event('change'));
    } else {
      setTimeout(function () { pollForGTSelect(lang, attempt + 1); }, 300);
    }
  }

  function resetGoogleTranslate(nextLang) {
    /* Clear Google Translate cookies */
    var domains = ['', '.insightbridge.global', 'insightbridge.global'];
    domains.forEach(function (d) {
      document.cookie = 'googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/' + (d ? '; domain=' + d : '');
    });
    /* Save desired next lang so it's applied after reload */
    localStorage.setItem('ib-lang', nextLang);
    location.reload();
  }

  /* ===== SPA HASH ROUTING ===== */
  var pageMap = {
    home:         'page-home',
    news:         'page-news',
    about:        'page-about',
    framework:    'page-framework',
    'ai-model':   'page-ai-model',
    publications: 'page-publications',
    cases:        'page-cases',
    tourism:      'page-tourism',
    intelligence: 'page-intelligence',
    tools:        'page-tools',
    contact:      'page-contact'
  };

  function navigateTo(page) {
    var targetId = pageMap[page] || 'page-home';

    var pages = document.querySelectorAll('.page');
    for (var i = 0; i < pages.length; i++) {
      pages[i].classList.remove('active');
    }

    var el = document.getElementById(targetId);
    if (el) el.classList.add('active');

    var navLinks = document.querySelectorAll('.header__nav a, .mobile-nav a');
    for (var j = 0; j < navLinks.length; j++) {
      navLinks[j].classList.remove('active');
      if (navLinks[j].getAttribute('href') === '#' + page) {
        navLinks[j].classList.add('active');
      }
    }

    closeDrawer();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    observeReveals();
  }

  function handleHash() {
    var hash = location.hash.replace('#', '') || 'home';
    navigateTo(hash);
  }

  window.addEventListener('hashchange', handleHash);
  handleHash();

  document.addEventListener('click', function (e) {
    var link = e.target.closest('a[href^="#"]');
    if (link) {
      e.preventDefault();
      var hash = link.getAttribute('href').replace('#', '');
      location.hash = hash;
    }
  });

  /* ===== MOBILE DRAWER (slide-in from right) ===== */
  var mobileMenuBtn  = document.getElementById('mobile-menu-btn');
  var mobileNav      = document.getElementById('mobile-nav');
  var mobileNavClose = document.getElementById('mobile-nav-close');
  var navBackdrop    = document.getElementById('mobile-nav-backdrop');

  function openDrawer() {
    if (!mobileNav) return;
    mobileNav.classList.add('open');
    if (navBackdrop) navBackdrop.style.display = 'block';
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    if (!mobileNav) return;
    mobileNav.classList.remove('open');
    if (navBackdrop) navBackdrop.style.display = '';
    document.body.style.overflow = '';
  }

  if (mobileMenuBtn)  mobileMenuBtn.addEventListener('click', openDrawer);
  if (mobileNavClose) mobileNavClose.addEventListener('click', closeDrawer);
  if (navBackdrop)    navBackdrop.addEventListener('click', closeDrawer);

  /* ===== SCROLL REVEAL (IntersectionObserver) ===== */
  function observeReveals() {
    var reveals = document.querySelectorAll('.reveal:not(.visible)');
    if (!reveals.length) return;

    if (!('IntersectionObserver' in window)) {
      for (var i = 0; i < reveals.length; i++) {
        reveals[i].classList.add('visible');
      }
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    for (var j = 0; j < reveals.length; j++) {
      observer.observe(reveals[j]);
    }
  }

  observeReveals();

  /* ===== DEFERRED GOOGLE ANALYTICS ===== */
  function loadGA() {
    if (window._gaLoaded) return;
    window._gaLoaded = true;
    var s = document.createElement('script');
    s.src = 'https://www.googletagmanager.com/gtag/js?id=G-VY7PLNRXNM';
    s.async = true;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    function gtag() { dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag('js', new Date());
    gtag('config', 'G-VY7PLNRXNM');
  }

  if ('requestIdleCallback' in window) {
    requestIdleCallback(loadGA, { timeout: 2500 });
  } else {
    setTimeout(loadGA, 2500);
  }

  /* ===== LAZY ZOHO SALESIQ (first interaction or 6 s idle) ===== */
  function loadZoho() {
    if (window._zohoLoaded) return;
    window._zohoLoaded = true;

    window.$zoho = window.$zoho || {};
    $zoho.salesiq = $zoho.salesiq || { ready: function () {} };

    var s = document.createElement('script');
    s.id = 'zsiqscript';
    s.src = 'https://salesiq.zohopublic.com/widget?wc=siq76f4656c64d4e5065c3194d7d468d59d7e82783c33020b302bf072dc0b1090d4';
    s.defer = true;
    document.body.appendChild(s);

    ['scroll', 'touchstart', 'click', 'keydown'].forEach(function (evt) {
      document.removeEventListener(evt, loadZoho);
    });
  }

  ['scroll', 'touchstart', 'click', 'keydown'].forEach(function (evt) {
    document.addEventListener(evt, loadZoho, { once: true, passive: true });
  });

  if ('requestIdleCallback' in window) {
    requestIdleCallback(function () { setTimeout(loadZoho, 1000); }, { timeout: 6000 });
  } else {
    setTimeout(loadZoho, 6000);
  }

  /* ===== iPad/Tablet safety: auto-close drawer when viewport >768px ===== */
  function autoCloseDrawerOnResize() {
    if (window.innerWidth > 768) {
      var mn = document.getElementById('mobile-nav');
      var bd = document.getElementById('mobile-nav-backdrop');
      if (mn) mn.classList.remove('open');
      if (bd) bd.style.display = '';
      document.body.style.overflow = '';
    }
  }
  window.addEventListener('resize', autoCloseDrawerOnResize);
  window.addEventListener('orientationchange', autoCloseDrawerOnResize);
  autoCloseDrawerOnResize();

})();
