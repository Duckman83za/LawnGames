(function () {
  'use strict';

  var header = document.querySelector('header');
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('primary-nav');
  var navLinks = nav ? nav.querySelectorAll('a') : [];

  /* Keep --header-h in sync so anchor targets clear the sticky header. */
  function syncHeaderHeight() {
    document.documentElement.style.setProperty('--header-h', header.offsetHeight + 'px');
  }
  syncHeaderHeight();
  window.addEventListener('load', syncHeaderHeight);
  if (window.ResizeObserver) {
    new ResizeObserver(syncHeaderHeight).observe(header);
  } else {
    window.addEventListener('resize', syncHeaderHeight);
  }

  /* --- Mobile menu --- */
  function closeMenu() {
    nav.classList.remove('is-open');
    closeSubs(null);
    toggle.setAttribute('aria-expanded', 'false');
  }

  toggle.addEventListener('click', function () {
    var open = nav.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  Array.prototype.forEach.call(navLinks, function (link) {
    link.addEventListener('click', closeMenu);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && nav.classList.contains('is-open')) {
      closeMenu();
      toggle.focus();
    }
  });

  document.addEventListener('click', function (e) {
    if (nav.classList.contains('is-open') && !header.contains(e.target)) closeMenu();
  });

  window.matchMedia('(min-width: 1025px)').addEventListener('change', function (e) {
    if (e.matches) closeMenu();
  });

  /* --- Dropdown sub-menus (The Games, Occasions) --- */
  var subs = document.querySelectorAll('.has-sub');

  function closeSubs(except) {
    Array.prototype.forEach.call(subs, function (li) {
      if (li !== except) {
        li.classList.remove('is-open');
        li.querySelector('.sub-toggle').setAttribute('aria-expanded', 'false');
      }
    });
  }

  Array.prototype.forEach.call(subs, function (li) {
    var btn = li.querySelector('.sub-toggle');
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var open = li.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      closeSubs(li);
    });
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSubs(null);
  });

  document.addEventListener('click', function (e) {
    if (!e.target.closest('.has-sub')) closeSubs(null);
  });

  /* --- Highlight the section currently in view --- */
  var sections = document.querySelectorAll('main section[id]');
  var onHome = document.body.classList.contains('page-home');
  var linkFor = {};
  Array.prototype.forEach.call(navLinks, function (link) {
    linkFor[link.getAttribute('href').slice(1)] = link;
  });

  if (onHome && window.IntersectionObserver) {
    var visible = {};
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        visible[entry.target.id] = entry.isIntersecting;
      });
      var current = null;
      Array.prototype.forEach.call(sections, function (s) {
        if (visible[s.id] && !current) current = s.id;
      });
      Array.prototype.forEach.call(navLinks, function (l) { l.removeAttribute('aria-current'); });
      if (current && linkFor[current]) linkFor[current].setAttribute('aria-current', 'true');
    }, { rootMargin: '-45% 0px -50% 0px' });

    Array.prototype.forEach.call(sections, function (s) { spy.observe(s); });
  }

  /* --- Package buttons prefill the enquiry form --- */
  var eventField = document.getElementById('event');
  Array.prototype.forEach.call(document.querySelectorAll('[data-package]'), function (btn) {
    btn.addEventListener('click', function () {
      if (!eventField) return;
      eventField.value = 'Package ' + btn.getAttribute('data-package');
      window.setTimeout(function () { eventField.focus({ preventScroll: true }); }, 700);
    });
  });

  /* --- Enquiry form -> Formspree ---------------------------------------
     Posts via fetch so the visitor stays on the page. If JS is unavailable
     the plain form action still submits and Formspree renders its own
     thank-you page, so the form degrades rather than breaking. */
  var form = document.getElementById('enquiry-form');
  var status = document.querySelector('.form-status');

  function setStatus(msg, state) {
    status.textContent = msg;
    status.classList.remove('is-error', 'is-success');
    if (state) status.classList.add(state);
  }

  if (form) {
    form.addEventListener('submit', function (e) {
      var endpoint = form.getAttribute('action');

      /* Not configured yet: let the mailto fallback handle it rather than
         posting to a dead endpoint and losing the enquiry. */
      if (endpoint.indexOf('YOUR_FORM_ID') !== -1) {
        e.preventDefault();
        if (!form.checkValidity()) { form.reportValidity(); return; }
        var f = form.elements;
        setStatus('Opening your email app…');
        window.location.href =
          'mailto:shaun@lawngamerentals.co.za' +
          '?subject=' + encodeURIComponent('Lawn Game Rentals enquiry - ' + f.name.value.trim()) +
          '&body=' + encodeURIComponent(
            'Name: ' + f.name.value.trim() + '\n' +
            'Email: ' + f.email.value.trim() + '\n' +
            'Event date / package: ' + (f.event.value.trim() || '-') + '\n\n' +
            'Message:\n' + (f.message.value.trim() || '-') + '\n');
        return;
      }

      if (!window.fetch) return;   /* Very old browser: normal POST proceeds. */
      e.preventDefault();

      if (!form.checkValidity()) { form.reportValidity(); return; }

      var btn = form.querySelector('.form-submit');
      var original = btn.textContent;
      btn.setAttribute('aria-disabled', 'true');
      btn.textContent = 'Sending…';
      setStatus('Sending your enquiry…');

      var data = new FormData(form);
      /* Makes "Reply" in the notification email go straight to the visitor. */
      data.append('_replyto', form.elements.email.value.trim());
      data.append('_subject', 'Lawn Game Rentals enquiry - ' + form.elements.name.value.trim());

      fetch(endpoint, {
        method: 'POST',
        body: data,
        headers: { Accept: 'application/json' }
      }).then(function (res) {
        if (res.ok) {
          form.reset();
          setStatus('Thank you - your enquiry is on its way. We will be in touch within one business day.', 'is-success');
          track('generate_lead', { method: 'enquiry_form' });
          return;
        }
        return res.json().then(function (body) {
          var msg = body && body.errors
            ? body.errors.map(function (x) { return x.message; }).join(', ')
            : 'Something went wrong sending that.';
          throw new Error(msg);
        });
      }).catch(function (err) {
        var reason = err.message || 'Something went wrong sending that';
        if (!/[.!?]$/.test(reason)) reason += '.';
        setStatus(
          reason + ' Please WhatsApp us on 081 756 6989 or email shaun@lawngamerentals.co.za.',
          'is-error'
        );
      }).then(function () {
        btn.removeAttribute('aria-disabled');
        btn.textContent = original;
      });
    });
  }

  /* --- Analytics helper: no-op if GA is blocked or hasn't loaded --- */
  function track(name, params) {
    if (typeof window.gtag === 'function') window.gtag('event', name, params || {});
  }

  /* Direct-contact clicks are leads too; count them alongside the form. */
  Array.prototype.forEach.call(
    document.querySelectorAll('a[href^="https://wa.me/"], a[href^="tel:"], a[href^="mailto:"]'),
    function (a) {
      a.addEventListener('click', function () {
        var href = a.getAttribute('href');
        var method = href.indexOf('wa.me') !== -1 ? 'whatsapp'
                   : href.indexOf('tel:') === 0    ? 'phone'
                   : 'email';
        track('contact', { method: method, placement: a.getAttribute('data-placement') || 'inline' });
      });
    }
  );

  /* --- Footer year --- */
  var year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
})();
