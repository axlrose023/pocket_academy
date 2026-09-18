const telegram = window.Telegram?.WebApp;

telegram?.ready();
telegram?.expand();

const state = {
  assets: [],
  editingAsset: null,
  editingMaterial: null,
  editingProduct: null,
  materials: [],
  products: [],
  user: null,
  userDiary: null,
};

class ApiError extends Error {}

const $ = (selector) => document.querySelector(selector);
const money = (value) => `$${Number(value || 0).toLocaleString('ru-RU')}`;
const pac = (value) => `${Number(value || 0).toLocaleString('ru-RU')} PAC`;
const rate = (value) => value === null ? '—' : `${Number(value).toLocaleString('ru-RU')}%`;
const average = (value) => value === null ? '—' : Number(value).toLocaleString('ru-RU', { maximumFractionDigits: 2 });
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
  $('[data-metric="leads"]').textContent = dashboard.leads;
  $('[data-metric="registrations"]').textContent = dashboard.registrations;
  $('[data-metric="deposit-count"]').textContent = dashboard.deposit_count;
  $('[data-metric="deposit-amount"]').textContent = money(dashboard.deposit_amount);
  $('[data-metric="first-deposits"]').textContent = dashboard.first_deposits;
  $('[data-metric="first-deposit-amount"]').textContent = money(dashboard.first_deposit_amount);
  $('[data-metric="repeat-deposits"]').textContent = dashboard.repeat_deposits;
  $('[data-metric="repeat-deposit-amount"]').textContent = money(dashboard.repeat_deposit_amount);
  $('[data-metric="signals"]').textContent = dashboard.signals;
  $('[data-metric="diary-entries"]').textContent = dashboard.diary_entries;
  $('[data-metric="active-users"]').textContent = dashboard.active_users;
  $('[data-metric="webapp-opens"]').textContent = dashboard.webapp_opens;
  $('[data-metric="registration-fd-rate"]').textContent = rate(dashboard.registration_to_first_deposit_rate);
  $('[data-metric="fd-rd-rate"]').textContent = rate(dashboard.first_to_repeat_deposit_rate);
  $('[data-metric="lead-registration-rate"]').textContent = rate(dashboard.lead_to_registration_rate);
  $('[data-metric="lead-fd-rate"]').textContent = rate(dashboard.lead_to_first_deposit_rate);
  $('[data-metric="diary-trades"]').textContent = `${average(dashboard.diary_average_profitable_trades)} / ${average(dashboard.diary_average_losing_trades)}`;
  const mood = dashboard.diary_average_mood === null ? 'Нет оценок' : `Среднее настроение ${average(dashboard.diary_average_mood)} · 1–5: ${dashboard.diary_mood_distribution.join(' / ')} · всего ${dashboard.diary_entries}`;
  $('[data-metric="diary-mood"]').textContent = mood;
  $('#dashboard-period').textContent = `Период: ${dashboard.date_from} — ${dashboard.date_to} UTC · ${({ day: 'по дням', week: 'по неделям', month: 'по месяцам' })[dashboard.granularity]}`;
  renderDashboardSeries(dashboard.series);
};

const renderDashboardSeries = (series) => {
  const root = $('#dashboard-series');
  root.replaceChildren();
  series.forEach((point) => {
    const row = document.createElement('tr');
    [
      point.period_start,
      point.leads,
      point.registrations,
      `${point.deposit_count} · ${money(point.deposit_amount)}`,
      `${point.first_deposits} · ${money(point.first_deposit_amount)}`,
      `${point.repeat_deposits} · ${money(point.repeat_deposit_amount)}`,
      point.webapp_opens,
      point.signals,
      point.diary_entries,
    ].forEach((value) => {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.append(cell);
    });
    root.append(row);
  });
};

const loadDashboard = async () => {
  const params = new URLSearchParams({
    date_from: $('#date-from').value,
    date_to: $('#date-to').value,
    granularity: $('#dashboard-granularity').value,
  });
  try {
    renderDashboard(await api(`/api/admin/dashboard?${params}`));
  } catch (error) {
    showToast(error.message, true);
  }
};

