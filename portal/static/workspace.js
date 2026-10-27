/* Shared navigation behavior. No third-party scripts or client data storage. */
(() => {
  const toggle = document.getElementById('navToggle');
  const sidebar = document.getElementById('workspaceSidebar');
  const backdrop = document.getElementById('navBackdrop');
  const content = document.querySelector('.workspace-body');
  const mobile = window.matchMedia('(max-width: 1024px)');
  let previousFocus;
  const syncVisibility = () => {
    const open = document.body.classList.contains('navigation-open');
    sidebar.inert = mobile.matches && !open;
    content.inert = mobile.matches && open;
    if (sidebar.inert) sidebar.setAttribute('aria-hidden', 'true');
    else sidebar.removeAttribute('aria-hidden');
    if (mobile.matches && open) { sidebar.setAttribute('role', 'dialog'); sidebar.setAttribute('aria-modal', 'true'); }
    else { sidebar.removeAttribute('role'); sidebar.removeAttribute('aria-modal'); }
  };
  const close = () => {
    document.body.classList.remove('navigation-open');
    toggle.setAttribute('aria-expanded', 'false');
    backdrop.hidden = true;
    syncVisibility();
    if (previousFocus) previousFocus.focus();
  };
  toggle.addEventListener('click', () => {
    if (document.body.classList.contains('navigation-open')) return close();
    previousFocus = document.activeElement;
    document.body.classList.add('navigation-open');
    toggle.setAttribute('aria-expanded', 'true');
    backdrop.hidden = false;
    syncVisibility();
    sidebar.querySelector('a').focus();
  });
  backdrop.addEventListener('click', close);
  document.getElementById('navClose').addEventListener('click', close);
  document.addEventListener('keydown', event => {
    if (!document.body.classList.contains('navigation-open')) return;
    if (event.key === 'Escape') close();
    if (event.key === 'Tab') {
      const links = [...sidebar.querySelectorAll('a, button')];
      const first = links[0], last = links[links.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  mobile.addEventListener('change', () => { close(); syncVisibility(); });
  syncVisibility();
})();
