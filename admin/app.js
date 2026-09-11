const telegram = window.Telegram?.WebApp;

telegram?.ready();
telegram?.expand();

const state = {
  assets: [],
  editingAsset: null,
  editingProduct: null,
  products: [],
  user: null,
};

class ApiError extends Error {}

const $ = (selector) => document.querySelector(selector);
const money = (value) => `$${Number(value || 0).toLocaleString('ru-RU')}`;
const pac = (value) => `${Number(value || 0).toLocaleString('ru-RU')} PAC`;
const rate = (value) => value === null ? '—' : `${Number(value).toLocaleString('ru-RU')}%`;
const today = () => new Date().toISOString().slice(0, 10);

const api = async (path, options = {}) => {
  if (!telegram?.initData) throw new ApiError('Открой админку из Telegram Mini App.');
  const headers = new Headers(options.headers);
  headers.set('X-Telegram-Init-Data', telegram.initData);
  if (options.body) headers.set('Content-Type', 'application/json');
  const response = await fetch(path, { ...options, headers });
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(payload?.detail || 'Не удалось выполнить запрос.');
  return payload;
};

const showOverlay = (title, message) => {
  $('#overlay-title').textContent = title;
  $('#overlay-message').textContent = message;
  $('#access-overlay').hidden = false;
};

let toastTimer;
const showToast = (message, isError = false) => {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.toggle('is-error', isError);
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
};

const createButton = (label, className = '') => {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = className;
  button.textContent = label;
  return button;
};

const readNullableNumber = (form, name) => {
  const value = form.elements[name].value.trim();
  return value === '' ? null : Number(value);
};

const renderDashboard = (dashboard) => {
  $('[data-metric="registrations"]').textContent = dashboard.registrations;
  $('[data-metric="first-deposits"]').textContent = dashboard.first_deposits;
  $('[data-metric="first-deposit-amount"]').textContent = money(dashboard.first_deposit_amount);
  $('[data-metric="repeat-deposits"]').textContent = dashboard.repeat_deposits;
  $('[data-metric="repeat-deposit-amount"]').textContent = money(dashboard.repeat_deposit_amount);
  $('[data-metric="signals"]').textContent = dashboard.signals;
  $('[data-metric="diary-entries"]').textContent = dashboard.diary_entries;
  $('[data-metric="active-users"]').textContent = dashboard.active_users;
  $('[data-metric="registration-fd-rate"]').textContent = rate(dashboard.registration_to_first_deposit_rate);
  $('[data-metric="fd-rd-rate"]').textContent = rate(dashboard.first_to_repeat_deposit_rate);
  $('#dashboard-period').textContent = `Период: ${dashboard.date_from} — ${dashboard.date_to} UTC`;
};

const loadDashboard = async () => {
  const params = new URLSearchParams({
    date_from: $('#date-from').value,
    date_to: $('#date-to').value,
  });
  try {
    renderDashboard(await api(`/api/admin/dashboard?${params}`));
  } catch (error) {
    showToast(error.message, true);
  }
};

const renderUser = () => {
  const root = $('#user-result');
  root.replaceChildren();
  if (!state.user) return;
  const user = state.user;
  const card = document.createElement('article');
  card.className = 'user-card';
  const head = document.createElement('div');
  head.className = 'user-card__head';
  const title = document.createElement('div');
  const name = document.createElement('h3');
  name.textContent = user.name || 'Без имени';
  const handle = document.createElement('p');
  handle.className = 'muted';
  handle.textContent = `${user.username ? `@${user.username} · ` : ''}${user.telegram_id}`;
  title.append(name, handle);
  const access = document.createElement('span');
  access.className = user.is_blocked ? 'muted' : '';
  access.textContent = user.is_blocked ? 'Доступ ограничен' : 'Доступ активен';
  head.append(title, access);
  const stats = document.createElement('div');
  stats.className = 'user-stats';
  [['Статус', user.status], ['Депозиты', money(user.total_deposits)], ['Баланс', pac(user.pac_balance)]].forEach(([label, value]) => {
    const item = document.createElement('div');
    const labelElement = document.createElement('span');
    labelElement.textContent = label;
    const valueElement = document.createElement('strong');
    valueElement.textContent = value;
    item.append(labelElement, valueElement);
    stats.append(item);
  });
  const controls = document.createElement('form');
  controls.className = 'inline-form';
  const reason = document.createElement('input');
  reason.placeholder = 'Причина ручной блокировки';
  reason.maxLength = 500;
  reason.value = user.manual_block_reason || '';
  const button = createButton(user.is_manually_blocked ? 'Снять ручную блокировку' : 'Заблокировать вручную', user.is_manually_blocked ? 'ghost-button' : 'danger-button');
  button.type = 'submit';
  controls.append(reason, button);
  controls.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!user.is_manually_blocked && !reason.value.trim()) {
      showToast('Укажи причину блокировки.', true);
      return;
    }
    button.disabled = true;
    try {
      state.user = await api(`/api/admin/users/${encodeURIComponent(String(user.telegram_id))}/block`, {
        method: 'PATCH',
        body: JSON.stringify({ is_blocked: !user.is_manually_blocked, reason: reason.value.trim() || null }),
      });
      renderUser();
      showToast('Доступ пользователя обновлён.');
    } catch (error) {
      button.disabled = false;
      showToast(error.message, true);
    }
  });
  card.append(head, stats, controls);
  root.append(card);
};

