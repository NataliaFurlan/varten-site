const header = document.getElementById('nav');
const menuButton = document.getElementById('menuBtn');
const navigation = document.getElementById('navLinks');
const mobileLayout = window.matchMedia('(max-width: 900px)');

function setMenu(open, restoreFocus = false) {
  navigation.classList.toggle('open', open);
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  if (restoreFocus) menuButton.focus();
}

menuButton.addEventListener('click', () => {
  setMenu(menuButton.getAttribute('aria-expanded') !== 'true');
});
header.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => setMenu(false));
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') {
    setMenu(false, true);
  }
});
document.addEventListener('click', (event) => {
  if (!header.contains(event.target)) setMenu(false);
});
mobileLayout.addEventListener('change', () => setMenu(false));

function updateHeader() {
  header.classList.toggle('scrolled', window.scrollY > 16);
}
window.addEventListener('scroll', updateHeader, { passive: true });
updateHeader();
document.getElementById('year').textContent = new Date().getFullYear();

// Keep the navigation state synchronized with the section in view.
if ('IntersectionObserver' in window) {
  const links = [...navigation.querySelectorAll('a[href^="#"]')];
  const observer = new IntersectionObserver((entries) => {
    const current = entries.filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!current) return;
    links.forEach((link) => {
      if (link.getAttribute('href') === `#${current.target.id}`) {
        link.setAttribute('aria-current', 'location');
      } else {
        link.removeAttribute('aria-current');
      }
    });
  }, { rootMargin: '-20% 0px -45% 0px', threshold: 0 });
  document.querySelectorAll('main section[id]').forEach((section) => observer.observe(section));
}
