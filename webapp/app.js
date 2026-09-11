const telegram = window.Telegram?.WebApp;

telegram?.ready();
telegram?.expand();

const statusNames = {
  novice: 'Novice',
  trader: 'Trader',
  professional: 'Professional',
  expert: 'Expert',
  master: 'Master',
  legend: 'Legend',
};

const state = {
  assets: [],
  availability: null,
  diary: null,
  mood: 3,
  notifications: [],
  productFilter: 'all',
  products: [],
  profile: null,
  selectedAssetId: null,
  selectedTimeframe: null,
  signalMode: 'standard',
};

class ApiError extends Error {}

const $ = (selector) => document.querySelector(selector);
const amount = (value) => Number(value || 0);
const statusLabel = (value) => statusNames[value] || value;
const pac = (value) => `${amount(value).toLocaleString('ru-RU')} PAC`;
const dollars = (value) => `$${amount(value).toLocaleString('ru-RU')}`;
const timeframeLabel = (seconds) => {
  if (seconds < 60) return `${seconds} с`;
  if (seconds % 3600 === 0) return `${seconds / 3600} ч`;
  if (seconds % 60 === 0) return `${seconds / 60} мин`;
  return `${seconds} с`;
};

const setScreen = (screen) => {
  document.querySelectorAll('.screen').forEach((item) => {
    item.classList.toggle('is-active', item.dataset.screen === screen);
  });
  document.querySelectorAll('.tab').forEach((item) => {
    item.classList.toggle('is-active', item.dataset.tab === screen);
  });
};

const showOverlay = (title, message) => {
  $('#overlay-title').textContent = title;
  $('#overlay-message').textContent = message;
  $('#access-overlay').hidden = false;
};

const api = async (path, options = {}) => {
  if (!telegram?.initData) {
    throw new ApiError('Open Pocket Academy from the Telegram bot.');
  }
  const headers = new Headers(options.headers);
  headers.set('X-Telegram-Init-Data', telegram.initData);
  if (options.body) headers.set('Content-Type', 'application/json');
  const response = await fetch(path, { ...options, headers });
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const message = payload?.detail || 'Не удалось выполнить запрос. Повтори ещё раз.';
    throw new ApiError(message);
  }
  return payload;
};

const createButton = (label, className = 'secondary-button') => {
  const button = document.createElement('button');
  button.className = className;
  button.type = 'button';
  button.textContent = label;
  return button;
};

const renderHome = () => {
  const profile = state.profile;
  $('#welcome-name').textContent = profile.name || 'Трейдер';
  $('#home-status').textContent = statusLabel(profile.status);
  $('#home-pac').textContent = pac(profile.pac_balance);

  const progress = $('#status-progress');
  if (!profile.next_status) {
    progress.style.width = '100%';
    $('#status-next').textContent = 'Максимальный статус достигнут.';
    return;
  }
  const currentMinimum = amount(profile.current_status_minimum_deposits);
  const nextMinimum = amount(profile.next_status_minimum_deposits);
  const ratio = ((amount(profile.total_deposits) - currentMinimum) / (nextMinimum - currentMinimum)) * 100;
  progress.style.width = `${Math.max(4, Math.min(100, ratio))}%`;
  $('#status-next').textContent = `До ${statusLabel(profile.next_status)}: ${dollars(profile.remaining_deposits)} депозитов`;
};

const renderProfile = () => {
  const profile = state.profile;
  const name = profile.name || 'Трейдер';
  $('#profile-name').textContent = name;
  $('#profile-initial').textContent = name.slice(0, 1).toUpperCase();
  $('#profile-meta').textContent = `${statusLabel(profile.status)} · ${dollars(profile.total_deposits)} депозитов`;
  const list = $('#status-list');
  list.replaceChildren();
  Object.entries(statusNames).forEach(([key, label]) => {
    const item = document.createElement('p');
    item.textContent = `${key === profile.status ? '●' : '○'} ${label}`;
    item.classList.toggle('is-current', key === profile.status);
    list.append(item);
  });
};

const renderDiary = () => {
  const entry = state.diary;
  $('#profitable-trades').value = entry?.profitable_trades || 0;
  $('#losing-trades').value = entry?.losing_trades || 0;
  $('#diary-comment').value = entry?.comment || '';
  state.mood = entry?.mood || 3;
  document.querySelectorAll('[data-mood]').forEach((button) => {
    button.classList.toggle('is-selected', Number(button.dataset.mood) === state.mood);
  });
};

const selectedAvailability = () => state.availability?.[state.signalMode];

