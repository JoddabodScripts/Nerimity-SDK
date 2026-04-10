(() => {
  const DURATION = 180;
  const content = () => document.querySelector('.md-content__inner');

  const TAB_ORDER = () =>
    [...document.querySelectorAll('.md-tabs__link')].map(a => a.href);

  let prevTabHref = null;
  let pendingClass = null;

  // Decide animation class on click, before nav happens
  document.addEventListener('click', e => {
    const tab = e.target.closest('.md-tabs__link');
    const side = e.target.closest('.md-nav__link');

    if (tab) {
      const tabs = TAB_ORDER();
      const prev = tabs.indexOf(prevTabHref);
      const next = tabs.indexOf(tab.href);
      pendingClass = next >= prev ? 'anim-left' : 'anim-right';
      prevTabHref = tab.href;
    } else if (side) {
      const rect = side.getBoundingClientRect();
      pendingClass = rect.top < window.innerHeight / 2 ? 'anim-up' : 'anim-down';
    }
  }, true);

  const run = () => {
    const el = content();
    if (!el) return;
    const cls = pendingClass || 'anim-fadein';
    pendingClass = null;
    // force reflow so animation restarts cleanly
    el.classList.remove('anim-left','anim-right','anim-up','anim-down','anim-fadein');
    void el.offsetWidth;
    el.classList.add(cls);
  };

  // First load
  document.addEventListener('DOMContentLoaded', () => {
    const tabs = TAB_ORDER();
    const active = document.querySelector('.md-tabs__link--active');
    prevTabHref = active ? active.href : tabs[0];
    pendingClass = 'anim-fadein';
    run();
  });

  // Every instant-nav swap — Material fires this
  document$.subscribe(() => run());
})();
