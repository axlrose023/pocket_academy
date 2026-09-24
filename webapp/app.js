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
  activeSignal: null,
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
  market: {
    assetId: null,
    candles: [],
    basePrice: 1,
    seed: 1,
  },
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

const selectedAsset = () => state.assets.find((asset) => asset.id === state.selectedAssetId) || null;
const hashText = (value) => [...value].reduce((hash, character) => ((hash * 31) + character.charCodeAt(0)) >>> 0, 2166136261);
const nextMarketRandom = () => {
  state.market.seed = ((state.market.seed * 1664525) + 1013904223) >>> 0;
  return state.market.seed / 4294967296;
};

const assetBasePrice = (label = '') => {
  if (label.includes('USD/JPY')) return 148.42;
  if (label.includes('GBP/USD')) return 1.2684;
  if (label.includes('EUR/CHF')) return 0.9342;
  if (label.includes('EUR/USD')) return 1.0842;
  return 1 + ((hashText(label) % 2_000) / 10_000);
};

const pricePrecision = (label = '') => label.includes('JPY') ? 3 : 5;

const appendMarketCandle = () => {
  const previous = state.market.candles.at(-1);
  const open = previous?.close ?? state.market.basePrice;
  const asset = selectedAsset();
  const volatility = state.market.basePrice * (asset?.is_otc ? .00105 : .00072);
  const drift = ((nextMarketRandom() - .48) * volatility);
  const close = Math.max(.00001, open + drift);
  const wick = volatility * (.24 + nextMarketRandom() * .75);
  state.market.candles.push({
    open,
    close,
    high: Math.max(open, close) + (wick * nextMarketRandom()),
    low: Math.min(open, close) - (wick * nextMarketRandom()),
  });
  if (state.market.candles.length > 36) state.market.candles.shift();
};

const updateMarketHeader = () => {
  const asset = selectedAsset();
  if (!asset) return;
  const candles = state.market.candles;
  const current = candles.at(-1)?.close ?? state.market.basePrice;
  const start = candles[0]?.open ?? current;
  const change = start ? ((current - start) / start) * 100 : 0;
  $('#chart-asset').textContent = asset.label;
  $('#chart-price').textContent = current.toFixed(pricePrecision(asset.label));
  $('#chart-change').textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
  $('#chart-change').classList.toggle('is-negative', change < 0);
  $('#chart-clock').textContent = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

const drawMarketChart = () => {
  const canvas = $('#market-chart');
  if (!canvas || !state.market.candles.length) return;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  const targetWidth = Math.round(width * pixelRatio);
  const targetHeight = Math.round(height * pixelRatio);
  if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
    canvas.width = targetWidth;
    canvas.height = targetHeight;
  }
  const context = canvas.getContext('2d');
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.clearRect(0, 0, width, height);

  const candles = state.market.candles;
  const top = 15;
  const bottom = height - 35;
  const left = 14;
  const right = width - 14;
  const plotHeight = bottom - top;
  const plotWidth = right - left;
  const high = Math.max(...candles.map((candle) => candle.high));
  const low = Math.min(...candles.map((candle) => candle.low));
  const padding = Math.max((high - low) * .14, state.market.basePrice * .00008);
  const max = high + padding;
  const min = low - padding;
  const range = max - min || 1;
  const y = (price) => top + ((max - price) / range) * plotHeight;

  context.lineWidth = 1;
  context.strokeStyle = 'rgba(136, 177, 231, .09)';
  for (let index = 0; index <= 4; index += 1) {
    const gridY = top + ((plotHeight / 4) * index);
    context.beginPath();
    context.moveTo(left, gridY);
    context.lineTo(right, gridY);
    context.stroke();
  }
  for (let index = 0; index <= 5; index += 1) {
    const gridX = left + ((plotWidth / 5) * index);
    context.beginPath();
    context.moveTo(gridX, top);
    context.lineTo(gridX, bottom);
    context.stroke();
  }

  const step = plotWidth / candles.length;
  const bodyWidth = Math.max(3, Math.min(8, step * .52));
  candles.forEach((candle, index) => {
    const x = left + (step * index) + (step / 2);
    const rising = candle.close >= candle.open;
    const color = rising ? '#2bd69f' : '#ff5c7a';
    context.strokeStyle = color;
    context.fillStyle = color;
    context.lineWidth = 1.2;
    context.beginPath();
    context.moveTo(x, y(candle.high));
    context.lineTo(x, y(candle.low));
    context.stroke();
    const bodyTop = Math.min(y(candle.open), y(candle.close));
    const bodyHeight = Math.max(2, Math.abs(y(candle.open) - y(candle.close)));
    context.fillRect(x - (bodyWidth / 2), bodyTop, bodyWidth, bodyHeight);
  });

  const currentY = y(candles.at(-1).close);
  context.save();
  context.setLineDash([4, 5]);
  context.strokeStyle = 'rgba(88, 183, 255, .55)';
  context.beginPath();
  context.moveTo(left, currentY);
  context.lineTo(right, currentY);
  context.stroke();
  context.restore();
};

