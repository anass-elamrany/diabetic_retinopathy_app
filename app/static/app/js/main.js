const sidebar = document.getElementById('sidebar');
const menuButton = document.getElementById('menu-button');
const scrim = document.getElementById('sidebar-scrim');

if (sidebar && menuButton && scrim) {
  function setMenuOpen(open) {
    sidebar.classList.toggle('is-open', open);
    menuButton.setAttribute('aria-expanded', String(open));
    scrim.hidden = !open;
  }

  menuButton.addEventListener('click', () => setMenuOpen(!sidebar.classList.contains('is-open')));
  scrim.addEventListener('click', () => setMenuOpen(false));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') setMenuOpen(false);
  });
}