const renderSignalControls = () => {
  const availability = selectedAvailability();
  if (!availability) return;
  const isPremium = state.signalMode === 'premium';
  document.querySelectorAll('[data-mode]').forEach((button) => {
    button.classList.toggle('is-selected', button.dataset.mode === state.signalMode);
  });

  const assets = $('#asset-options');
  assets.replaceChildren();
  if (!state.assets.length) {
    assets.textContent = 'Активные пары пока не добавлены администратором.';
    assets.className = 'muted';
  } else {
    assets.className = 'chip-row';
    state.assets.forEach((asset) => {
      const button = createButton(asset.label, 'chip');
      button.dataset.assetId = asset.id;
      button.classList.toggle('is-selected', asset.id === state.selectedAssetId);
      assets.append(button);
    });
  }

  const timeframes = $('#timeframe-options');
  timeframes.replaceChildren();
  const allowed = state.availability.allowed_timeframes || [];
  if (!allowed.includes(state.selectedTimeframe)) {
    state.selectedTimeframe = allowed[0] || null;
  }
  allowed.forEach((seconds) => {
    const button = createButton(timeframeLabel(seconds), 'chip');
    button.dataset.timeframe = seconds;
    button.classList.toggle('is-selected', seconds === state.selectedTimeframe);
    timeframes.append(button);
  });

  const limit = availability.limit === null ? '∞' : availability.limit;
  $('#signal-limit').textContent = `${availability.used} / ${limit}`;
  const notice = $('#signal-notice');
  const button = $('#signal-button');
  const nextAvailableAt = availability.next_available_at ? new Date(availability.next_available_at) : null;
  const isWaiting = nextAvailableAt && nextAvailableAt > new Date();
  const premiumBlocked = isPremium && !state.availability.is_premium_available;
  const dailyLimitReached = availability.limit !== null && availability.used >= availability.limit;
  button.disabled = Boolean(
    state.availability.is_blocked
      || premiumBlocked
      || isWaiting
      || dailyLimitReached
      || !state.selectedAssetId
      || !state.selectedTimeframe,
  );

  if (state.availability.is_blocked) {
    notice.textContent = 'Доступ к сигналам временно ограничен.';
  } else if (premiumBlocked) {
    notice.textContent = `Premium доступен от ${dollars(state.availability.premium_minimum_deposit)} депозитов.`;
  } else if (dailyLimitReached) {
    notice.textContent = 'Дневной лимит сигналов исчерпан.';
  } else if (isWaiting) {
    notice.textContent = `Следующий сигнал будет доступен в ${nextAvailableAt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}.`;
  } else {
    notice.textContent = isPremium ? 'Premium-сигналы имеют отдельный лимит.' : 'Направление и вероятность формируются для твоего статуса.';
  }
};

const renderProducts = () => {
  const root = $('#product-list');
  root.replaceChildren();
  const products = state.products.filter((product) => state.productFilter === 'all' || product.product_type === state.productFilter);
  if (!products.length) {
    root.append(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'В этом разделе пока нет материалов.' }));
    return;
  }
  products.forEach((product, index) => {
    const card = document.createElement('article');
    card.className = 'product-card';
    const mark = document.createElement('span');
    mark.className = 'product-mark';
    mark.textContent = String(index + 1).padStart(2, '0');
    const body = document.createElement('div');
    const title = document.createElement('h3');
    title.textContent = product.title;
    const description = document.createElement('p');
    description.textContent = product.description || 'Материал Pocket Academy.';
    body.append(title, description);
    card.append(mark, body, productAction(product));
    root.append(card);
  });
};

const productAction = (product) => {
  if (product.is_available && product.external_url) {
    const button = createButton('Открыть');
    button.addEventListener('click', () => openExternal(product.external_url));
    return button;
  }
  if (product.is_available) {
    const button = createButton('Открыто');
    button.disabled = true;
    return button;
  }
  if (product.price_pac !== null) {
    const button = createButton(`${pac(product.price_pac)}`);
    button.addEventListener('click', () => purchaseProduct(product, button));
    return button;
  }
  const button = createButton(product.grant_condition === 'deposit_threshold' ? 'После депозита' : 'Недоступно');
  button.disabled = true;
  return button;
};