const initializeMarketChart = () => {
  const asset = selectedAsset();
  if (!asset) return;
  state.market.assetId = asset.id;
  state.market.basePrice = assetBasePrice(asset.label);
  state.market.seed = hashText(asset.asset_key || asset.label) || 1;
  state.market.candles = [];
  for (let index = 0; index < 32; index += 1) appendMarketCandle();
  updateMarketHeader();
  requestAnimationFrame(drawMarketChart);
};

const tickMarketChart = () => {
  if (!selectedAsset()) return;
  appendMarketCandle();
  updateMarketHeader();
  drawMarketChart();
};

const formatCountdown = (totalSeconds) => {
  const seconds = Math.max(0, Math.ceil(totalSeconds));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  return hours > 0
    ? `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
    : `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
};

let signalCountdownTimer;
const updateActiveSignalTimer = () => {
  if (!state.activeSignal) return;
  const now = Date.now();
  const remaining = Math.max(0, (state.activeSignal.expiresAt - now) / 1000);
  const ratio = Math.max(0, Math.min(100, (remaining / state.activeSignal.timeframe_seconds) * 100));
  $('#signal-countdown').textContent = formatCountdown(remaining);
  $('#signal-progress').style.width = `${ratio}%`;
  const stateLabel = $('#signal-result').querySelector('.signal-state');
  if (remaining <= 0) {
    stateLabel.lastChild.textContent = 'СИГНАЛ ЗАВЕРШЕН';
    clearInterval(signalCountdownTimer);
  } else {
    stateLabel.lastChild.textContent = 'СИГНАЛ АКТИВЕН';
  }
};

const showActiveSignal = (signal, { includeExpired = false } = {}) => {
  const requestedAt = new Date(signal.requested_at).getTime();
  const expiresAt = requestedAt + (signal.timeframe_seconds * 1000);
  if (!includeExpired && expiresAt <= Date.now()) return;
  state.activeSignal = { ...signal, expiresAt };
  const card = $('#signal-result');
  const isSell = signal.direction.toLowerCase() === 'sell';
  card.classList.toggle('is-sell', isSell);
  card.classList.toggle('is-buy', !isSell);
  $('#signal-direction').textContent = signal.direction.toUpperCase();
  $('#signal-direction-icon').textContent = isSell ? '↓' : '↑';
  $('#signal-probability').textContent = `${signal.probability}%`;
  $('#signal-asset').textContent = `${signal.asset_label} · ${timeframeLabel(signal.timeframe_seconds)}`;
  $('#signal-expiry').textContent = new Date(expiresAt).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  card.hidden = false;
  clearInterval(signalCountdownTimer);
  updateActiveSignalTimer();
  if (expiresAt > Date.now()) signalCountdownTimer = setInterval(updateActiveSignalTimer, 1_000);
};

