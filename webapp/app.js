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
  diaryHistory: [],
  deposits: [],
  mood: 3,
  notifications: [],
  productFilter: 'all',
  products: [],
  profile: null,
  selectedAssetId: null,
  selectedTimeframe: null,
  signals: [],
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

const showOverlay = (title, message, managerUrl = null) => {
  $('#overlay-title').textContent = title;
  $('#overlay-message').textContent = message;
  const managerButton = $('#overlay-manager');
  managerButton.hidden = !managerUrl;
  managerButton.onclick = managerUrl ? () => openExternal(managerUrl) : null;
  $('#access-overlay').hidden = false;
};

let notificationToastTimer;
const showNotificationToast = (notification) => {
  if (!notification) return;
  const toast = $('#notification-toast');
  toast.textContent = `${notification.title}: ${notification.body}`;
  toast.hidden = false;
  clearTimeout(notificationToastTimer);
  notificationToastTimer = setTimeout(() => { toast.hidden = true; }, 6_000);
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
  } else {
    const currentMinimum = amount(profile.current_status_minimum_deposits);
    const nextMinimum = amount(profile.next_status_minimum_deposits);
    const ratio = ((amount(profile.total_deposits) - currentMinimum) / (nextMinimum - currentMinimum)) * 100;
    progress.style.width = `${Math.max(4, Math.min(100, ratio))}%`;
    $('#status-next').textContent = `До ${statusLabel(profile.next_status)}: ${dollars(profile.remaining_deposits)} депозитов`;
  }
  renderJourney();
  renderHomeProducts();
};

const appendJourneyStep = (root, index, title, description, action) => {
  const step = document.createElement('li');
  step.className = 'step';
  const mark = document.createElement('span');
  mark.textContent = index;
  const content = document.createElement('div');
  const heading = document.createElement('strong');
  heading.textContent = title;
  const text = document.createElement('p');
  text.textContent = description;
  content.append(heading, text);
  if (action) content.append(action);
  step.append(mark, content);
  root.append(step);
};