const renderNotifications = () => {
  const root = $('#notification-list');
  root.replaceChildren();
  if (!state.notifications.length) {
    root.append(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Новых уведомлений нет.' }));
    return;
  }
  state.notifications.forEach((notification) => {
    const item = document.createElement('article');
    item.className = 'notification-item';
    const title = document.createElement('strong');
    title.textContent = notification.title;
    const body = document.createElement('p');
    body.textContent = notification.body;
    const time = document.createElement('time');
    time.className = 'muted';
    time.textContent = new Date(notification.created_at).toLocaleString('ru-RU');
    item.append(title, body, time);
    root.append(item);
  });
  const unreadCount = state.notifications.filter((notification) => !notification.read_at).length;
  const badge = $('#notification-badge');
  badge.hidden = unreadCount === 0;
  badge.textContent = unreadCount > 9 ? '9+' : String(unreadCount);
};

const renderAll = () => {
  renderHome();
  renderProfile();
  renderDiary();
  renderSignalControls();
  renderProducts();
  renderNotifications();
};

const refreshProfileAndProducts = async () => {
  const [profile, products] = await Promise.all([api('/api/me'), api('/api/products')]);
  state.profile = profile;
  state.products = products.products;
  renderHome();
  renderProfile();
  renderProducts();
};

const generateSignal = async () => {
  const button = $('#signal-button');
  button.disabled = true;
  try {
    const signal = await api('/api/signals', {
      method: 'POST',
      body: JSON.stringify({
        asset_id: state.selectedAssetId,
        timeframe_seconds: state.selectedTimeframe,
        is_premium: state.signalMode === 'premium',
      }),
    });
    $('#signal-direction').textContent = signal.direction.toUpperCase();
    $('#signal-probability').textContent = `${signal.probability}%`;
    $('#signal-asset').textContent = `${signal.asset_label} · ${timeframeLabel(signal.timeframe_seconds)}`;
    $('#signal-result').hidden = false;
    state.availability = await api('/api/signals/availability');
    renderSignalControls();
  } catch (error) {
    try {
      state.availability = await api('/api/signals/availability');
      renderSignalControls();
    } finally {
      $('#signal-notice').textContent = error.message;
    }
  }
};

const saveDiary = async () => {
  const button = $('#diary-button');
  button.disabled = true;
  try {
    state.diary = await api('/api/me/diary', {
      method: 'PUT',
      body: JSON.stringify({
        profitable_trades: Number($('#profitable-trades').value || 0),
        losing_trades: Number($('#losing-trades').value || 0),
        mood: state.mood,
        comment: $('#diary-comment').value.trim() || null,
      }),
    });
    $('#diary-notice').textContent = state.diary.reward_granted ? 'Дневник сохранён. За серию начислено 5 PAC.' : 'Дневник сохранён.';
    renderDiary();
  } catch (error) {
    $('#diary-notice').textContent = error.message;
  } finally {
    button.disabled = false;
  }
};

const purchaseProduct = async (product, button) => {
  button.disabled = true;
  try {
    await api(`/api/products/${product.id}/purchase`, { method: 'POST' });
    await refreshProfileAndProducts();
  } catch (error) {
    button.disabled = false;
    telegram?.showAlert?.(error.message);
  }
};

const openExternal = (url) => {
  if (telegram?.openLink) {
    telegram.openLink(url);
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
};

const openNotifications = async () => {
  $('#notification-panel').hidden = false;
  try {
    const payload = await api('/api/me/notifications');
    state.notifications = payload.notifications;
    renderNotifications();
    if (state.notifications.some((notification) => !notification.read_at)) {
      await api('/api/me/notifications/read', { method: 'POST' });
      state.notifications = state.notifications.map((notification) => ({ ...notification, read_at: new Date().toISOString() }));
      renderNotifications();
    }
  } catch (error) {
    $('#notification-list').textContent = error.message;
  }
};

const bindEvents = () => {
  document.querySelectorAll('[data-tab]').forEach((button) => {
    button.addEventListener('click', () => setScreen(button.dataset.tab));
  });
  $('#asset-options').addEventListener('click', (event) => {
    const button = event.target.closest('[data-asset-id]');
    if (!button) return;
    state.selectedAssetId = button.dataset.assetId;
    renderSignalControls();
  });
  $('#timeframe-options').addEventListener('click', (event) => {
    const button = event.target.closest('[data-timeframe]');
    if (!button) return;
    state.selectedTimeframe = Number(button.dataset.timeframe);
    renderSignalControls();
  });
  document.querySelectorAll('[data-mode]').forEach((button) => {
    button.addEventListener('click', () => {
      state.signalMode = button.dataset.mode;
      renderSignalControls();
    });
  });
  document.querySelectorAll('[data-product-filter]').forEach((button) => {
    button.addEventListener('click', () => {
      state.productFilter = button.dataset.productFilter;
      document.querySelectorAll('[data-product-filter]').forEach((filter) => {
        filter.classList.toggle('is-selected', filter === button);
      });
      renderProducts();
    });
  });
  document.querySelectorAll('[data-mood]').forEach((button) => {
    button.addEventListener('click', () => {
      state.mood = Number(button.dataset.mood);
      renderDiary();
    });
  });
  $('#signal-button').addEventListener('click', generateSignal);
  $('#diary-button').addEventListener('click', saveDiary);
  $('[data-action="notifications"]').addEventListener('click', openNotifications);
  $('[data-action="close-notifications"]').addEventListener('click', () => {
    $('#notification-panel').hidden = true;
  });
};

const bootstrap = async () => {
  bindEvents();
  if (!telegram?.initData) {
    showOverlay('Открой приложение в Telegram', 'Для безопасной авторизации нужен Telegram Mini App.');
    return;
  }
  try {
    const [profile, diary, notifications, products, assets, availability] = await Promise.all([
      api('/api/me'),
      api('/api/me/diary'),
      api('/api/me/notifications'),
      api('/api/products'),
      api('/api/signals/assets'),
      api('/api/signals/availability'),
    ]);
    state.profile = profile;
    state.diary = diary;
    state.notifications = notifications.notifications;
    state.products = products.products;
    state.assets = assets.assets;
    state.availability = availability;
    state.selectedAssetId = state.assets[0]?.id || null;
    renderAll();
    if (profile.is_blocked) {
      showOverlay('Доступ временно ограничен', 'Сигналы будут доступны после урегулирования вывода средств.');
    }
  } catch (error) {
    showOverlay('Не удалось открыть Academy', error.message);
  }
};

bootstrap();