const setScreen = (screen) => {
  document.querySelectorAll('.screen').forEach((item) => {
    item.classList.toggle('is-active', item.dataset.screen === screen);
  });
  document.querySelectorAll('.tab').forEach((item) => {
    item.classList.toggle('is-active', item.dataset.tab === screen);
  });
  window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  if (screen === 'signals') requestAnimationFrame(drawMarketChart);
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
  let registrationAction = null;
  if (!profile.is_registered) {
    registrationAction = createButton(
      'Зарегистрироваться в Pocket Option',
      'text-button',
    );
    registrationAction.addEventListener('click', () => {
      void openPocketOptionRegistration(registrationAction, false);
    });
  }
  appendJourneyStep(
    root,
    '1',
    'Регистрация',
    profile.is_registered
      ? '✅ Аккаунт Pocket Option подключён.'
      : 'Создай торговый аккаунт по партнёрской ссылке.',
    registrationAction,
  );
  let depositText = profile.has_deposit
    ? `✅ Первый депозит: ${dollars(profile.first_deposit_amount)}.`
    : 'После регистрации пополни торговый счёт, чтобы активировать сигналы.';
  if (profile.is_low_first_deposit) {
    depositText += ` Сумма меньше порога ${dollars(profile.minimum_first_deposit)}.`;
  }
  let reregistrationAction = null;
  if (profile.is_low_first_deposit) {
    reregistrationAction = createButton('Перерегистрироваться', 'text-button');
    reregistrationAction.addEventListener('click', () => {
      void openPocketOptionRegistration(reregistrationAction, true);
    });
  }
  appendJourneyStep(root, '2', 'Первый депозит', depositText, reregistrationAction);
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
  renderMoodOptions();
};

const renderMoodOptions = () => {
  document.querySelectorAll('[data-mood]').forEach((button) => {
    button.classList.toggle('is-selected', Number(button.dataset.mood) === state.mood);
  });
};

const selectedAvailability = () => state.availability?.[state.signalMode];

