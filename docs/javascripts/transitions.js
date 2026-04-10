(() => {
  const CLASSES = ['anim-left','anim-right','anim-up','anim-down','anim-fadein',
                   'exit-left','exit-right','exit-up','exit-down'];

  const EXIT = { 'anim-left':'exit-left', 'anim-right':'exit-right',
                 'anim-up':'exit-up',     'anim-down':'exit-down', 'anim-fadein':'exit-up' };

  const SIDE_SEL = 'a.md-nav__link:not(.md-tabs__link)';

  const play = (cls) => {
    const el = document.querySelector('.md-content__inner');
    if (!el) return;
    const clone = el.cloneNode(true);
    CLASSES.forEach(c => clone.classList.remove(c));
    clone.classList.add(cls);
    el.replaceWith(clone);
  };

  const tabIndex = (pathname) => {
    const tabs = [...document.querySelectorAll('.md-tabs__link')];
    const base = new URL(tabs[0].href).pathname;
    let best = -1, bestLen = -1;
    tabs.forEach((a, i) => {
      const tp = new URL(a.href).pathname;
      if (tp === base && pathname !== base) return;
      if (pathname.startsWith(tp) && tp.length > bestLen) {
        best = i; bestLen = tp.length;
      }
    });
    return best;
  };

  const sideIndex = (el) => {
    const all = [...document.querySelectorAll(SIDE_SEL)];
    return all.indexOf(el);
  };

  const currentSideIndex = () => {
    const all = [...document.querySelectorAll(SIDE_SEL)];
    return all.findIndex(a => {
      try { return new URL(a.href).pathname === location.pathname; } catch { return false; }
    });
  };

  let pendingEnter = null;
  let pendingExit  = null;

  document.addEventListener('click', e => {
    const tab  = e.target.closest('.md-tabs__link');
    const side = e.target.closest(SIDE_SEL);

    if (tab) {
      const pi = tabIndex(location.pathname);
      const ni = tabIndex(new URL(tab.href).pathname);
      pendingEnter = ni > pi ? 'anim-right' : 'anim-left';
    } else if (side) {
      const ci = currentSideIndex();
      const ni = sideIndex(side);
      pendingEnter = ni > ci ? 'anim-down' : 'anim-up';
    } else {
      return;
    }

    // Phase 1: exit animation on current content
    pendingExit = EXIT[pendingEnter];
    const el = document.querySelector('.md-content__inner');
    if (el) {
      el.classList.remove(...CLASSES);
      void el.offsetWidth;
      el.classList.add(pendingExit);
    }
  }, true);

  const init = () => {
    play('anim-fadein');
    window.document$.subscribe(() => {
      play(pendingEnter || 'anim-fadein');
      pendingEnter = null;
      pendingExit  = null;
    });
  };

  if (window.document$) {
    init();
  } else {
    const iv = setInterval(() => {
      if (window.document$) { clearInterval(iv); init(); }
    }, 10);
  }
})();