const renderProducts = () => {
  const root = $('#product-list');
  root.replaceChildren();
  state.products.forEach((product) => {
    const row = document.createElement('tr');
    const info = document.createElement('td');
    const title = document.createElement('strong');
    title.textContent = product.title;
    const detail = document.createElement('span');
    detail.textContent = `${product.product_type} · ${product.price_pac === null ? product.grant_condition : pac(product.price_pac)}`;
    info.append(title, detail);
    const access = document.createElement('td');
    access.textContent = product.is_published ? 'Опубликован' : 'Архив';
    const actions = document.createElement('td');
    actions.className = 'row-actions';
    const edit = createButton('Изменить', 'ghost-button');
    edit.addEventListener('click', () => startProductEdit(product));
    const archive = createButton('Архив', 'danger-button');
    archive.disabled = !product.is_published;
    archive.addEventListener('click', () => archiveProduct(product));
    actions.append(edit, archive);
    row.append(info, access, actions);
    root.append(row);
  });
};

const productPayload = (form) => ({
  title: form.elements.title.value.trim(),
  description: form.elements.description.value.trim() || null,
  product_type: form.elements.product_type.value,
  price_pac: readNullableNumber(form, 'price_pac'),
  grant_condition: form.elements.grant_condition.value,
  grant_deposit_threshold: readNullableNumber(form, 'grant_deposit_threshold'),
  external_url: form.elements.external_url.value.trim() || null,
  is_published: form.elements.is_published.checked,
  sort_order: Number(form.elements.sort_order.value || 0),
});

const resetProductEditor = () => {
  state.editingProduct = null;
  const form = $('#product-editor');
  form.reset();
  form.elements.is_published.checked = true;
  form.elements.sort_order.value = 0;
  $('#product-submit').textContent = 'Создать товар';
  $('#cancel-product-edit').hidden = true;
};

const startProductEdit = (product) => {
  state.editingProduct = product;
  const form = $('#product-editor');
  Object.entries(product).forEach(([name, value]) => {
    if (!form.elements[name]) return;
    if (form.elements[name].type === 'checkbox') form.elements[name].checked = value;
    else form.elements[name].value = value ?? '';
  });
  $('#product-submit').textContent = 'Сохранить товар';
  $('#cancel-product-edit').hidden = false;
  form.scrollIntoView({ behavior: 'smooth', block: 'center' });
};