const renderUserList = (users) => {
  const root = $('#user-filter-list');
  root.replaceChildren();
  if (!users.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 5;
    cell.textContent = 'Пользователи по заданным условиям не найдены.';
    row.append(cell);
    root.append(row);
    return;
  }
  users.forEach((user) => {
    const row = document.createElement('tr');
    const identity = document.createElement('td');
    const name = document.createElement('strong');
    name.textContent = user.name || 'Без имени';
    const handle = document.createElement('span');
    handle.textContent = `${user.username ? `@${user.username} · ` : ''}${user.telegram_id}`;
    identity.append(name, handle);
    const status = document.createElement('td');
    status.textContent = user.status;
    const deposits = document.createElement('td');
    deposits.textContent = money(user.total_deposits);
    const registered = document.createElement('td');
    registered.textContent = user.registered_at ? new Date(user.registered_at).toLocaleDateString('ru-RU') : '—';
    const actions = document.createElement('td');
    const open = createButton('Открыть', 'ghost-button');
    open.addEventListener('click', () => { void loadUser(String(user.telegram_id)); });
    actions.append(open);
    row.append(identity, status, deposits, registered, actions);
    root.append(row);
  });
};

const userFilterParams = () => {
  const form = $('#user-filter');
  const params = new URLSearchParams({ limit: '50' });
  ['user_status', 'registered_from', 'registered_to', 'minimum_deposits', 'maximum_deposits'].forEach((name) => {
    const value = form.elements[name].value.trim();
    if (value) params.set(name, value);
  });
  return params;
};

const loadUserList = async () => {
  try {
    const payload = await api(`/api/admin/users/list?${userFilterParams()}`);
    renderUserList(payload.users);
  } catch (error) {
    showToast(error.message, true);
  }
};

const renderUserDiary = (report) => {
  if (!report) return null;
  const section = document.createElement('section');
  section.className = 'user-diary';
  const heading = document.createElement('h4');
  heading.textContent = 'Дневник трейдера · последние 30 дней';
  const summary = document.createElement('p');
  summary.className = 'muted';
  summary.textContent = report.entry_count
    ? `Записей: ${report.entry_count} · среднее профит / убыток: ${average(report.average_profitable_trades)} / ${average(report.average_losing_trades)} · настроение: ${average(report.average_mood)} · 1–5: ${report.mood_distribution.join(' / ')}`
    : 'За последние 30 дней записей нет.';
  section.append(heading, summary);
  if (report.series.length) {
    const series = document.createElement('div');
    series.className = 'table-wrap';
    const table = document.createElement('table');
    const head = document.createElement('thead');
    const headRow = document.createElement('tr');
    ['Неделя', 'Записи', 'Ср. профит', 'Ср. убыток', 'Настроение'].forEach((label) => {
      const cell = document.createElement('th');
      cell.textContent = label;
      headRow.append(cell);
    });
    head.append(headRow);
    const body = document.createElement('tbody');
    report.series.forEach((point) => {
      const row = document.createElement('tr');
      [point.period_start, point.entry_count, average(point.average_profitable_trades), average(point.average_losing_trades), average(point.average_mood)].forEach((value) => {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      });
      body.append(row);
    });
    table.append(head, body);
    series.append(table);
    section.append(series);
  }
  if (report.entries.length) {
    const details = document.createElement('details');
    const title = document.createElement('summary');
    title.textContent = `Показать записи (${report.entries.length})`;
    details.append(title);
    report.entries.forEach((entry) => {
      const item = document.createElement('p');
      item.className = 'muted';
      item.textContent = `${entry.entry_day} · +${entry.profitable_trades} / −${entry.losing_trades} · настроение ${entry.mood}${entry.comment ? ` · ${entry.comment}` : ''}`;
      details.append(item);
    });
    section.append(details);
  }
  return section;
};

