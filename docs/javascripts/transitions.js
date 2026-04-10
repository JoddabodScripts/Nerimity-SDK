(() => {
  const CLASSES = ['anim-left','anim-right','anim-up','anim-down','anim-fadein'];

  const play = (cls) => {
    const el = document.querySelector('.md-content__inner');
    if (!el) return;
    el.classList.remove(...CLASSES);
    void el.offsetWidth;
    el.classList.add(cls);
  };

  // Return index of which tab "owns" a given pathname
  const tabIndex = (pathname) => {
    const tabs = [...document.querySelectorAll('.md-tabs__link')];
    // find the longest matching tab prefix
    let best = -1, bestLen = -1;
    tabs.forEach((a, i) => {
      const tp = new URL(a.href).pathname;
      if (pathname.startsWith(tp) && tp.length > bestLen) {
        best = i; bestLen = tp.length;
      }
    });
    return best;
  };

  let pendingClass = null;

  document.addEventListener('click', e => {
    const tab  = e.target.closest('.md-tabs__link');
    const side = e.target.closest('.md-nav__link:not(.md-tabs__link)');

    if (tab) {
      const pi = tabIndex(location.pathname);
      const ni = tabIndex(new URL(tab.href).pathname);
      pendingClass = ni >= pi ? 'anim-left' : 'anim-right';
    } else if (side) {
      const rect = side.getBoundingClientRect();
      pendingClass = rect.top < window.innerHeight / 2 ? 'anim-up' : 'anim-down';
    }
  }, true);

  const init = () => {
    play('anim-fadein');
    window.document$.subscribe(() => {
      play(pendingClass || 'anim-fadein');
      pendingClass = null;
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
