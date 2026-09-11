const telegram = window.Telegram?.WebApp;
telegram?.ready();
telegram?.expand();

const setScreen = (screen) => {
  document.querySelectorAll('.screen').forEach((item) => item.classList.toggle('is-active', item.dataset.screen === screen));
  document.querySelectorAll('.tab').forEach((item) => item.classList.toggle('is-active', item.dataset.tab === screen));
};
document.querySelectorAll('[data-tab]').forEach((button) => button.addEventListener('click', () => setScreen(button.dataset.tab)));
document.querySelectorAll('[data-select]').forEach((group) => group.addEventListener('click', (event) => {
  if (event.target.tagName !== 'BUTTON') return;
  group.querySelectorAll('button').forEach((button) => button.classList.toggle('is-selected', button === event.target));
}));

const user = telegram?.initDataUnsafe?.user;
if (user) {
  const name = user.first_name || 'Трейдер';
  document.querySelector('#welcome-name').textContent = name;
  document.querySelector('#profile-name').textContent = name;
  document.querySelector('#profile-initial').textContent = name.slice(0, 1).toUpperCase();
  fetch('/api/auth/telegram', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({init_data:telegram.initData}) }).catch(() => undefined);
}
document.querySelector('[data-action="signal"]').addEventListener('click', () => {
  const result = document.querySelector('#signal-result');
  document.querySelector('#signal-direction').textContent = '—';
  document.querySelector('#signal-probability').textContent = '—';
  document.querySelector('#signal-asset').textContent = 'Подключи торговый аккаунт, чтобы получить сигнал.';
  result.hidden = false;
});