const loadUser = async (identifier) => {
  const result = $('#user-result');
  result.textContent = 'Загружаем карточку пользователя…';
  try {
    const params = new URLSearchParams({ identifier });
    const user = await api(`/api/admin/users?${params}`);
    const diary = await api(`/api/admin/users/${encodeURIComponent(String(user.telegram_id))}/diary?granularity=week`);
    state.user = user;
    state.userDiary = diary;
    $('#user-identifier').value = identifier;
    renderUser();
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    state.user = null;
    state.userDiary = null;
    result.textContent = error.message;
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
  const identifiers = document.createElement('p');
  identifiers.className = 'muted';
  identifiers.textContent = [
    user.trader_ids.length ? `Trader: ${user.trader_ids.join(', ')}` : null,
    user.click_id ? `Click: ${user.click_id}` : null,
  ].filter(Boolean).join(' · ') || 'Данных о связке с Pocket Option пока нет';
  title.append(identifiers);
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
  const nextBlock = !user.is_blocked;
  const button = createButton(
    nextBlock ? 'Заблокировать вручную' : 'Разблокировать вручную',
    nextBlock ? 'danger-button' : 'ghost-button',
  );
  button.type = 'submit';
  controls.append(reason, button);
  controls.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (nextBlock && !reason.value.trim()) {
      showToast('Укажи причину блокировки.', true);
      return;
    }
    button.disabled = true;
    try {
      state.user = await api(`/api/admin/users/${encodeURIComponent(String(user.telegram_id))}/block`, {
        method: 'PATCH',
        body: JSON.stringify({ is_blocked: nextBlock, reason: reason.value.trim() || null }),
      });
      renderUser();
      showToast('Доступ пользователя обновлён.');
    } catch (error) {
      button.disabled = false;
      showToast(error.message, true);
    }
  });
  const testAccessControls = document.createElement('form');
  testAccessControls.className = 'inline-form';
  const testAccessDescription = document.createElement('span');
  testAccessDescription.className = 'muted';
  testAccessDescription.textContent = user.is_test_access
    ? 'Тестовый доступ включён: можно проверять сигналы без регистрации и депозита.'
    : 'Тестовый доступ даёт возможность проверять сигналы без регистрации и депозита.';
  const nextTestAccess = !user.is_test_access;
  const testAccessButton = createButton(
    nextTestAccess ? 'Открыть тестовый доступ' : 'Закрыть тестовый доступ',
    nextTestAccess ? '' : 'ghost-button',
  );
  testAccessButton.type = 'submit';
  testAccessControls.append(testAccessDescription, testAccessButton);
  testAccessControls.addEventListener('submit', async (event) => {
    event.preventDefault();
    testAccessButton.disabled = true;
    try {
      state.user = await api(`/api/admin/users/${encodeURIComponent(String(user.telegram_id))}/test-access`, {
        method: 'PATCH',
        body: JSON.stringify({ is_test_access: nextTestAccess }),
      });
      renderUser();
      showToast(nextTestAccess ? 'Тестовый доступ открыт.' : 'Тестовый доступ закрыт.');
    } catch (error) {
      testAccessButton.disabled = false;
      showToast(error.message, true);
    }
  });
  const diary = renderUserDiary(state.userDiary);
  card.append(head, stats);
  if (diary) card.append(diary);
  card.append(controls, testAccessControls);
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
  state.materials = [];
  state.editingMaterial = null;
  const form = $('#product-editor');
  form.reset();
  form.elements.is_published.checked = true;
  form.elements.sort_order.value = 0;
  $('#product-submit').textContent = 'Создать товар';
  $('#cancel-product-edit').hidden = true;
  $('#materials-editor').hidden = true;
};