const saveProduct = async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = $('#product-submit');
  button.disabled = true;
  try {
    const payload = productPayload(form);
    if (state.editingProduct) {
      await api(`/api/admin/products/${state.editingProduct.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
      showToast('Товар обновлён.');
    } else {
      await api('/api/admin/products', { method: 'POST', body: JSON.stringify(payload) });
      showToast('Товар создан.');
    }
    state.products = (await api('/api/admin/products')).products;
    renderProducts();
    resetProductEditor();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    button.disabled = false;
  }
};

const archiveProduct = async (product) => {
  if (!window.confirm(`Отправить «${product.title}» в архив?`)) return;
  try {
    await api(`/api/admin/products/${product.id}`, { method: 'DELETE' });
    state.products = (await api('/api/admin/products')).products;
    renderProducts();
    showToast('Товар отправлен в архив.');
  } catch (error) {
    showToast(error.message, true);
  }
};

const renderAssets = () => {
  const root = $('#asset-list');
  root.replaceChildren();
  state.assets.forEach((asset) => {
    const row = document.createElement('tr');
    const info = document.createElement('td');
    const title = document.createElement('strong');
    title.textContent = asset.label;
    const detail = document.createElement('span');
    detail.textContent = `${asset.asset_key}${asset.is_active ? '' : ' · неактивна'}`;
    info.append(title, detail);
    const category = document.createElement('td');
    category.textContent = asset.category;
    const actions = document.createElement('td');
    actions.className = 'row-actions';
    const edit = createButton('Изменить', 'ghost-button');
    edit.addEventListener('click', () => startAssetEdit(asset));
    actions.append(edit);
    row.append(info, category, actions);
    root.append(row);
  });
};

const assetPayload = (form, editing) => ({
  ...(editing ? {} : { asset_key: form.elements.asset_key.value.trim() }),
  label: form.elements.label.value.trim(),
  category: form.elements.category.value.trim(),
  is_otc: form.elements.is_otc.checked,
  is_popular: form.elements.is_popular.checked,
  ...(editing ? { is_active: form.elements.is_active.checked } : {}),
  sort_order: Number(form.elements.sort_order.value || 0),
});

const resetAssetEditor = () => {
  state.editingAsset = null;
  const form = $('#asset-editor');
  form.reset();
  form.elements.category.value = 'forex';
  form.elements.sort_order.value = 0;
  form.elements.asset_key.disabled = false;
  $('#asset-active-field').hidden = true;
  $('#asset-submit').textContent = 'Добавить пару';
  $('#cancel-asset-edit').hidden = true;
};

const startAssetEdit = (asset) => {
  state.editingAsset = asset;
  const form = $('#asset-editor');
  Object.entries(asset).forEach(([name, value]) => {
    if (!form.elements[name]) return;
    if (form.elements[name].type === 'checkbox') form.elements[name].checked = value;
    else form.elements[name].value = value ?? '';
  });
  form.elements.asset_key.disabled = true;
  $('#asset-active-field').hidden = false;
  $('#asset-submit').textContent = 'Сохранить пару';
  $('#cancel-asset-edit').hidden = false;
  form.scrollIntoView({ behavior: 'smooth', block: 'center' });
};

const saveAsset = async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = $('#asset-submit');
  button.disabled = true;
  try {
    const payload = assetPayload(form, state.editingAsset);
    if (state.editingAsset) {
      await api(`/api/admin/signal-assets/${state.editingAsset.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
      showToast('Пара обновлена.');
    } else {
      await api('/api/admin/signal-assets', { method: 'POST', body: JSON.stringify(payload) });
      showToast('Пара добавлена.');
    }
    state.assets = (await api('/api/admin/signal-assets')).assets;
    renderAssets();
    resetAssetEditor();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    button.disabled = false;
  }
};

const loadSettings = async () => {
  const settings = await api('/api/admin/settings');
  const form = $('#settings-editor');
  Object.entries(settings).forEach(([name, value]) => {
    if (form.elements[name]) form.elements[name].value = value ?? '';
  });
};

const saveSettings = async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    await api('/api/admin/settings', {
      method: 'PUT',
      body: JSON.stringify({
        minimum_first_deposit: Number(form.elements.minimum_first_deposit.value),
        premium_minimum_deposit: Number(form.elements.premium_minimum_deposit.value),
        premium_daily_limit: Number(form.elements.premium_daily_limit.value),
        manager_telegram_url: form.elements.manager_telegram_url.value.trim() || null,
      }),
    });
    showToast('Настройки сохранены.');
  } catch (error) {
    showToast(error.message, true);
  } finally {
    button.disabled = false;
  }
};

const bindEvents = () => {
  $('#dashboard-filter').addEventListener('submit', (event) => { event.preventDefault(); loadDashboard(); });
  $('#user-search').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      state.user = await api(`/api/admin/users/${encodeURIComponent($('#user-identifier').value.trim())}`);
      renderUser();
    } catch (error) {
      state.user = null;
      $('#user-result').textContent = error.message;
    }
  });
  $('#product-editor').addEventListener('submit', saveProduct);
  $('#asset-editor').addEventListener('submit', saveAsset);
  $('#settings-editor').addEventListener('submit', saveSettings);
  $('#cancel-product-edit').addEventListener('click', resetProductEditor);
  $('#cancel-asset-edit').addEventListener('click', resetAssetEditor);
};

const bootstrap = async () => {
  $('#date-from').value = today();
  $('#date-to').value = today();
  bindEvents();
  if (!telegram?.initData) {
    showOverlay('Открой админку в Telegram', 'Для безопасной проверки прав нужен Telegram Mini App.');
    return;
  }
  try {
    const [dashboard, products, assets] = await Promise.all([
      api(`/api/admin/dashboard?date_from=${$('#date-from').value}&date_to=${$('#date-to').value}`),
      api('/api/admin/products'),
      api('/api/admin/signal-assets'),
      loadSettings(),
    ]);
    renderDashboard(dashboard);
    state.products = products.products;
    state.assets = assets.assets;
    renderProducts();
    renderAssets();
  } catch (error) {
    showOverlay('Не удалось открыть админку', error.message);
  }
};

bootstrap();
