(() => {
  const DURATION = 180;
  const getEl = () => document.querySelector('.md-content__inner');

  const CLASSES = ['anim-left','anim-right','anim-up','anim-down','anim-fadein'];

  const play = (cls) => {
    const el = getEl();
    if (!el) return;
    el.classList.remove(...CLASSES);
    void el.offsetWidth; // force reflow
    el.classList.add(cls);
  };

  // Tab hrefs in order — used to detect left/right direction
  const tabHrefs = () =>
    [...document.querySelectorAll('.md-tabs__link')].map(a => a.href);

  let prevHref = location.href;
  let pendingClass = null;

  // Intercept clicks before navigation
  document.addEventListener('click', e => {
    const tab  = e.target.closest('.md-tabs__link');
    const side = e.target.closest('.md-nav__link:not(.md-tabs__link)');

    if (tab) {
      const tabs = tabHrefs();
      const pi = tabs.findIndex(h => h === prevHref || prevHref.startsWith(h));
      const ni = tabs.indexOf(tab.href);
      pendingClass = (ni >= pi) ? 'anim-left' : 'anim-right';
    } else if (side) {
      const rect = side.getBoundingClientRect();
      pendingClass = rect.top < window.innerHeight / 2 ? 'anim-up' : 'anim-down';
    }
  }, true);

  // Hook pushState (Material instant nav uses this)
  const _push = history.pushState.bind(history);
  history.pushState = (...args) => {
    _push(...args);
    prevHref = location.href;
    // Content isn't in DOM yet — wait one frame
    requestAnimationFrame(() => {
      requestAnimationFrame(() => play(pendingClass || 'anim-fadein'));
    });
    pendingClass = null;
  };

  // popstate (back/forward buttons)
  window.addEventListener('popstate', () => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => play('anim-fadein'));
    });
    prevHref = location.href;
  });

  // First load
  document.addEventListener('DOMContentLoaded', () => {
    prevHref = location.href;
    play('anim-fadein');
  });
})();