const startProductEdit = async (product) => {
  state.editingProduct = product;
  const form = $('#product-editor');
  Object.entries(product).forEach(([name, value]) => {
    if (!form.elements[name]) return;
    if (form.elements[name].type === 'checkbox') form.elements[name].checked = value;
    else form.elements[name].value = value ?? '';
  });
  $('#product-submit').textContent = 'Сохранить товар';
  $('#cancel-product-edit').hidden = false;
  $('#materials-editor').hidden = false;
  $('#materials-title').textContent = `Уроки: ${product.title}`;
  await loadMaterials(product);
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

const renderMaterials = () => {
  const root = $('#material-admin-list');
  root.replaceChildren();
  state.materials.forEach((material) => {
    const row = document.createElement('tr');
    const info = document.createElement('td');
    const title = document.createElement('strong');
    title.textContent = material.title;
    const detail = document.createElement('span');
    detail.textContent = material.content_type;
    info.append(title, detail);
    const source = document.createElement('td');
    source.textContent = material.external_url ? 'Внешняя ссылка' : 'S3 key';
    const actions = document.createElement('td');
    actions.className = 'row-actions';
    const edit = createButton('Изменить', 'ghost-button');
    edit.addEventListener('click', () => startMaterialEdit(material));
    const remove = createButton('Удалить', 'danger-button');
    remove.addEventListener('click', () => deleteMaterial(material));
    actions.append(edit, remove);
    row.append(info, source, actions);
    root.append(row);
  });
};

const loadMaterials = async (product) => {
  try {
    state.materials = (await api(`/api/admin/products/${product.id}/materials`)).materials;
    renderMaterials();
  } catch (error) {
    showToast(error.message, true);
  }
};

const materialPayload = (form) => ({
  title: form.elements.title.value.trim(),
  content_type: form.elements.content_type.value,
  external_url: form.elements.external_url.value.trim() || null,
  storage_key: form.elements.storage_key.value.trim() || null,
  sort_order: Number(form.elements.sort_order.value || 0),
});

const resetMaterialEditor = () => {
  state.editingMaterial = null;
  const form = $('#material-editor');
  form.reset();
  form.elements.sort_order.value = 0;
  $('#material-submit').textContent = 'Добавить урок';
  $('#cancel-material-edit').hidden = true;
};

const startMaterialEdit = (material) => {
  state.editingMaterial = material;
  const form = $('#material-editor');
  Object.entries(material).forEach(([name, value]) => {
    if (form.elements[name]) form.elements[name].value = value ?? '';
  });
  $('#material-submit').textContent = 'Сохранить урок';
  $('#cancel-material-edit').hidden = false;
};

const saveMaterial = async (event) => {
  event.preventDefault();
  if (!state.editingProduct) return;
  const form = event.currentTarget;
  const button = $('#material-submit');
  button.disabled = true;
  try {
    const payload = materialPayload(form);
    if (state.editingMaterial) {
      await api(`/api/admin/products/${state.editingProduct.id}/materials/${state.editingMaterial.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
      showToast('Урок обновлён.');
    } else {
      await api(`/api/admin/products/${state.editingProduct.id}/materials`, { method: 'POST', body: JSON.stringify(payload) });
      showToast('Урок добавлен.');
    }
    await loadMaterials(state.editingProduct);
    resetMaterialEditor();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    button.disabled = false;
  }
};

const deleteMaterial = async (material) => {
  if (!state.editingProduct || !window.confirm(`Удалить «${material.title}»?`)) return;
  try {
    await api(`/api/admin/products/${state.editingProduct.id}/materials/${material.id}`, { method: 'DELETE' });
    await loadMaterials(state.editingProduct);
    resetMaterialEditor();
    showToast('Урок удалён.');
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
  $('#user-search').addEventListener('submit', (event) => {
    event.preventDefault();
    void loadUser($('#user-identifier').value.trim());
  });
  $('#user-filter').addEventListener('submit', (event) => { event.preventDefault(); void loadUserList(); });
  $('#product-editor').addEventListener('submit', saveProduct);
  $('#material-editor').addEventListener('submit', saveMaterial);
  $('#asset-editor').addEventListener('submit', saveAsset);
  $('#settings-editor').addEventListener('submit', saveSettings);
  $('#cancel-product-edit').addEventListener('click', resetProductEditor);
  $('#cancel-material-edit').addEventListener('click', resetMaterialEditor);
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
    const [dashboard, products, assets, _settings, users] = await Promise.all([
      api(`/api/admin/dashboard?date_from=${$('#date-from').value}&date_to=${$('#date-to').value}&granularity=${$('#dashboard-granularity').value}`),
      api('/api/admin/products'),
      api('/api/admin/signal-assets'),
      loadSettings(),
      api('/api/admin/users/list?limit=50'),
    ]);
    renderDashboard(dashboard);
    state.products = products.products;
    state.assets = assets.assets;
    renderProducts();
    renderAssets();
    renderUserList(users.users);
  } catch (error) {
    showOverlay('Не удалось открыть админку', error.message);
  }
};

bootstrap();