const renderJourney = () => {
  const root = $('#journey-steps');
  const profile = state.profile;
  root.replaceChildren();
  appendJourneyStep(
    root,
    '1',
    'Регистрация',
    profile.is_registered ? '✅ Аккаунт Pocket Option подключён.' : 'Партнёрская ссылка появится после завершения настройки Pocket Option.',
  );
  let depositText = profile.has_deposit
    ? `✅ Первый депозит: ${dollars(profile.first_deposit_amount)}.`
    : 'После регистрации пополни торговый счёт, чтобы активировать сигналы.';
  if (profile.is_low_first_deposit) {
    depositText += ` Сумма меньше порога ${dollars(profile.minimum_first_deposit)}.`;
  }
  const lowDepositNote = profile.is_low_first_deposit
    ? Object.assign(document.createElement('span'), { className: 'text-note', textContent: 'Перерегистрация станет доступна после настройки нового click_id.' })
    : null;
  appendJourneyStep(root, '2', 'Первый депозит', depositText, lowDepositNote);
  let managerAction = null;
  if (profile.has_deposit && profile.manager_telegram_url) {
    managerAction = createButton('Написать менеджеру', 'text-button');
    managerAction.addEventListener('click', () => openExternal(profile.manager_telegram_url));
  }
  appendJourneyStep(
    root,
    '3',
    'Поддержка',
    profile.has_deposit ? 'Менеджер доступен для вопросов по Academy.' : 'Контакт менеджера открывается после первого депозита.',
    managerAction,
  );
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
  const signalLimit = $('#signal-limit');
  signalLimit.hidden = state.availability.standard.used === 0 && state.availability.premium.used === 0;
  signalLimit.textContent = `${availability.used} / ${limit}`;
  const notice = $('#signal-notice');
  const button = $('#signal-button');
  const nextAvailableAt = availability.next_available_at ? new Date(availability.next_available_at) : null;
  const isWaiting = nextAvailableAt && nextAvailableAt > new Date();
  const premiumBlocked = isPremium && !state.availability.is_premium_available;
  const dailyLimitReached = availability.limit !== null && availability.used >= availability.limit;
  const registrationRequired = !state.profile.is_registered;
  const depositRequired = !state.profile.has_deposit;
  button.disabled = Boolean(
    state.availability.is_blocked
      || registrationRequired
      || depositRequired
      || premiumBlocked
      || isWaiting
      || dailyLimitReached
      || !state.selectedAssetId
      || !state.selectedTimeframe,
  );

  if (registrationRequired) {
    button.textContent = 'Зарегистрироваться';
    notice.textContent = 'Сначала подключи торговый аккаунт Pocket Option.';
  } else if (depositRequired) {
    button.textContent = 'Сделать депозит';
    notice.textContent = 'Первый депозит активирует торговые сигналы.';
  } else if (state.availability.is_blocked) {
    button.textContent = isPremium ? 'Premium-сигнал' : 'Получить сигнал';
    notice.textContent = 'Доступ к сигналам временно ограничен.';
  } else if (premiumBlocked) {
    button.textContent = 'Premium-сигнал';
    notice.textContent = `Premium доступен от ${dollars(state.availability.premium_minimum_deposit)} депозитов.`;
  } else if (dailyLimitReached) {
    button.textContent = isPremium ? 'Premium-сигнал' : 'Получить сигнал';
    notice.textContent = 'Дневной лимит сигналов исчерпан.';
  } else if (isWaiting) {
    button.textContent = isPremium ? 'Premium-сигнал' : 'Получить сигнал';
    notice.textContent = `Следующий сигнал будет доступен в ${nextAvailableAt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}.`;
  } else {
    button.textContent = isPremium ? 'Premium-сигнал' : 'Получить сигнал';
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

const renderHomeProducts = () => {
  const root = $('#home-product-list');
  root.replaceChildren();
  const products = state.products.slice(0, 3);
  if (!products.length) {
    root.append(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Материалы скоро появятся в Academy.' }));
    return;
  }
  products.forEach((product) => {
    const card = document.createElement('article');
    card.className = 'product-card product-card--compact';
    const body = document.createElement('div');
    const title = document.createElement('h3');
    title.textContent = product.title;
    const description = document.createElement('p');
    description.textContent = product.price_pac === null ? 'Доступ по условию Academy.' : product.price_pac === '0' || Number(product.price_pac) === 0 ? 'Бесплатно' : pac(product.price_pac);
    body.append(title, description);
    card.append(body, productAction(product));
    root.append(card);
  });
};

const renderSignalHistory = () => {
  const root = $('#signal-history');
  root.replaceChildren();
  if (!state.signals.length) {
    root.append(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Сигналов пока нет.' }));
    return;
  }
  state.signals.forEach((signal) => {
    const item = document.createElement('article');
    item.className = 'history-item';
    const title = document.createElement('strong');
    title.textContent = `${signal.direction.toUpperCase()} · ${signal.probability}%`;
    const details = document.createElement('p');
    details.className = 'muted';
    details.textContent = `${signal.asset_label} · ${timeframeLabel(signal.timeframe_seconds)}${signal.is_premium ? ' · Premium' : ''}`;
    item.append(title, details);
    root.append(item);
  });
};

const renderProfileCollections = () => {
  const productsRoot = $('#my-product-list');
  productsRoot.replaceChildren();
  const availableProducts = state.products.filter((product) => product.is_available);
  if (!availableProducts.length) {
    productsRoot.append(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Открытых продуктов пока нет.' }));
  } else {
    availableProducts.forEach((product) => {
      const item = document.createElement('article');
      item.className = 'history-item';
      const title = document.createElement('strong');
      title.textContent = product.title;
      item.append(title);
      const button = createButton('Открыть', 'text-button');
      if (product.external_url && ['group', 'bot'].includes(product.product_type)) {
        button.addEventListener('click', () => openExternal(product.external_url));
      } else {
        button.addEventListener('click', () => openProductMaterials(product));
      }
      item.append(button);
      productsRoot.append(item);
    });
  }

  const depositsRoot = $('#deposit-history');
  depositsRoot.replaceChildren();
  if (!state.deposits.length) {
    depositsRoot.append(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Депозитов пока нет.' }));
  } else {
    state.deposits.forEach((deposit) => {
      const item = document.createElement('article');
      item.className = 'history-item';
      const title = document.createElement('strong');
      title.textContent = `${dollars(deposit.amount)} · ${deposit.kind === 'first' ? 'FD' : 'RD'}`;
      const date = document.createElement('p');
      date.className = 'muted';
      date.textContent = new Date(deposit.occurred_at).toLocaleString('ru-RU');
      item.append(title, date);
      depositsRoot.append(item);
    });
  }

  const diaryRoot = $('#diary-history');
  diaryRoot.replaceChildren();
  if (!state.diaryHistory.length) {
    diaryRoot.append(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Записей пока нет.' }));
  } else {
    state.diaryHistory.forEach((entry) => {
      const item = document.createElement('article');
      item.className = 'history-item';
      const title = document.createElement('strong');
      title.textContent = `${entry.entry_day} · настроение ${entry.mood}/5`;
      const details = document.createElement('p');
      details.className = 'muted';
      details.textContent = `Прибыльных: ${entry.profitable_trades}; убыточных: ${entry.losing_trades}.`;
      item.append(title, details);
      diaryRoot.append(item);
    });
  }
};

const productAction = (product) => {
  if (product.is_available && product.external_url && ['group', 'bot'].includes(product.product_type)) {
    const button = createButton('Открыть');
    button.addEventListener('click', () => openExternal(product.external_url));
    return button;
  }
  if (product.is_available) {
    const button = createButton('Открыть');
    button.addEventListener('click', () => openProductMaterials(product));
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
  renderSignalHistory();
  renderProducts();
  renderProfileCollections();
  renderNotifications();
};

const refreshProfileAndProducts = async () => {
  const [profile, products, notifications] = await Promise.all([
    api('/api/me'),
    api('/api/products'),
    api('/api/me/notifications'),
  ]);
  state.profile = profile;
  state.products = products.products;
  state.notifications = notifications.notifications;
  renderHome();
  renderProfile();
  renderProducts();
  renderNotifications();
  showNotificationToast(state.notifications.find((notification) => !notification.read_at));
  renderProfileCollections();
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
    const [availability, signals] = await Promise.all([api('/api/signals/availability'), api('/api/signals')]);
    state.availability = availability;
    state.signals = signals.signals;
    renderSignalControls();
    renderSignalHistory();
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
    state.diaryHistory = (await api('/api/me/diary/history')).entries;
    renderDiary();
    renderProfileCollections();
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

const openProductMaterials = async (product) => {
  $('#material-panel').hidden = false;
  $('#material-panel-title').textContent = product.title;
  const root = $('#material-list');
  root.replaceChildren(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Загружаем материалы…' }));
  try {
    const payload = await api(`/api/products/${product.id}/materials`);
    root.replaceChildren();
    if (!payload.materials.length) {
      root.append(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Материалы этого продукта скоро появятся.' }));
      return;
    }
    payload.materials.forEach((material) => {
      const item = document.createElement('article');
      item.className = 'history-item';
      const title = document.createElement('strong');
      title.textContent = material.title;
      item.append(title);
      if (material.external_url) {
        const button = createButton('Открыть', 'text-button');
        button.addEventListener('click', () => openExternal(material.external_url));
        item.append(button);
      } else {
        const note = document.createElement('span');
        note.className = 'muted';
        note.textContent = 'Готовится';
        item.append(note);
      }
      root.append(item);
    });
  } catch (error) {
    root.textContent = error.message;
  }
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
  $('[data-action="close-materials"]').addEventListener('click', () => {
    $('#material-panel').hidden = true;
  });
};

const bootstrap = async () => {
  bindEvents();
  if (!telegram?.initData) {
    showOverlay('Открой приложение в Telegram', 'Для безопасной авторизации нужен Telegram Mini App.');
    return;
  }
  void api('/api/me/activity/webapp-opened', { method: 'POST' }).catch(() => undefined);
  try {
    const [profile, diary, diaryHistory, deposits, notifications, products, assets, availability, signals] = await Promise.all([
      api('/api/me'),
      api('/api/me/diary'),
      api('/api/me/diary/history'),
      api('/api/me/deposits'),
      api('/api/me/notifications'),
      api('/api/products'),
      api('/api/signals/assets'),
      api('/api/signals/availability'),
      api('/api/signals'),
    ]);
    state.profile = profile;
    state.diary = diary;
    state.diaryHistory = diaryHistory.entries;
    state.deposits = deposits.deposits;
    state.notifications = notifications.notifications;
    state.products = products.products;
    state.assets = assets.assets;
    state.availability = availability;
    state.signals = signals.signals;
    state.selectedAssetId = state.assets[0]?.id || null;
    renderAll();
    showNotificationToast(
      state.notifications.find((notification) => !notification.read_at),
    );
    if (profile.is_blocked) {
      showOverlay(
        'Доступ временно ограничен',
        'Для восстановления отмените заявку на вывод или пополните счёт на сумму вывода. Либо свяжитесь с менеджером.',
        profile.manager_telegram_url,
      );
    }
  } catch (error) {
    showOverlay('Не удалось открыть Academy', error.message);
  }
};

bootstrap();