const setSignalButtonLabel = (label) => {
  const labelNode = $('#signal-button').querySelector('span');
  if (labelNode) labelNode.textContent = label;
};

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
    assets.className = 'asset-scroll muted';
  } else {
    assets.className = 'asset-scroll';
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
  $('#selected-timeframe').textContent = state.selectedTimeframe ? timeframeLabel(state.selectedTimeframe) : '—';
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
  const hasTestAccess = state.availability.is_test_access;
  const premiumBlocked = isPremium && !hasTestAccess && !state.availability.is_premium_available;
  const dailyLimitReached = availability.limit !== null && availability.used >= availability.limit;
  const registrationRequired = !hasTestAccess && !state.profile.is_registered;
  const depositRequired = !hasTestAccess && !state.profile.has_deposit;
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
    setSignalButtonLabel('Зарегистрироваться');
    notice.textContent = 'Сначала подключи торговый аккаунт Pocket Option.';
  } else if (depositRequired) {
    setSignalButtonLabel('Сделать депозит');
    notice.textContent = 'Первый депозит активирует торговые сигналы.';
  } else if (state.availability.is_blocked) {
    setSignalButtonLabel(isPremium ? 'Premium-сигнал' : 'Получить сигнал');
    notice.textContent = 'Доступ к сигналам временно ограничен.';
  } else if (premiumBlocked) {
    setSignalButtonLabel('Premium-сигнал');
    notice.textContent = `Premium доступен от ${dollars(state.availability.premium_minimum_deposit)} депозитов.`;
  } else if (dailyLimitReached) {
    setSignalButtonLabel(isPremium ? 'Premium-сигнал' : 'Получить сигнал');
    notice.textContent = 'Дневной лимит сигналов исчерпан.';
  } else if (isWaiting) {
    setSignalButtonLabel(isPremium ? 'Premium-сигнал' : 'Получить сигнал');
    notice.textContent = `Следующий сигнал будет доступен в ${nextAvailableAt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}.`;
  } else if (hasTestAccess) {
    setSignalButtonLabel(isPremium ? 'Premium-сигнал' : 'Получить сигнал');
    notice.textContent = 'Тестовый доступ: сигналы доступны без регистрации и депозита.';
  } else {
    setSignalButtonLabel(isPremium ? 'Premium-сигнал' : 'Получить сигнал');
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
    item.className = 'history-item signal-history-item';
    const direction = document.createElement('span');
    direction.className = `history-direction${signal.direction.toLowerCase() === 'sell' ? ' is-sell' : ''}`;
    direction.textContent = signal.direction.toLowerCase() === 'sell' ? '↓' : '↑';
    const copy = document.createElement('div');
    copy.className = 'history-copy';
    const title = document.createElement('strong');
    title.textContent = signal.asset_label;
    const details = document.createElement('p');
    details.className = 'muted';
    details.textContent = `${signal.direction.toUpperCase()} · ${timeframeLabel(signal.timeframe_seconds)}${signal.is_premium ? ' · Premium' : ''}`;
    copy.append(title, details);
    const probability = document.createElement('span');
    probability.className = 'history-probability';
    probability.textContent = `${signal.probability}%`;
    item.append(direction, copy, probability);
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
  const badge = $('#notification-badge');
  root.replaceChildren();
  if (!state.notifications.length) {
    badge.hidden = true;
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
  button.classList.add('is-loading');
  setSignalButtonLabel('Анализируем рынок…');
  try {
    const signal = await api('/api/signals', {
      method: 'POST',
      body: JSON.stringify({
        asset_id: state.selectedAssetId,
        timeframe_seconds: state.selectedTimeframe,
        is_premium: state.signalMode === 'premium',
      }),
    });
    showActiveSignal(signal, { includeExpired: true });
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
  } finally {
    button.classList.remove('is-loading');
  }
};

const saveDiary = async () => {
  const button = $('#diary-button');
  button.disabled = true;
  let savedDiary;
  try {
    savedDiary = await api('/api/me/diary', {
      method: 'PUT',
      body: JSON.stringify({
        profitable_trades: Number($('#profitable-trades').value || 0),
        losing_trades: Number($('#losing-trades').value || 0),
        mood: state.mood,
        comment: $('#diary-comment').value.trim() || null,
      }),
    });
  } catch (error) {
    $('#diary-notice').textContent = error.message;
    button.disabled = false;
    return;
  }

  state.diary = savedDiary;
  if (state.profile) state.profile.pac_balance = savedDiary.pac_balance;
  $('#diary-notice').textContent = savedDiary.reward_granted ? 'Дневник сохранён. За серию начислено 5 PAC.' : 'Дневник сохранён.';
  renderDiary();
  if (state.profile) renderHome();

  try {
    const [diaryHistory, notifications] = await Promise.all([
      api('/api/me/diary/history'),
      api('/api/me/notifications'),
    ]);
    state.diaryHistory = diaryHistory.entries;
    state.notifications = notifications.notifications;
    renderProfileCollections();
    renderNotifications();
    if (savedDiary.reward_granted) {
      showNotificationToast(
        state.notifications.find(
          (notification) => notification.notification_type === 'diary_streak_reward' && !notification.read_at,
        ),
      );
    }
  } catch {
    $('#diary-notice').textContent += ' История и уведомления обновятся при следующем открытии.';
  }
  button.disabled = false;
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

const openPocketOptionRegistration = async (button, forceNew) => {
  button.disabled = true;
  try {
    const registration = await api('/api/me/pocket-option/link', {
      method: 'POST',
      body: JSON.stringify({ force_new: forceNew }),
    });
    openExternal(registration.url);
  } catch (error) {
    if (telegram?.showAlert) {
      telegram.showAlert(error.message);
    } else {
      window.alert(error.message);
    }
  } finally {
    button.disabled = false;
  }
};

const openProductMaterials = async (product) => {
  window.scrollTo({ left: 0, behavior: 'auto' });
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
  window.scrollTo({ left: 0, behavior: 'auto' });
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
    initializeMarketChart();
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
      renderMoodOptions();
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
    initializeMarketChart();
    if (state.signals[0]) showActiveSignal(state.signals[0]);
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

const chartCanvas = $('#market-chart');
if (window.ResizeObserver && chartCanvas) {
  new ResizeObserver(() => drawMarketChart()).observe(chartCanvas);
} else {
  window.addEventListener('resize', drawMarketChart);
}
setInterval(() => {
  if (!document.hidden) tickMarketChart();
}, 1_400);

bootstrap();
