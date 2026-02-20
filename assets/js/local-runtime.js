(function () {
  'use strict';

  var CART_STORAGE_KEY = 'vhc_local_cart_items';
  var COURSE_PROGRESS_STORAGE_KEY = 'vhc_course_progress_v1';
  var searchIndexPromise = null;

  function resolveSearchIndexUrl() {
    var script = document.currentScript;
    if (!script) {
      var scripts = document.querySelectorAll('script[src]');
      for (var i = scripts.length - 1; i >= 0; i -= 1) {
        if (/local-runtime\.js(?:\?|$)/.test(scripts[i].src)) {
          script = scripts[i];
          break;
        }
      }
    }
    if (script && script.src) {
      return new URL('../data/search-index.json', script.src).toString();
    }
    return 'assets/data/search-index.json';
  }

  function safeJsonParse(value, fallback) {
    try {
      return JSON.parse(value);
    } catch (_error) {
      return fallback;
    }
  }

  function getCartItems() {
    var raw = window.localStorage.getItem(CART_STORAGE_KEY);
    var parsed = raw ? safeJsonParse(raw, []) : [];
    return Array.isArray(parsed) ? parsed : [];
  }

  function updateCartBadge() {
    var count = getCartItems().length;
    var badges = document.querySelectorAll('.sqs-cart-quantity');
    badges.forEach(function (badge) {
      badge.textContent = String(count);
    });
  }

  function initMenuToggle() {
    var menu = document.querySelector('.header-menu');
    if (!menu) {
      return;
    }

    var body = document.body;
    var toggles = document.querySelectorAll('.header-burger-btn');

    function setOpen(isOpen) {
      body.classList.toggle('header--menu-open', isOpen);
      toggles.forEach(function (button) {
        button.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      });
    }

    function toggleOpen() {
      setOpen(!body.classList.contains('header--menu-open'));
    }

    toggles.forEach(function (button) {
      button.setAttribute('aria-expanded', 'false');
      button.addEventListener('click', function (event) {
        event.preventDefault();
        toggleOpen();
      });
    });

    menu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        setOpen(false);
      });
    });

    var backdrop = menu.querySelector('.header-menu-bg');
    if (backdrop) {
      backdrop.addEventListener('click', function () {
        setOpen(false);
      });
    }

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    });
  }

  function initNonCommerceCart() {
    var root = document.getElementById('local-cart-root');
    if (!root) {
      return;
    }

    var countNode = root.querySelector('[data-local-cart-count]');
    if (countNode) {
      countNode.textContent = String(getCartItems().length);
    }

    var clearButton = root.querySelector('[data-local-clear-cart]');
    if (clearButton) {
      clearButton.addEventListener('click', function () {
        window.localStorage.removeItem(CART_STORAGE_KEY);
        updateCartBadge();
        if (countNode) {
          countNode.textContent = '0';
        }
      });
    }
  }

  function tokenize(input) {
    return input
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter(Boolean);
  }

  function scoreEntry(entry, tokens) {
    var title = String(entry.title || '').toLowerCase();
    var text = String(entry.text || '').toLowerCase();
    var score = 0;

    tokens.forEach(function (token) {
      if (title.indexOf(token) !== -1) {
        score += 8;
      }
      if (text.indexOf(token) !== -1) {
        score += 2;
      }
    });

    return score;
  }

  function formatSnippet(text, tokens) {
    var normalized = String(text || '').replace(/\s+/g, ' ').trim();
    if (!normalized) {
      return '';
    }

    var lower = normalized.toLowerCase();
    var firstHit = -1;

    tokens.forEach(function (token) {
      if (firstHit !== -1) {
        return;
      }
      var idx = lower.indexOf(token);
      if (idx !== -1) {
        firstHit = idx;
      }
    });

    if (firstHit === -1) {
      return normalized.slice(0, 180) + (normalized.length > 180 ? '...' : '');
    }

    var start = Math.max(0, firstHit - 70);
    var end = Math.min(normalized.length, firstHit + 110);
    var prefix = start > 0 ? '...' : '';
    var suffix = end < normalized.length ? '...' : '';
    return prefix + normalized.slice(start, end) + suffix;
  }

  function loadSearchIndex() {
    if (!searchIndexPromise) {
      searchIndexPromise = fetch(resolveSearchIndexUrl(), { cache: 'no-store' })
        .then(function (response) {
          if (!response.ok) {
            throw new Error('Search index request failed');
          }
          return response.json();
        })
        .then(function (payload) {
          return Array.isArray(payload.pages) ? payload.pages : [];
        })
        .catch(function () {
          return [];
        });
    }
    return searchIndexPromise;
  }

  function createSearchOverlay() {
    if (document.getElementById('local-search-overlay')) {
      return document.getElementById('local-search-overlay');
    }

    var overlay = document.createElement('div');
    overlay.id = 'local-search-overlay';
    overlay.className = 'local-search-overlay';
    overlay.hidden = true;
    overlay.innerHTML =
      '<div class="local-search-panel" role="dialog" aria-modal="true" aria-label="Site search">' +
      '  <div class="local-search-header">' +
      '    <h2>Search This Site</h2>' +
      '    <button type="button" class="local-search-close" aria-label="Close search">Close</button>' +
      '  </div>' +
      '  <input type="search" class="local-search-input" placeholder="Search modules, lessons, or topics" autocomplete="off" />' +
      '  <p class="local-search-help">Use Enter to open the first result. Press Esc to close.</p>' +
      '  <ul class="local-search-results" aria-live="polite"></ul>' +
      '</div>';

    document.body.appendChild(overlay);
    return overlay;
  }

  function initSearchUi() {
    var overlay = createSearchOverlay();
    var closeButton = overlay.querySelector('.local-search-close');
    var input = overlay.querySelector('.local-search-input');
    var results = overlay.querySelector('.local-search-results');

    function closeSearch() {
      overlay.hidden = true;
      document.body.classList.remove('local-search-open');
    }

    function openSearch(prefill) {
      overlay.hidden = false;
      document.body.classList.add('local-search-open');
      input.focus();
      if (typeof prefill === 'string') {
        input.value = prefill;
      }
      runSearch();
    }

    function renderResults(items, queryTokens) {
      results.innerHTML = '';

      if (!items.length) {
        var empty = document.createElement('li');
        empty.className = 'local-search-empty';
        empty.textContent = 'No matching pages found.';
        results.appendChild(empty);
        return;
      }

      items.forEach(function (item) {
        var li = document.createElement('li');
        var link = document.createElement('a');
        var title = document.createElement('strong');
        var snippet = document.createElement('span');

        link.href = item.url;
        title.textContent = item.title;
        snippet.textContent = formatSnippet(item.text, queryTokens);

        link.appendChild(title);
        if (snippet.textContent) {
          link.appendChild(snippet);
        }
        li.appendChild(link);
        results.appendChild(li);
      });
    }

    function runSearch() {
      var query = input.value.trim();
      if (!query) {
        results.innerHTML = '';
        return;
      }

      var queryTokens = tokenize(query);
      if (!queryTokens.length) {
        results.innerHTML = '';
        return;
      }

      loadSearchIndex().then(function (pages) {
        var matches = pages
          .map(function (entry) {
            return {
              entry: entry,
              score: scoreEntry(entry, queryTokens),
            };
          })
          .filter(function (item) {
            return item.score > 0;
          })
          .sort(function (left, right) {
            return right.score - left.score;
          })
          .slice(0, 12)
          .map(function (item) {
            return item.entry;
          });

        renderResults(matches, queryTokens);
      });
    }

    closeButton.addEventListener('click', closeSearch);
    overlay.addEventListener('click', function (event) {
      if (event.target === overlay) {
        closeSearch();
      }
    });

    input.addEventListener('input', runSearch);
    input.addEventListener('keydown', function (event) {
      if (event.key === 'Enter') {
        var firstLink = results.querySelector('a');
        if (firstLink) {
          window.location.href = firstLink.href;
        }
      }
    });

    document.addEventListener('keydown', function (event) {
      var target = event.target;
      var targetTag = target && target.tagName ? target.tagName.toLowerCase() : '';
      var isTyping = targetTag === 'input' || targetTag === 'textarea' || (target && target.isContentEditable);

      if (event.key === 'Escape' && !overlay.hidden) {
        closeSearch();
      }

      if (event.key === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        openSearch('');
      }

      if (event.key === '/' && !isTyping) {
        event.preventDefault();
        openSearch('');
      }
    });

    var launchTargets = document.querySelectorAll('.header-actions .showOnDesktop, .header-actions .showOnMobile');
    launchTargets.forEach(function (container) {
      if (container.querySelector('.local-search-launch')) {
        return;
      }
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'local-search-launch';
      button.textContent = 'Search';
      button.addEventListener('click', function () {
        openSearch('');
      });
      container.appendChild(button);
    });

    var initialQuery = new URLSearchParams(window.location.search).get('q');
    if (initialQuery) {
      openSearch(initialQuery);
    }
  }

  function extractFormData(form) {
    var data = {};
    var formData = new FormData(form);
    formData.forEach(function (value, key) {
      if (typeof value === 'string') {
        data[key] = value.trim();
      }
    });
    return data;
  }

  function validateForm(form, fields) {
    var requiredFields = form.querySelectorAll('[name][required]');
    for (var i = 0; i < requiredFields.length; i += 1) {
      var field = requiredFields[i];
      var value = fields[field.name] || '';
      if (!value) {
        return field.name + ' is required.';
      }
      if (field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        return 'Please provide a valid email address.';
      }
    }
    return '';
  }

  function setFormStatus(form, message, state) {
    var status = form.querySelector('[data-local-form-status]');
    if (!status) {
      status = document.createElement('p');
      status.setAttribute('data-local-form-status', '');
      form.appendChild(status);
    }
    status.className = 'local-form-status local-form-status--' + state;
    status.textContent = message;
  }

  function initForms() {
    var forms = document.querySelectorAll('form[data-local-form], form.local-form');
    forms.forEach(function (form) {
      form.addEventListener('submit', function (event) {
        event.preventDefault();

        var fields = extractFormData(form);
        var validationMessage = validateForm(form, fields);
        if (validationMessage) {
          setFormStatus(form, validationMessage, 'error');
          return;
        }

        setFormStatus(form, 'Submitting...', 'pending');

        fetch('/api/forms', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            formId: form.getAttribute('data-local-form') || form.id || 'local-form',
            page: window.location.pathname,
            fields: fields,
          }),
        })
          .then(function (response) {
            return response.json().then(function (payload) {
              return { response: response, payload: payload };
            });
          })
          .then(function (result) {
            if (!result.response.ok || !result.payload.ok) {
              throw new Error(result.payload && result.payload.error ? result.payload.error : 'Unable to submit form.');
            }
            form.reset();
            setFormStatus(form, 'Thanks! Your feedback was saved locally.', 'success');
          })
          .catch(function (error) {
            setFormStatus(form, error.message || 'Unable to submit form.', 'error');
          });
      });
    });
  }

  function safeGetCompletionState() {
    var raw = window.localStorage.getItem(COURSE_PROGRESS_STORAGE_KEY);
    var parsed = raw ? safeJsonParse(raw, {}) : {};
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  }

  function saveCompletionState(state) {
    window.localStorage.setItem(COURSE_PROGRESS_STORAGE_KEY, JSON.stringify(state));
  }

  function normalizeCourseItemId(input) {
    return String(input || '').trim();
  }

  function getCourseItemCheckboxes() {
    return Array.from(document.querySelectorAll('input[type="checkbox"][data-course-item-id]'));
  }

  function getPageCourseItemIds() {
    var seen = {};
    var ids = [];
    getCourseItemCheckboxes().forEach(function (checkbox) {
      var id = normalizeCourseItemId(checkbox.getAttribute('data-course-item-id'));
      if (!id || seen[id]) {
        return;
      }
      seen[id] = true;
      ids.push(id);
    });
    return ids;
  }

  function syncCheckboxesForItem(itemId, checked, sourceCheckbox) {
    getCourseItemCheckboxes().forEach(function (checkbox) {
      if (checkbox === sourceCheckbox) {
        return;
      }
      if (normalizeCourseItemId(checkbox.getAttribute('data-course-item-id')) === itemId) {
        checkbox.checked = checked;
      }
    });
  }

  function updateProgressBarsForPage(completionState) {
    var ids = getPageCourseItemIds();
    var total = ids.length;
    var completed = 0;

    ids.forEach(function (id) {
      if (completionState[id]) {
        completed += 1;
      }
    });

    var percentage = total ? Math.round((completed / total) * 100) : 0;
    var bars = document.querySelectorAll('.course-list__progress-bar, .course-item__side-nav-progress-bar');
    bars.forEach(function (bar) {
      bar.style.width = percentage + '%';
      bar.setAttribute('aria-valuenow', String(percentage));
    });

    var labels = document.querySelectorAll('.course-list__progress-bar-percentage, .course-item__side-nav-progress-bar-percentage');
    labels.forEach(function (label) {
      label.textContent = percentage + '%';
    });

    var containers = document.querySelectorAll('.course-list__progress-bar-container, .course-item__side-nav-progress-bar-container');
    containers.forEach(function (container) {
      container.setAttribute('data-loaded', 'true');
    });
  }

  function setCompleteAndContinueLabel(button, isCurrentComplete, hasNext) {
    var incomplete = button.querySelector('.course-item__next-lesson-text--incomplete');
    var complete = button.querySelector('.course-item__next-lesson-text--complete');
    var paywall = button.querySelector('.course-item__next-lesson-text--paywall-link');

    if (incomplete) {
      incomplete.hidden = isCurrentComplete;
    }
    if (complete) {
      complete.hidden = !isCurrentComplete;
    }
    if (paywall) {
      paywall.hidden = true;
    }

    if (!hasNext) {
      button.setAttribute('aria-label', 'Back to Modules');
    }
  }

  function getCurrentCourseItemId() {
    var activeSegment = document.querySelector('.course-item__side-nav-segment.course-item__side-nav-lesson.active');
    if (activeSegment) {
      var activeCheckbox = activeSegment.querySelector('input[type="checkbox"][data-course-item-id]');
      if (activeCheckbox) {
        return normalizeCourseItemId(activeCheckbox.getAttribute('data-course-item-id'));
      }
    }

    var courseItemRoot = document.querySelector('.course-item[data-collection-context]');
    if (!courseItemRoot) {
      return '';
    }
    var contextRaw = courseItemRoot.getAttribute('data-collection-context');
    var context = safeJsonParse(contextRaw, {});
    return normalizeCourseItemId(context.id || '');
  }

  function getNextLessonHref() {
    var links = Array.from(document.querySelectorAll('.course-item__side-nav-segment.course-item__side-nav-lesson a.course-item__side-nav-link'));
    if (!links.length) {
      return '';
    }

    var currentPath = window.location.pathname.split('/').pop() || '';
    var currentIndex = -1;

    links.forEach(function (link, index) {
      if (currentIndex !== -1) {
        return;
      }
      var href = link.getAttribute('href') || '';
      var normalized = href.split('#')[0].split('?')[0].split('/').pop() || '';
      if (normalized === currentPath) {
        currentIndex = index;
      }
    });

    if (currentIndex === -1 || currentIndex + 1 >= links.length) {
      return '';
    }
    return links[currentIndex + 1].getAttribute('href') || '';
  }

  function refreshCompleteAndContinueButtons(completionState) {
    var buttons = document.querySelectorAll('[data-complete-and-continue]');
    if (!buttons.length) {
      return;
    }

    var currentItemId = getCurrentCourseItemId();
    var isCurrentComplete = currentItemId ? Boolean(completionState[currentItemId]) : false;
    var nextHref = getNextLessonHref();

    buttons.forEach(function (button) {
      var targetHref = nextHref || '../courses.html';
      button.setAttribute('href', targetHref);
      setCompleteAndContinueLabel(button, isCurrentComplete, Boolean(nextHref));
    });
  }

  function initCourseCompletionTracking() {
    var checkboxes = getCourseItemCheckboxes();
    if (!checkboxes.length) {
      return;
    }

    var completionState = safeGetCompletionState();

    checkboxes.forEach(function (checkbox) {
      var itemId = normalizeCourseItemId(checkbox.getAttribute('data-course-item-id'));
      checkbox.checked = Boolean(itemId && completionState[itemId]);
    });

    function refreshDerivedState() {
      updateProgressBarsForPage(completionState);
      refreshCompleteAndContinueButtons(completionState);
    }

    checkboxes.forEach(function (checkbox) {
      checkbox.addEventListener('change', function () {
        var itemId = normalizeCourseItemId(checkbox.getAttribute('data-course-item-id'));
        if (!itemId) {
          return;
        }
        completionState[itemId] = checkbox.checked;
        syncCheckboxesForItem(itemId, checkbox.checked, checkbox);
        saveCompletionState(completionState);
        refreshDerivedState();
      });
    });

    var continueButtons = document.querySelectorAll('[data-complete-and-continue]');
    continueButtons.forEach(function (button) {
      button.addEventListener('click', function (event) {
        event.preventDefault();
        var currentItemId = getCurrentCourseItemId();
        if (currentItemId) {
          completionState[currentItemId] = true;
          saveCompletionState(completionState);
          syncCheckboxesForItem(currentItemId, true);
        }
        updateProgressBarsForPage(completionState);
        refreshCompleteAndContinueButtons(completionState);
        var href = button.getAttribute('href') || '../courses.html';
        window.location.href = href;
      });
    });

    refreshDerivedState();
  }

  function initCourseListAccordions() {
    var triggers = document.querySelectorAll('.course-list__list-chapter-item-accordion-trigger');
    if (!triggers.length) {
      return;
    }

    triggers.forEach(function (trigger) {
      var item = trigger.closest('.course-list__list-chapter-item');
      if (!item) {
        return;
      }
      var contentId = trigger.getAttribute('aria-controls');
      var content = contentId ? document.getElementById(contentId) : item.querySelector('.course-list__list-chapter-item-accordion-content');

      function setExpanded(expanded) {
        item.setAttribute('data-expanded', expanded ? 'true' : 'false');
        trigger.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        if (content) {
          content.hidden = !expanded;
        }
      }

      var initiallyExpanded =
        item.getAttribute('data-expanded') !== 'false' &&
        trigger.getAttribute('aria-expanded') !== 'false';
      setExpanded(initiallyExpanded);

      trigger.addEventListener('click', function () {
        var expanded = trigger.getAttribute('aria-expanded') === 'true';
        setExpanded(!expanded);
      });

      trigger.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          var expanded = trigger.getAttribute('aria-expanded') === 'true';
          setExpanded(!expanded);
        }
      });
    });
  }

  function initCourseSideNavToggles() {
    var courseItem = document.querySelector('.course-item');
    if (!courseItem) {
      return;
    }

    var buttons = courseItem.querySelectorAll('.course-item__side-nav-toggle-button');
    if (!buttons.length) {
      return;
    }
    var backdrop = courseItem.querySelector('.course-item__side-nav-mobile-backdrop');
    var desktopQuery = window.matchMedia('(min-width: 992px)');

    function applyOpenState(isOpen) {
      courseItem.classList.toggle('nav-open', isOpen);
      courseItem.classList.toggle('nav-closed', !isOpen);
      courseItem.classList.remove('nav-loading');

      buttons.forEach(function (button) {
        button.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        var labelAttr = isOpen ? 'data-label-expanded' : 'data-label-collapsed';
        var label = button.getAttribute(labelAttr);
        if (label) {
          button.setAttribute('aria-label', label);
        }
      });
    }

    var initialOpen = desktopQuery.matches ? true : !courseItem.classList.contains('nav-closed');
    applyOpenState(initialOpen);

    if (typeof desktopQuery.addEventListener === 'function') {
      desktopQuery.addEventListener('change', function (event) {
        if (event.matches) {
          applyOpenState(true);
        } else {
          applyOpenState(false);
        }
      });
    }

    buttons.forEach(function (button) {
      button.addEventListener('click', function (event) {
        event.preventDefault();
        var isOpen = courseItem.classList.contains('nav-open');
        applyOpenState(!isOpen);
      });
    });

    if (backdrop) {
      backdrop.addEventListener('click', function () {
        applyOpenState(false);
      });
    }

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        applyOpenState(false);
      }
    });
  }

  function initLearningInteractions() {
    initCourseListAccordions();
    initCourseSideNavToggles();
    initCourseCompletionTracking();
  }

  function init() {
    initMenuToggle();
    updateCartBadge();
    initNonCommerceCart();
    initSearchUi();
    initForms();
    initLearningInteractions();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
