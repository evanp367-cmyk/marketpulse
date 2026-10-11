import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { createPortal } from 'react-dom';
import {
  Activity,
  ArrowLeftRight,
  Bell,
  ChartCandlestick,
  Globe,
  LayoutDashboard,
  Search,
  Check,
  ChevronDown,
  Settings,
  Star,
  Wallet,
  Newspaper,
  Sun,
  Moon,
  RefreshCw,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import { api, type Ticker, type Candle, type OfficialFxResponse, type WorldFxResponse, type FxCurrency, type FxCurrencyCatalog, type FxConversionResponse, type PortfolioResponse } from './api';
import Chart from './Chart';

type Lang = 'ru' | 'en';
type Page = 'terminal' | 'currencies' | 'portfolio' | 'signals' | 'news' | 'plans';
type FxMode = 'world' | 'cbr';
type ConverterPickerTarget = 'from' | 'to' | null;

const FALLBACK_FX_CURRENCIES: FxCurrency[] = [
  { code: 'USD', name: 'United States Dollar', symbol: '$', numeric_code: '840', start_date: null, end_date: null },
  { code: 'EUR', name: 'Euro', symbol: '€', numeric_code: '978', start_date: null, end_date: null },
  { code: 'GBP', name: 'Pound Sterling', symbol: '£', numeric_code: '826', start_date: null, end_date: null },
  { code: 'RUB', name: 'Russian Ruble', symbol: '₽', numeric_code: '643', start_date: null, end_date: null },
];

const words = {
  ru: {
    terminal: 'Терминал', markets: 'Крипторынок', currencies: 'Валюты', signals: 'Сигналы',
    news: 'Новости', portfolio: 'Портфель', watch: 'Избранное', settings: 'Настройки',
    live: 'КРИПТОРЫНОК · SPOT', subtitle: 'Котировки Binance Spot · по запросу',
    search: 'Найти инструмент', price: 'Цена', change: '24ч', volume: 'Объём', chart: 'График цены',
    loading: 'Загрузка рыночных данных…', error: 'Не удалось получить данные', retry: 'Обновить',
    source: 'Источник', notice: 'Условия коммерческого распространения рыночных данных требуют отдельной проверки.',
    add: 'В избранное', remove: 'Убрать из избранного', noData: 'Нет данных', lang: 'Язык',
    theme: 'Тема', dark: 'Тёмная', light: 'Светлая', fxTitle: 'Официальные курсы валют',
    fxSubtitle: 'Ежедневные справочные курсы Банка России', fxNotice: 'Это официальные курсы для справочных и учётных целей, а не биржевые Forex-котировки в реальном времени. Обновляются по расписанию Банка России, не непрерывно.',
    rateDate: 'Дата курса', referenceRate: 'Официальный курс', stale: 'Источник сейчас недоступен — показаны ранее полученные данные.',
    fxError: 'Не удалось загрузить официальные курсы', noFx: 'Нет доступных курсов',
    base: 'Валюта', rate: 'Курс к рублю', official: 'Официальный дневной курс',
    fxMarketType: 'СПРАВОЧНЫЕ ВАЛЮТНЫЕ КУРСЫ', cbrLink: 'Открыть сайт Банка России',
    fxWorldTitle: 'Мировые справочные курсы', fxWorldSubtitle: 'Ежедневные курсы на основе данных центральных банков и официальных источников',
    fxWorldSource: 'Мировые курсы', fxCbrSource: 'Курс ЦБ РФ', fxBase: 'Базовая валюта', fxWorldError: 'Не удалось загрузить мировые курсы',
    fxWorldNotice: 'Это ежедневные справочные курсы, а не котировки Forex в реальном времени. Набор валют зависит от доступности у источника.',
    fxSearch: 'Поиск валюты по коду или названию', fxShowing: 'Показано', fxLoadMore: 'Показать ещё', fxCurrencyCount: 'валют с доступным курсом', fxNoSearch: 'Валюты не найдены по этому запросу',
    fxUnavailable: 'Источник не предоставил эти валюты для выбранной базовой валюты:', fxRefSource: 'Открыть Frankfurter API',
    converterTitle: 'Конвертер валют', converterSubtitle: 'Расчёт по последнему доступному справочному курсу', converterAmount: 'Сумма', converterFrom: 'Из валюты', converterTo: 'В валюту', converterButton: 'Конвертировать', converterSwap: 'Поменять валюты местами', converterRate: 'Курс', converterResult: 'Результат', converterDate: 'Дата курса', converterError: 'Не удалось выполнить конвертацию', converterSame: 'Одинаковые валюты: сумма не меняется', converterDisclaimer: 'Справочный расчёт, не курс для исполнения сделки; итог банка или обменника может отличаться.', converterSearchCurrency: 'Поиск по коду или названию валюты', converterChooseCurrency: 'Выбрать валюту', converterNoCurrencies: 'Ничего не найдено. Попробуй другой запрос.', converterClosePicker: 'Закрыть окно выбора валюты',
    signalsUnavailable: 'Создание и отправка сигналов ещё не реализованы.',
    newsUnavailable: 'Новости и экономический календарь пока не подключены к подтверждённому источнику.',
    portfolioTitle: 'Мой портфель', portfolioSubtitle: 'Ручные позиции с оценкой по последней доступной котировке Binance Spot',
    portfolioAdd: 'Добавить позицию', portfolioPair: 'Криптовалюта', portfolioPairHint: 'Найти по названию или тикеру', portfolioQuantity: 'Количество',
    portfolioSearchHint: 'Начни вводить название или тикер', portfolioPopular: 'Популярные активы', portfolioNoMatches: 'Ничего не найдено', portfolioChoose: 'Выбрать', portfolioPairCaption: 'Торговая пара', portfolioSearchLoading: 'Загружаем рынок…', portfolioMarketError: 'Рыночные данные не загружены. Проверь сервер и подключение.',
    portfolioEntry: 'Цена покупки за 1 актив (необязательно)', portfolioSave: 'Добавить', portfolioEmpty: 'Пока нет позиций. Добавь первую позицию ниже.',
    portfolioValue: 'Текущая стоимость', portfolioCost: 'Стоимость покупки', portfolioPnl: 'Нереализованный P/L', portfolioPnlPercent: 'Изменение',
    portfolioCurrentPrice: 'Текущая цена', portfolioUnknownPrice: 'Нет актуальной цены для этой пары', portfolioTotals: 'Оценка по валюте котировки',
    portfolioDelete: 'Удалить позицию', portfolioUpdated: 'Цены получены', portfolioInfo: 'Текущая стоимость рассчитывается по публичной котировке Binance Spot. P/L отображается только если указана цена покупки. Разные валюты котировки не суммируются между собой.',
    portfolioLoadError: 'Не удалось загрузить портфель', portfolioSaveError: 'Не удалось сохранить позицию', portfolioDeleteError: 'Не удалось удалить позицию',
    portfolioEntryHint: 'Без цены покупки стоимость будет показана, но P/L рассчитан не будет.',
    quoteFresh: 'Котировки актуальны', quoteStale: 'Данные устаревают', quoteUnavailable: 'Нет свежих данных', quoteNoPositions: 'Добавь позицию, чтобы отслеживать актуальность котировок.', quoteAge: 'Обновлено', quoteAutoRefresh: 'Автообновление каждые 15 секунд', quoteAgeSeconds: 'сек. назад',
  },
  en: {
    terminal: 'Terminal', markets: 'Crypto markets', currencies: 'Currencies', signals: 'Alerts',
    news: 'News', portfolio: 'Portfolio', watch: 'Watchlist', settings: 'Settings',
    live: 'CRYPTO MARKET · SPOT', subtitle: 'Binance Spot quotes · fetched on request',
    search: 'Search instrument', price: 'Price', change: '24h', volume: 'Volume', chart: 'Price chart',
    loading: 'Loading market data…', error: 'Could not load market data', retry: 'Refresh',
    source: 'Source', notice: 'Commercial display and redistribution rights for market data require separate review.',
    add: 'Add to watchlist', remove: 'Remove from watchlist', noData: 'No data', lang: 'Language',
    theme: 'Theme', dark: 'Dark', light: 'Light', fxTitle: 'Official currency rates',
    fxSubtitle: 'Daily reference rates from the Bank of Russia', fxNotice: 'These are official reference/accounting rates, not realtime tradable Forex quotes. They are updated according to the Bank of Russia publication schedule, not continuously.',
    rateDate: 'Rate date', referenceRate: 'Official rate', stale: 'Provider is unavailable — showing previously fetched data.',
    fxError: 'Could not load official rates', noFx: 'No rates available', base: 'Currency', rate: 'Rate in RUB',
    official: 'Official daily rate', fxMarketType: 'DAILY REFERENCE EXCHANGE RATES', cbrLink: 'Open Bank of Russia website',
    fxWorldTitle: 'World reference rates', fxWorldSubtitle: 'Daily rates based on central-bank and official-source data',
    fxWorldSource: 'World rates', fxCbrSource: 'Bank of Russia', fxBase: 'Base currency', fxWorldError: 'Could not load world reference rates',
    fxWorldNotice: 'These are daily reference rates, not real-time Forex quotes. Available currencies depend on the provider.',
    fxSearch: 'Search currency by code or name', fxShowing: 'Showing', fxLoadMore: 'Load more', fxCurrencyCount: 'currencies with available rates', fxNoSearch: 'No currencies match your search',
    fxUnavailable: 'The provider did not return these currencies for the selected base:', fxRefSource: 'Open Frankfurter API',
    converterTitle: 'Currency converter', converterSubtitle: 'Calculated using the latest available reference rate', converterAmount: 'Amount', converterFrom: 'From currency', converterTo: 'To currency', converterButton: 'Convert', converterSwap: 'Swap currencies', converterRate: 'Rate', converterResult: 'Result', converterDate: 'Rate date', converterError: 'Could not convert this amount', converterSame: 'Currencies match: the amount stays the same', converterDisclaimer: 'Reference calculation, not an executable transaction rate; banks and exchanges may offer different rates.', converterSearchCurrency: 'Search by currency code or name', converterChooseCurrency: 'Choose currency', converterNoCurrencies: 'No currencies found. Try another search.', converterClosePicker: 'Close currency picker',
    signalsUnavailable: 'Alert evaluation and delivery are not implemented yet.',
    newsUnavailable: 'News and the economic calendar are not connected to a verified provider yet.',
    portfolioTitle: 'My portfolio', portfolioSubtitle: 'Manual positions valued using the latest available Binance Spot quote',
    portfolioAdd: 'Add position', portfolioPair: 'Cryptocurrency', portfolioPairHint: 'Search by name or ticker', portfolioQuantity: 'Quantity',
    portfolioSearchHint: 'Start typing a name or ticker', portfolioPopular: 'Popular assets', portfolioNoMatches: 'No assets found', portfolioChoose: 'Select', portfolioPairCaption: 'Trading pair', portfolioSearchLoading: 'Loading market…', portfolioMarketError: 'Market data could not be loaded. Check the API server and connection.',
    portfolioEntry: 'Entry price per asset (optional)', portfolioSave: 'Add position', portfolioEmpty: 'No positions yet. Add your first position below.',
    portfolioValue: 'Current value', portfolioCost: 'Cost basis', portfolioPnl: 'Unrealized P/L', portfolioPnlPercent: 'Change',
    portfolioCurrentPrice: 'Current price', portfolioUnknownPrice: 'No current price for this pair', portfolioTotals: 'Valuation by quote asset',
    portfolioDelete: 'Delete position', portfolioUpdated: 'Prices fetched', portfolioInfo: 'Current value uses public Binance Spot quotes. P/L is shown only when an entry price is provided. Values in different quote currencies are not added together.',
    portfolioLoadError: 'Could not load portfolio', portfolioSaveError: 'Could not save position', portfolioDeleteError: 'Could not delete position',
    portfolioEntryHint: 'Without an entry price, current value is shown but P/L cannot be calculated.',
    quoteFresh: 'Quotes are fresh', quoteStale: 'Data is getting stale', quoteUnavailable: 'No fresh data', quoteNoPositions: 'Add a position to track quote freshness.', quoteAge: 'Updated', quoteAutoRefresh: 'Auto-refresh every 15 seconds', quoteAgeSeconds: 'sec ago',
  },
} as const;

const coinNames: Record<string, { ru: string; en: string }> = {
  BTC: { ru: 'Биткоин', en: 'Bitcoin' }, ETH: { ru: 'Эфириум', en: 'Ethereum' },
  BNB: { ru: 'БНБ', en: 'BNB' }, SOL: { ru: 'Солана', en: 'Solana' }, XRP: { ru: 'Рипл', en: 'XRP' },
  ADA: { ru: 'Кардано', en: 'Cardano' }, DOGE: { ru: 'Догикоин', en: 'Dogecoin' }, TON: { ru: 'Тонкоин', en: 'Toncoin' },
  TRX: { ru: 'Трон', en: 'TRON' }, DOT: { ru: 'Полкадот', en: 'Polkadot' }, LTC: { ru: 'Лайткоин', en: 'Litecoin' },
  BCH: { ru: 'Биткоин Кэш', en: 'Bitcoin Cash' }, LINK: { ru: 'Чейнлинк', en: 'Chainlink' }, AVAX: { ru: 'Аваланч', en: 'Avalanche' },
  SHIB: { ru: 'Шиба-ину', en: 'Shiba Inu' }, UNI: { ru: 'Юнисвап', en: 'Uniswap' }, ATOM: { ru: 'Космос', en: 'Cosmos' },
  XLM: { ru: 'Стеллар', en: 'Stellar' }, ETC: { ru: 'Эфириум Классик', en: 'Ethereum Classic' }, FIL: { ru: 'Файлкоин', en: 'Filecoin' },
  APT: { ru: 'Аптос', en: 'Aptos' }, ARB: { ru: 'Арбитрум', en: 'Arbitrum' }, OP: { ru: 'Оптимизм', en: 'Optimism' },
  NEAR: { ru: 'Near Protocol', en: 'NEAR Protocol' }, SUI: { ru: 'Суи', en: 'Sui' }, INJ: { ru: 'Инжектив', en: 'Injective' },
  AAVE: { ru: 'Ааве', en: 'Aave' }, MKR: { ru: 'Мейкер', en: 'Maker' }, ICP: { ru: 'Internet Computer', en: 'Internet Computer' },
  PEPE: { ru: 'Пепе', en: 'Pepe' }, WLD: { ru: 'Worldcoin', en: 'Worldcoin' }, FET: { ru: 'Fetch.ai', en: 'Fetch.ai' },
  USDT: { ru: 'Тезер', en: 'Tether' }, USDC: { ru: 'ЮСДК', en: 'USD Coin' }, FDUSD: { ru: 'First Digital USD', en: 'First Digital USD' },
  DAI: { ru: 'Дай', en: 'Dai' }, TUSD: { ru: 'TrueUSD', en: 'TrueUSD' }, PAXG: { ru: 'Золотой токен PAX', en: 'PAX Gold' },
};

const quoteAssets = ['USDT', 'USDC', 'FDUSD', 'BTC', 'ETH', 'BNB', 'EUR', 'TRY', 'BRL', 'USD'];
function splitTradingPair(symbol: string): { base: string; quote: string } {
  const quote = quoteAssets.find((candidate) => symbol.endsWith(candidate) && symbol.length > candidate.length) ?? '';
  return quote ? { base: symbol.slice(0, -quote.length), quote } : { base: symbol, quote: '' };
}
function coinName(base: string, lang: Lang): string {
  return coinNames[base]?.[lang] ?? base;
}
const coinAliases: Record<string, string[]> = {
  BTC: ['bitcoin', 'биткоин', 'биткойн'], ETH: ['ethereum', 'ether', 'эфир', 'эфириум'],
  XRP: ['ripple', 'рипл'], DOGE: ['dogecoin', 'доджкоин', 'догикоин'], TON: ['toncoin', 'тонкоин'],
  SOL: ['solana', 'солана'], BNB: ['binance coin', 'бинанс коин'], ADA: ['cardano', 'кардано'],
  LTC: ['litecoin', 'лайткоин'], BCH: ['bitcoin cash', 'биткоин кэш'], LINK: ['chainlink', 'чейнлинк'],
  AVAX: ['avalanche', 'аваланш'], SHIB: ['shiba inu', 'шиба ину'], DOT: ['polkadot', 'полкадот'],
  USDT: ['tether', 'тезер', 'usdt'], USDC: ['usd coin', 'юсдк'],
};

function formatRate(value: string, lang: Lang): string {
  return new Intl.NumberFormat(lang === 'ru' ? 'ru-RU' : 'en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(Number(value));
}

function formatConversionNumber(value: string, lang: Lang): string {
  return new Intl.NumberFormat(lang === 'ru' ? 'ru-RU' : 'en-US', {
    maximumFractionDigits: 8,
  }).format(Number(value));
}

function formatRateDate(value: string, lang: Lang): string {
  const date = new Date(`${value}T12:00:00Z`);
  return new Intl.DateTimeFormat(lang === 'ru' ? 'ru-RU' : 'en-GB', {
    day: '2-digit', month: 'long', year: 'numeric', timeZone: 'UTC',
  }).format(date);
}

export default function App() {
  const [lang, setLang] = useState<Lang>('ru');
  const [dark, setDark] = useState(true);
  const [page, setPage] = useState<Page>('terminal');
  const [tickers, setTickers] = useState<Ticker[]>([]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [selected, setSelected] = useState('BTCUSDT');
  const [search, setSearch] = useState('');
  const [favorites, setFavorites] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [marketDataError, setMarketDataError] = useState('');
  const [chartError, setChartError] = useState('');
  const [busy, setBusy] = useState(false);
  const [fx, setFx] = useState<OfficialFxResponse | null>(null);
  const [fxError, setFxError] = useState('');
  const [fxBusy, setFxBusy] = useState(false);
  const [fxMode, setFxMode] = useState<FxMode>('world');
  const [worldBase, setWorldBase] = useState('EUR');
  const [worldFx, setWorldFx] = useState<WorldFxResponse | null>(null);
  const [worldFxError, setWorldFxError] = useState('');
  const [worldFxBusy, setWorldFxBusy] = useState(false);
  const [worldCurrencies, setWorldCurrencies] = useState<FxCurrency[]>([]);
  const [worldCurrencySearch, setWorldCurrencySearch] = useState('');
  const [worldFxVisibleCount, setWorldFxVisibleCount] = useState(40);
  const [converterAmount, setConverterAmount] = useState('100');
  const [converterFrom, setConverterFrom] = useState('USD');
  const [converterTo, setConverterTo] = useState('EUR');
  const [converterResult, setConverterResult] = useState<FxConversionResponse | null>(null);
  const [converterError, setConverterError] = useState('');
  const [converterBusy, setConverterBusy] = useState(false);
  const [converterPicker, setConverterPicker] = useState<ConverterPickerTarget>(null);
  const [converterCurrencySearch, setConverterCurrencySearch] = useState('');
  const [portfolioData, setPortfolioData] = useState<PortfolioResponse | null>(null);
  const [portfolioBusy, setPortfolioBusy] = useState(false);
  const [portfolioError, setPortfolioError] = useState('');
  const [portfolioFormError, setPortfolioFormError] = useState('');
  const [clockNow, setClockNow] = useState(Date.now());
  const [signalData, setSignalData] = useState<any>(null);
  const [signalError, setSignalError] = useState('');
  const [signalBusy, setSignalBusy] = useState(false);
  const [signalInterval, setSignalInterval] = useState('1h');
  const [newsData, setNewsData] = useState<any>(null);
  const [newsError, setNewsError] = useState('');
  const [newsBusy, setNewsBusy] = useState(false);
  const [planData, setPlanData] = useState<any>(null);
  const [planError, setPlanError] = useState('');
  const [planBusy, setPlanBusy] = useState(false);
  const [positionSymbol, setPositionSymbol] = useState('BTCUSDT');
  const [positionSearch, setPositionSearch] = useState('Bitcoin (BTC)');
  const [positionPickerOpen, setPositionPickerOpen] = useState(false);
  const [positionQuantity, setPositionQuantity] = useState('');
  const [positionEntryPrice, setPositionEntryPrice] = useState('');
  const t = words[lang];
  const availableFxCurrencies = worldCurrencies.length ? worldCurrencies : FALLBACK_FX_CURRENCIES;
  const converterPickerResults = useMemo(() => {
    const query = converterCurrencySearch.trim().toLocaleLowerCase();
    const items = availableFxCurrencies;
    if (!query) return items;
    return items.filter(currency =>
      currency.code.toLocaleLowerCase().includes(query)
      || currency.name.toLocaleLowerCase().includes(query)
      || currency.symbol.toLocaleLowerCase().includes(query)
    ).sort((a, b) => Number(a.code.toLocaleLowerCase() !== query) - Number(b.code.toLocaleLowerCase() !== query) || a.code.localeCompare(b.code));
  }, [availableFxCurrencies, converterCurrencySearch]);
  const converterFromInfo = availableFxCurrencies.find(currency => currency.code === converterFrom) ?? FALLBACK_FX_CURRENCIES[0];
  const converterToInfo = availableFxCurrencies.find(currency => currency.code === converterTo) ?? FALLBACK_FX_CURRENCIES[1];
  const quoteUpdatedMs = portfolioData?.updated_at ? Date.parse(portfolioData.updated_at) : NaN;
  const quoteAgeSeconds = Number.isFinite(quoteUpdatedMs) ? Math.max(0, Math.floor((clockNow - quoteUpdatedMs) / 1000)) : null;
  const quoteStatus = !portfolioData?.items.length || quoteAgeSeconds === null || quoteAgeSeconds > 120
    ? 'unavailable' : quoteAgeSeconds >= 30 ? 'stale' : 'fresh';
  const filteredWorldRates = useMemo(() => {
    const query = worldCurrencySearch.trim().toLocaleLowerCase();
    const names = new Map(worldCurrencies.map((currency) => [currency.code, currency]));
    const items = worldFx?.items ?? [];
    if (!query) return items;
    return items.filter((item) => {
      const currency = names.get(item.quote);
      return item.quote.toLocaleLowerCase().includes(query)
        || (currency?.name ?? '').toLocaleLowerCase().includes(query)
        || (currency?.symbol ?? '').toLocaleLowerCase().includes(query);
    });
  }, [worldFx, worldCurrencySearch, worldCurrencies]);

  async function load() {
    setBusy(true);
    setError('');
    setMarketDataError('');
    setChartError('');
    let tickersLoaded = false;
    try {
      const response = await api<{ items: Ticker[] }>('/api/market/tickers');
      if (!Array.isArray(response.items) || response.items.length === 0) throw new Error('Market API returned no ticker data');
      setTickers(response.items);
      tickersLoaded = true;
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setMarketDataError(message);
      setError(message);
    }
    try {
      const candleResponse = await api<{ items: Candle[] }>(`/api/market/klines?symbol=${encodeURIComponent(selected)}&interval=1h&limit=180`);
      if (!Array.isArray(candleResponse.items)) throw new Error('Market API returned invalid candle data');
      setCandles(candleResponse.items);
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setCandles([]);
      setChartError(message);
      if (!tickersLoaded) setError(message);
    } finally {
      setBusy(false);
    }
  }

  async function loadCurrencyCatalog() {
    try {
      const response = await api<FxCurrencyCatalog>('/api/fx/currencies');
      setWorldCurrencies(response.items);
    } catch (e) {
      setWorldFxError(e instanceof Error ? e.message : String(e));
    }
  }

  async function loadWorldRates(base: string = worldBase) {
    setWorldFxBusy(true);
    setWorldFxError('');
    setWorldFxVisibleCount(40);
    try {
      // Omitting quotes asks Frankfurter for every currency it currently supports.
      const response = await api<WorldFxResponse>(`/api/fx/world/daily?base=${encodeURIComponent(base)}`);
      setWorldFx(response);
    } catch (e) {
      setWorldFxError(e instanceof Error ? e.message : String(e));
    } finally {
      setWorldFxBusy(false);
    }
  }

  function openConverterPicker(target: Exclude<ConverterPickerTarget, null>) {
    setConverterCurrencySearch('');
    setConverterPicker(target);
  }

  function chooseConverterCurrency(code: string) {
    if (converterPicker === 'from') setConverterFrom(code);
    if (converterPicker === 'to') setConverterTo(code);
    setConverterResult(null);
    setConverterError('');
    setConverterPicker(null);
    setConverterCurrencySearch('');
  }

  async function runCurrencyConversion(event?: FormEvent) {
    event?.preventDefault();
    const amount = Number(converterAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setConverterResult(null);
      setConverterError(lang === 'ru' ? 'Введи сумму больше нуля.' : 'Enter an amount greater than zero.');
      return;
    }
    setConverterBusy(true);
    setConverterError('');
    try {
      const result = await api<FxConversionResponse>(`/api/fx/convert?amount=${encodeURIComponent(converterAmount)}&from_currency=${encodeURIComponent(converterFrom)}&to_currency=${encodeURIComponent(converterTo)}`);
      setConverterResult(result);
    } catch (e) {
      setConverterResult(null);
      setConverterError(e instanceof Error ? e.message : String(e));
    } finally {
      setConverterBusy(false);
    }
  }

  async function loadOfficialRates() {
    setFxBusy(true);
    setFxError('');
    try {
      const response = await api<OfficialFxResponse>('/api/fx/cbr/daily');
      setFx(response);
    } catch (e) {
      setFxError(e instanceof Error ? e.message : String(e));
    } finally {
      setFxBusy(false);
    }
  }

  async function loadWatchlist() {
    try {
      const response = await api<{ items: string[] }>('/api/watchlist');
      setFavorites(response.items.map((symbol) => symbol.toUpperCase()));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function loadPortfolio() {
    setPortfolioBusy(true);
    setPortfolioError('');
    try {
      const response = await api<PortfolioResponse>('/api/portfolio');
      setPortfolioData(response);
    } catch (e) {
      setPortfolioError(e instanceof Error ? e.message : String(e));
    } finally {
      setPortfolioBusy(false);
    }
  }

  async function loadSignals() {
    setSignalBusy(true); setSignalError('');
    try { setSignalData(await api<any>(`/api/signals?symbol=${encodeURIComponent(selected)}&interval=${signalInterval}`)); }
    catch (e) { setSignalError(e instanceof Error ? e.message : String(e)); }
    finally { setSignalBusy(false); }
  }

  async function loadNews() {
    setNewsBusy(true); setNewsError('');
    try { setNewsData(await api<any>('/api/news?limit=20')); }
    catch (e) { setNewsError(e instanceof Error ? e.message : String(e)); }
    finally { setNewsBusy(false); }
  }

  async function loadPlans() {
    setPlanBusy(true); setPlanError('');
    try { setPlanData(await api<any>('/api/plans')); }
    catch (e) { setPlanError(e instanceof Error ? e.message : String(e)); }
    finally { setPlanBusy(false); }
  }

  async function startProCheckout() {
    setPlanBusy(true); setPlanError('');
    try {
      const result = await api<{invoice_url: string}>('/api/subscription/pro/invoice', { method: 'POST' });
      const webApp = window.Telegram?.WebApp;
      if (webApp?.openInvoice) {
        webApp.openInvoice(result.invoice_url, (status) => { if (status === 'paid') void loadPlans(); });
      } else {
        window.open(result.invoice_url, '_blank', 'noopener,noreferrer');
      }
    } catch (e) { setPlanError(e instanceof Error ? e.message : String(e)); }
    finally { setPlanBusy(false); }
  }

  async function addPortfolioPosition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPortfolioFormError('');
    const quantity = Number(positionQuantity);
    const entry = positionEntryPrice.trim() ? Number(positionEntryPrice) : null;
    if (!positionSymbol.trim() || !Number.isFinite(quantity) || quantity <= 0 || (entry !== null && (!Number.isFinite(entry) || entry <= 0))) {
      setPortfolioFormError(t.portfolioSaveError);
      return;
    }
    try {
      await api('/api/portfolio', {
        method: 'POST',
        body: JSON.stringify({
          symbol: positionSymbol.trim().toUpperCase(),
          quantity: positionQuantity,
          average_entry_price: positionEntryPrice.trim() ? positionEntryPrice.trim() : null,
        }),
      });
      setPositionQuantity('');
      setPositionEntryPrice('');
      setPositionSearch('');
      setPositionSymbol('');
      setPositionPickerOpen(false);
      await loadPortfolio();
    } catch (e) {
      setPortfolioFormError(e instanceof Error ? e.message : t.portfolioSaveError);
    }
  }

  async function deletePortfolioPosition(positionId: number) {
    setPortfolioFormError('');
    try {
      await api(`/api/portfolio/${positionId}`, { method: 'DELETE' });
      await loadPortfolio();
    } catch (e) {
      setPortfolioFormError(e instanceof Error ? e.message : t.portfolioDeleteError);
    }
  }

  function formatAmount(value: string | null | undefined, maximumFractionDigits = 8): string {
    if (value === null || value === undefined) return '—';
    const number = Number(value);
    if (!Number.isFinite(number)) return '—';
    return new Intl.NumberFormat(lang === 'ru' ? 'ru-RU' : 'en-US', {
      maximumFractionDigits,
      minimumFractionDigits: 0,
    }).format(number);
  }

  useEffect(() => {
    if (!converterPicker) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setConverterPicker(null);
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [converterPicker]);

  useEffect(() => {
    void loadWatchlist();
    // The watchlist is user-specific and must be loaded from the API, not seeded in the UI.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (page !== 'portfolio') return;
    void loadPortfolio();
    const refreshTimer = window.setInterval(() => void loadPortfolio(), 15_000);
    const clockTimer = window.setInterval(() => setClockNow(Date.now()), 5_000);
    return () => { window.clearInterval(refreshTimer); window.clearInterval(clockTimer); };
    // Refresh while the portfolio is visible; stop polling when leaving the page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  useEffect(() => {
    window.Telegram?.WebApp?.ready?.();
    window.Telegram?.WebApp?.expand?.();
    void load();
    // selected is intentionally included so changing a crypto instrument refreshes its candles.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  useEffect(() => {
    if (page === 'signals') void loadSignals();
    // Keep the technical overview synchronized with the selected market and timeframe.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, selected, signalInterval]);

  useEffect(() => {
    if (page !== 'currencies') return;
    if (worldCurrencies.length === 0) void loadCurrencyCatalog();
    if (fxMode === 'world' && worldFx === null && !worldFxBusy) void loadWorldRates();
    if (fxMode === 'cbr' && fx === null && !fxBusy) void loadOfficialRates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, fxMode]);

  const filtered = useMemo(() => tickers
    .filter(item => item.symbol.includes(search.toUpperCase()))
    .sort((a, b) => Number(favorites.includes(b.symbol)) - Number(favorites.includes(a.symbol)))
    .slice(0, 80), [tickers, search, favorites]);
  const current = tickers.find(item => item.symbol === selected);
  const portfolioSuggestions = useMemo(() => {
    const query = positionSearch.trim().toLocaleLowerCase();
    const quoteRank = (quote: string) => {
      const rank = quoteAssets.indexOf(quote);
      return rank < 0 ? 999 : rank;
    };
    const candidates = tickers
      .map((ticker) => ({ ...ticker, ...splitTradingPair(ticker.symbol) }))
      .filter((ticker) => ticker.quote.length > 0)
      .sort((a, b) => quoteRank(a.quote) - quoteRank(b.quote) || Number(b.quote_volume) - Number(a.quote_volume));
    const bestByBase = new Map<string, typeof candidates[number]>();
    for (const item of candidates) {
      if (!bestByBase.has(item.base)) bestByBase.set(item.base, item);
    }
    const unique = [...bestByBase.values()];
    const matching = query ? unique.filter((item) => {
      const nameRu = coinName(item.base, 'ru').toLocaleLowerCase();
      const nameEn = coinName(item.base, 'en').toLocaleLowerCase();
      return item.base.toLocaleLowerCase().includes(query)
        || item.symbol.toLocaleLowerCase().includes(query)
        || nameRu.includes(query)
        || nameEn.includes(query)
        || (coinAliases[item.base] ?? []).some((alias) => alias.includes(query));
    }) : unique;
    return matching
      .sort((a, b) => query
        ? Number(a.base.toLocaleLowerCase() !== query) - Number(b.base.toLocaleLowerCase() !== query) || Number(b.quote_volume) - Number(a.quote_volume)
        : Number(b.quote_volume) - Number(a.quote_volume))
      .slice(0, 8);
  }, [tickers, positionSearch, lang]);

  function choosePortfolioAsset(symbol: string) {
    const pair = splitTradingPair(symbol);
    setPositionSymbol(symbol);
    setPositionSearch(`${coinName(pair.base, lang)} (${pair.base})`);
    setPositionPickerOpen(false);
    setPortfolioFormError('');
  }

  async function toggle(symbol: string) {
    const isSaved = favorites.includes(symbol);
    const next = isSaved ? favorites.filter(item => item !== symbol) : [...favorites, symbol];
    try {
      if (isSaved) await api(`/api/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' });
      else await api('/api/watchlist', { method: 'POST', body: JSON.stringify({ symbol }) });
      setFavorites(next);
    } catch (e) {
      // Keep the UI in sync with persisted state when the API request fails.
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function showUnavailable(message: string) {
    setError(message);
    setPage('terminal');
  }

  return (
    <main className={dark ? 'app dark' : 'app light'}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><Activity size={20} /></div>
          <span>Market<span className="brand-accent">Pulse</span><small>MARKET INTELLIGENCE</small></span>
        </div>
        <nav>
          <button className={`nav ${page === 'terminal' ? 'active' : ''}`} onClick={() => { setPage('terminal'); setError(''); }}><LayoutDashboard size={17} />{t.terminal}</button>
          <button className={`nav ${page === 'terminal' ? '' : ''}`} onClick={() => { setPage('terminal'); setError(''); document.getElementById('markets')?.scrollIntoView({ behavior: 'smooth' }); }}><ChartCandlestick size={17} />{t.markets}</button>
          <button className={`nav ${page === 'currencies' ? 'active' : ''}`} onClick={() => { setPage('currencies'); setFxError(''); }}><ArrowLeftRight size={17} />{t.currencies}</button>
          <button className={`nav ${page === 'signals' ? 'active' : ''}`} onClick={() => { setPage('signals'); }}><Bell size={17} />{t.signals}</button>
          <button className={`nav ${page === 'news' ? 'active' : ''}`} onClick={() => { setPage('news'); void loadNews(); }}><Newspaper size={17} />{t.news}</button>
          <button className={`nav ${page === 'portfolio' ? 'active' : ''}`} onClick={() => { setPage('portfolio'); setPortfolioError(''); setPortfolioFormError(''); }}><Wallet size={17} />{t.portfolio}</button>
          <button className={`nav ${page === 'plans' ? 'active' : ''}`} onClick={() => { setPage('plans'); void loadPlans(); }}><Star size={17} />{lang === 'ru' ? 'Тарифы Free / Pro' : 'Free / Pro plans'}</button>
          <button className="nav" onClick={() => { setPage('terminal'); setError(''); document.getElementById('markets')?.scrollIntoView({ behavior: 'smooth' }); }}><Star size={17} />{t.watch}</button>
        </nav>
        <div className="side-bottom">
          <span className="connection"><i />{error || fxError ? 'API issue' : 'API connected'}</span>
          <button className="nav" onClick={() => setDark(!dark)}>{dark ? <Sun size={17} /> : <Moon size={17} />} {t.theme}: {dark ? t.dark : t.light}</button>
          <button className="nav" onClick={() => setLang(lang === 'ru' ? 'en' : 'ru')}><Globe size={17} />{t.lang}: {lang.toUpperCase()}</button>
          <div className="chart-credit">Charts by TradingView · Apache 2.0</div>
        </div>
      </aside>

      <section className="workspace">
        {page === 'signals' ? (
          <>
            <header className="topbar"><div><div className="eyebrow">BINANCE SPOT · TECHNICAL STUDY</div><h1>{lang === 'ru' ? 'Рыночные сигналы' : 'Market signals'}<span className="dot-live" /></h1><p>{lang === 'ru' ? 'Индикаторы по закрытым свечам — без обещаний прибыли' : 'Indicators from closed candles — no profit promises'}</p></div><button className="refresh" onClick={() => void loadSignals()} disabled={signalBusy}><RefreshCw size={16} className={signalBusy ? 'spin' : ''}/>{lang === 'ru' ? 'Обновить' : 'Refresh'}</button></header>
            <div className="signal-controls panel"><label>{lang === 'ru' ? 'Инструмент' : 'Instrument'}<select value={selected} onChange={e => setSelected(e.target.value)}>{tickers.slice(0,100).map(x => <option key={x.symbol} value={x.symbol}>{x.symbol}</option>)}</select></label><label>{lang === 'ru' ? 'Таймфрейм' : 'Timeframe'}<select value={signalInterval} onChange={e => {setSignalInterval(e.target.value);}}><option value="15m">15m</option><option value="1h">1h</option><option value="4h">4h</option><option value="1d">1d</option></select></label></div>
            {signalError && <div className="error-banner">{signalError}</div>}
            {signalData && <><section className="signal-hero panel"><div><span className="eyebrow">{signalData.symbol} · {signalData.interval}</span><h2>{signalData.label === 'bullish_bias' ? (lang === 'ru' ? 'Преобладает бычий импульс' : 'Bullish bias') : signalData.label === 'bearish_bias' ? (lang === 'ru' ? 'Преобладает медвежий импульс' : 'Bearish bias') : (lang === 'ru' ? 'Смешанная картина' : 'Mixed picture')}</h2><p>{lang === 'ru' ? 'Оценка индикаторов, не команда на покупку или продажу.' : 'Indicator summary, not a buy or sell instruction.'}</p></div><div className="signal-score"><strong>{signalData.score > 0 ? '+' : ''}{signalData.score}</strong><small>{lang === 'ru' ? 'балл импульса' : 'momentum score'}</small></div></section><section className="signal-indicators"><article className="panel"><span>RSI · 14</span><strong>{signalData.indicators.rsi14}</strong><small>{signalData.indicators.rsi14 >= 70 ? (lang === 'ru' ? 'Возможная перекупленность' : 'Potentially overbought') : signalData.indicators.rsi14 <= 30 ? (lang === 'ru' ? 'Возможная перепроданность' : 'Potentially oversold') : (lang === 'ru' ? 'Нейтральная зона' : 'Neutral zone')}</small></article><article className="panel"><span>EMA · 20</span><strong>{formatAmount(String(signalData.indicators.ema20), 4)}</strong><small>{lang === 'ru' ? 'Краткосрочный тренд' : 'Short-term trend'}</small></article><article className="panel"><span>EMA · 50</span><strong>{formatAmount(String(signalData.indicators.ema50), 4)}</strong><small>{lang === 'ru' ? 'Среднесрочный тренд' : 'Medium-term trend'}</small></article><article className="panel"><span>MACD HIST.</span><strong className={signalData.indicators.macd_histogram >= 0 ? 'positive' : 'negative'}>{formatAmount(String(signalData.indicators.macd_histogram), 5)}</strong><small>{lang === 'ru' ? 'Импульс' : 'Momentum'}</small></article><article className="panel"><span>BOLLINGER · PRO</span>{signalData.pro_features ? <><strong>{formatAmount(String(signalData.indicators.bollinger_middle), 4)}</strong><small>{lang === 'ru' ? `Диапазон ${formatAmount(String(signalData.indicators.bollinger_lower), 4)} — ${formatAmount(String(signalData.indicators.bollinger_upper), 4)}` : `Range ${formatAmount(String(signalData.indicators.bollinger_lower), 4)} — ${formatAmount(String(signalData.indicators.bollinger_upper), 4)}`}</small></> : <><strong>🔒 Pro</strong><small>{lang === 'ru' ? 'Полосы Боллинджера доступны в Pro' : 'Bollinger Bands are included in Pro'}</small><button className="inline-upgrade" onClick={() => {setPage('plans'); void loadPlans();}}>{lang === 'ru' ? 'Открыть тарифы' : 'View plans'}</button></>}</article></section><section className="panel signal-reasons"><div className="panel-head"><div><span className="eyebrow">WHY THIS SUMMARY</span><h2>{lang === 'ru' ? 'Что повлияло на оценку' : 'What shaped the summary'}</h2></div></div>{signalData.reasons.map((reason: string, i: number) => <div className="signal-reason" key={i}><span>{i+1}</span><p>{reason}</p></div>)}<div className="signal-meta">{lang === 'ru' ? 'Свеча закрыта' : 'Closed candle'}: {new Date(signalData.candle_closed_at).toLocaleString()} · {signalData.source}</div></section></>}
            {!signalData && !signalError && <div className="empty panel">{signalBusy ? t.loading : (lang === 'ru' ? 'Выбери инструмент и обнови анализ.' : 'Choose an instrument and refresh analysis.')}</div>}
            <div className="disclaimer"><Settings size={15}/><span>{lang === 'ru' ? 'Сигналы рассчитаны по историческим свечам Binance Spot. Технические индикаторы могут ошибаться и не предсказывают будущее.' : 'Signals use historical Binance Spot candles. Technical indicators can be wrong and do not predict the future.'}</span></div>
          </>
        ) : page === 'news' ? (
          <>
            <header className="topbar"><div><div className="eyebrow">THIRD-PARTY RSS · ORIGINAL SOURCES</div><h1>{lang === 'ru' ? 'Криптоновости' : 'Crypto news'}<span className="dot-live" /></h1><p>{lang === 'ru' ? 'Заголовки с переходом к оригинальной публикации' : 'Headlines linked to original publishers'}</p></div><button className="refresh" onClick={() => void loadNews()} disabled={newsBusy}><RefreshCw size={16} className={newsBusy ? 'spin' : ''}/>{lang === 'ru' ? 'Обновить' : 'Refresh'}</button></header>
            {newsError && <div className="error-banner">{newsError}</div>}{newsData && <div className="plan-note">{lang === 'ru' ? `Тариф ${newsData.plan.toUpperCase()} · доступно заголовков: ${newsData.limit}` : `Plan ${newsData.plan.toUpperCase()} · headlines available: ${newsData.limit}`}</div>}
            <section className="news-grid">{newsData?.items?.map((item: any, i: number) => <article className="panel news-card" key={item.url}><div className="news-card-top"><span>{item.publisher}</span><span>#{String(i+1).padStart(2,'0')}</span></div><h2>{item.title}</h2>{item.published_at && <small>{item.published_at}</small>}<a href={item.url} target="_blank" rel="noreferrer">{lang === 'ru' ? 'Читать у источника' : 'Read at source'} ↗</a></article>)}</section>
            {!newsData && !newsError && <div className="empty panel">{newsBusy ? t.loading : (lang === 'ru' ? 'Загрузка новостей…' : 'Loading news…')}</div>}
            <div className="disclaimer"><Settings size={15}/><span>{lang === 'ru' ? (newsData?.disclaimer || 'Новости предоставляются сторонними издателями. Проверяй лицензии источников перед коммерческим использованием.') : 'News are provided by third-party publishers. Check source licensing before commercial use. Not investment advice.'}</span></div>
          </>
        ) : page === 'plans' ? (
          <>
            <header className="topbar"><div><div className="eyebrow">MEMBERSHIP · TELEGRAM STARS</div><h1>{lang === 'ru' ? 'Выбери свой уровень' : 'Choose your plan'}<span className="dot-live" /></h1><p>{lang === 'ru' ? 'Начни бесплатно и расширяй инструменты по мере роста' : 'Start free and expand your toolkit as you grow'}</p></div><button className="refresh" onClick={() => void loadPlans()} disabled={planBusy}><RefreshCw size={16} className={planBusy ? 'spin' : ''}/>{lang === 'ru' ? 'Обновить' : 'Refresh'}</button></header>
            {planError && <div className="error-banner">{planError}</div>}
            <section className="plans-grid"><article className="panel plan-card"><div className="plan-top"><span>STARTER</span><span className="plan-badge">{lang === 'ru' ? 'БАЗОВЫЙ' : 'BASIC'}</span></div><h2>Free</h2><div className="plan-price">0 <small>{lang === 'ru' ? 'навсегда' : 'forever'}</small></div><p>{lang === 'ru' ? 'Всё необходимое для знакомства с рынком.' : 'Everything you need to explore the market.'}</p><ul><li>✓ {lang === 'ru' ? 'Котировки и графики' : 'Quotes and charts'}</li><li>✓ {lang === 'ru' ? 'Ручной портфель' : 'Manual portfolio'}</li><li>✓ {lang === 'ru' ? 'Технический обзор' : 'Technical overview'}</li><li>✓ {lang === 'ru' ? '5 новостных заголовков' : '5 news headlines'}</li><li>✓ {lang === 'ru' ? 'До 2 правил алертов' : 'Up to 2 alert rules'}</li></ul><button className="plan-secondary" disabled>{planData?.current_plan === 'free' ? (lang === 'ru' ? 'Текущий тариф' : 'Current plan') : 'Free'}</button></article><article className="panel plan-card plan-pro"><div className="plan-top"><span>MARKETPULSE</span><span className="plan-badge pro-badge">PRO</span></div><h2>Pro <span>✦</span></h2><div className="plan-price">{planData?.plans?.find((plan: any) => plan.code === 'pro')?.price ?? 250} <small>⭐ / 30 {lang === 'ru' ? 'дней' : 'days'}</small></div><p>{lang === 'ru' ? 'Для тех, кому нужны более глубокие данные и больше контроля.' : 'For deeper data and more control.'}</p><ul><li>✓ {lang === 'ru' ? 'До 50 новостных заголовков' : 'Up to 50 news headlines'}</li><li>✓ {lang === 'ru' ? 'Полосы Боллинджера в техническом обзоре' : 'Bollinger Bands in technical overview'}</li><li>✓ {lang === 'ru' ? 'До 20 сохранённых правил (автопроверка пока не включена)' : 'Up to 20 saved rules (automatic checks not enabled yet)'}</li><li>✓ {lang === 'ru' ? 'До 100 ручных позиций в портфеле' : 'Up to 100 manual portfolio positions'}</li><li>✓ {lang === 'ru' ? 'Telegram Stars — безопасная оплата внутри Telegram' : 'Telegram Stars payments inside Telegram'}</li></ul><button className="plan-primary" onClick={() => void startProCheckout()} disabled={planBusy || planData?.current_plan === 'pro'}>{planBusy ? '…' : planData?.current_plan === 'pro' ? (lang === 'ru' ? 'Pro активен' : 'Pro active') : (lang === 'ru' ? 'Подключить Pro' : 'Upgrade to Pro')}</button><small className="plan-footnote">{lang === 'ru' ? 'Цена — тестовая гипотеза в Telegram Stars, не рубли. Платёжный сценарий работает только при настроенном боте.' : 'Test price in Telegram Stars, not rubles. Requires a configured bot.'}</small></article></section>
            {planData?.ends_at && <div className="plan-note">{lang === 'ru' ? 'Тариф действует до: ' : 'Plan valid until: '}{new Date(planData.ends_at).toLocaleString()}</div>}
            <div className="disclaimer"><Settings size={15}/><span>{lang === 'ru' ? 'Pro открывается только после подтверждённого платежа Telegram. Не вводи платёжные данные на сторонних сайтах. Перед запуском в продакшен проверь правила Telegram Stars и условия источников данных.' : 'Pro is activated only after Telegram confirms payment. Never enter payment details on third-party sites. Review Telegram Stars and data-source terms before production.'}</span></div>
          </>
        ) : page === 'currencies' ? (
          <>
            <header className="topbar">
              <div>
                <div className="eyebrow">{t.fxMarketType}</div>
                <h1>{fxMode === 'world' ? t.fxWorldTitle : t.fxTitle}<span className="dot-live" /></h1>
                <p>{fxMode === 'world' ? t.fxWorldSubtitle : t.fxSubtitle}</p>
              </div>
              <button className="refresh" onClick={() => void (fxMode === 'world' ? loadWorldRates() : loadOfficialRates())} disabled={fxMode === 'world' ? worldFxBusy : fxBusy}>
                <RefreshCw size={16} className={(fxMode === 'world' ? worldFxBusy : fxBusy) ? 'spin' : ''} />{(fxMode === 'world' ? worldFxBusy : fxBusy) ? '…' : t.retry}
              </button>
            </header>
            <section className="panel currency-converter">
              <div className="converter-heading">
                <div><span className="eyebrow">MARKETPULSE · FX TOOL</span><h2>{t.converterTitle}</h2><p>{t.converterSubtitle}</p></div>
                <span className="converter-mark"><ArrowLeftRight size={19} /></span>
              </div>
              <form className="converter-form" onSubmit={(event) => void runCurrencyConversion(event)}>
                <label>{t.converterAmount}<input aria-label={t.converterAmount} type="number" min="0.00000001" max="1000000000000000" step="any" value={converterAmount} onChange={(event) => { setConverterAmount(event.target.value); setConverterResult(null); setConverterError(''); }} required /></label>
                <div className="converter-picker-field converter-picker-from">
                  <span className="converter-field-label">{t.converterFrom}</span>
                  <button className="currency-picker-trigger" type="button" onClick={() => openConverterPicker('from')} aria-haspopup="dialog" aria-label={`${t.converterFrom}: ${converterFrom} · ${converterFromInfo.name}`}>
                    <span className="currency-picker-code">{converterFromInfo.code}</span>
                    <span className="currency-picker-identity"><strong>{converterFromInfo.name}</strong><small>{converterFromInfo.symbol || converterFromInfo.code} · {converterFromInfo.code}</small></span>
                    <ChevronDown size={19} aria-hidden="true" />
                  </button>
                </div>
                <button className="converter-swap" type="button" title={t.converterSwap} aria-label={t.converterSwap} onClick={() => { setConverterFrom(converterTo); setConverterTo(converterFrom); setConverterResult(null); setConverterError(''); }}><ArrowLeftRight size={19} /></button>
                <div className="converter-picker-field converter-picker-to">
                  <span className="converter-field-label">{t.converterTo}</span>
                  <button className="currency-picker-trigger" type="button" onClick={() => openConverterPicker('to')} aria-haspopup="dialog" aria-label={`${t.converterTo}: ${converterTo} · ${converterToInfo.name}`}>
                    <span className="currency-picker-code">{converterToInfo.code}</span>
                    <span className="currency-picker-identity"><strong>{converterToInfo.name}</strong><small>{converterToInfo.symbol || converterToInfo.code} · {converterToInfo.code}</small></span>
                    <ChevronDown size={19} aria-hidden="true" />
                  </button>
                </div>
                <button className="plan-primary converter-submit" type="submit" disabled={converterBusy}>{converterBusy ? '…' : t.converterButton}</button>
              </form>
              {converterError && <div className="error-banner converter-error" role="alert">{t.converterError}: {converterError}</div>}
              {converterResult && <div className="converter-result" aria-live="polite"><div><span>{t.converterResult}</span><strong>{formatConversionNumber(converterResult.converted_amount, lang)} <em>{converterResult.to_currency}</em></strong></div><div><span>{t.converterRate}</span><strong>1 {converterResult.from_currency} = {formatConversionNumber(converterResult.rate, lang)} {converterResult.to_currency}</strong></div><small>{converterResult.from_currency === converterResult.to_currency ? t.converterSame : `${t.converterDate}: ${converterResult.rate_date ? formatRateDate(converterResult.rate_date, lang) : '—'} · ${converterResult.source}`}{converterResult.stale ? ` · ${t.stale}` : ''}</small></div>}
              <div className="converter-disclaimer">{t.converterDisclaimer}</div>
            </section>
            <div className="fx-controls">
              <div className="fx-mode-switch" role="tablist" aria-label={t.currencies}>
                <button className={fxMode === 'world' ? 'active' : ''} role="tab" aria-selected={fxMode === 'world'} onClick={() => { setFxMode('world'); setWorldFxError(''); }}>{t.fxWorldSource}</button>
                <button className={fxMode === 'cbr' ? 'active' : ''} role="tab" aria-selected={fxMode === 'cbr'} onClick={() => { setFxMode('cbr'); setFxError(''); }}>{t.fxCbrSource}</button>
              </div>
              {fxMode === 'world' && <label className="fx-base-select">{t.fxBase}
                <select value={worldBase} onChange={(event) => { const nextBase = event.target.value; setWorldBase(nextBase); setWorldFx(null); setWorldFxError(''); setWorldCurrencySearch(''); void loadWorldRates(nextBase); }}>
                  {(worldCurrencies.length ? worldCurrencies : [
                    { code: 'EUR', name: 'Euro', symbol: '€', numeric_code: '978', start_date: null, end_date: null },
                    { code: 'USD', name: 'United States Dollar', symbol: '$', numeric_code: '840', start_date: null, end_date: null },
                    { code: 'GBP', name: 'Pound Sterling', symbol: '£', numeric_code: '826', start_date: null, end_date: null },
                    { code: 'CNY', name: 'Chinese Yuan', symbol: '¥', numeric_code: '156', start_date: null, end_date: null },
                    { code: 'CHF', name: 'Swiss Franc', symbol: 'CHF', numeric_code: '756', start_date: null, end_date: null },
                    { code: 'JPY', name: 'Japanese Yen', symbol: '¥', numeric_code: '392', start_date: null, end_date: null },
                  ]).map((currency) => <option key={currency.code} value={currency.code}>{currency.code} · {currency.name}</option>)}
                </select>
              </label>}
            </div>
            {fxMode === 'world' ? (
              <>
                {worldFxError && <div className="error-banner"><span>{t.fxWorldError}: {worldFxError}</span><button onClick={() => setWorldFxError('')}>×</button></div>}
                {worldFx?.stale && <div className="stale-banner">{t.stale}</div>}
                <section className="fx-summary panel">
                  <div>
                    <span className="eyebrow">{t.rateDate}</span>
                    <h2>{worldFx?.rate_date ? formatRateDate(worldFx.rate_date, lang) : (worldFxBusy ? t.loading : '—')}</h2>
                    <p>1 {worldBase} = rate in quote currency</p>
                  </div>
                  <div className="fx-source"><span className="source-label">● {t.source}</span><strong>Frankfurter · reference rates</strong><a href="https://frankfurter.dev/" target="_blank" rel="noreferrer">{t.fxRefSource} ↗</a></div>
                </section>
                <div className="fx-currency-search">
                  <label className="search" htmlFor="fx-currency-search"><Search size={16} /><input id="fx-currency-search" value={worldCurrencySearch} onChange={(event) => { setWorldCurrencySearch(event.target.value); setWorldFxVisibleCount(40); }} placeholder={t.fxSearch} /></label>
                  <span className="count">{filteredWorldRates.length} {t.fxCurrencyCount}</span>
                </div>
                <section className="fx-grid" aria-live="polite">
                  {filteredWorldRates.slice(0, worldFxVisibleCount).map(item => {
                    const currency = worldCurrencies.find((entry) => entry.code === item.quote);
                    return <article className="fx-card panel" key={item.symbol}>
                      <div className="fx-card-top"><span className="fx-currency-code">{item.quote}</span><span className="fx-symbol">{currency?.symbol || item.quote}</span></div>
                      <div className="fx-name">{currency?.name || `${item.base} → ${item.quote}`}</div>
                      <div className="fx-rate">{formatRate(item.rate, lang)}</div>
                      <div className="fx-rate-caption">1 {item.base} = {formatRate(item.rate, lang)} {item.quote}</div>
                      <div className="fx-card-foot"><span>{t.rateDate}</span><strong>{formatRateDate(item.rate_date, lang)}</strong></div>
                    </article>;
                  })}
                  {!filteredWorldRates.length && <div className="empty panel">{worldFxBusy ? t.loading : (worldCurrencySearch ? t.fxNoSearch : (worldFxError || t.noFx))}</div>}
                </section>
                {filteredWorldRates.length > worldFxVisibleCount && <div className="fx-load-more"><button onClick={() => setWorldFxVisibleCount((count) => Math.min(count + 40, filteredWorldRates.length))}>{t.fxLoadMore} · {Math.min(40, filteredWorldRates.length - worldFxVisibleCount)}</button><span>{t.fxShowing} {Math.min(worldFxVisibleCount, filteredWorldRates.length)} / {filteredWorldRates.length}</span></div>}
                {Boolean(worldFx?.unsupported_quotes?.length) && <div className="stale-banner">{t.fxUnavailable} {worldFx?.unsupported_quotes.join(', ')}</div>}
                <div className="disclaimer"><Settings size={15} /><span>{t.fxWorldNotice}</span></div>
                <footer>MARKETPULSE <span>WORLD DAILY REFERENCE RATES · NOT REAL-TIME FOREX</span></footer>
              </>
            ) : (
              <>
                {fxError && <div className="error-banner"><span>{t.fxError}: {fxError}</span><button onClick={() => setFxError('')}>×</button></div>}
                {fx?.stale && <div className="stale-banner">{t.stale}</div>}
                <section className="fx-summary panel">
                  <div>
                    <span className="eyebrow">{t.rateDate}</span>
                    <h2>{fx ? formatRateDate(fx.rate_date, lang) : (fxBusy ? t.loading : '—')}</h2>
                    <p>{t.official}</p>
                  </div>
                  <div className="fx-source"><span className="source-label">● {t.source}</span><strong>Bank of Russia</strong><a href="https://www.cbr.ru/currency_base/daily/" target="_blank" rel="noreferrer">{t.cbrLink} ↗</a></div>
                </section>
                <section className="fx-grid" aria-live="polite">
                  {fx?.items.map(item => (
                    <article className="fx-card panel" key={item.base}>
                      <div className="fx-card-top"><span className="fx-currency-code">{item.base}</span><span className="fx-symbol">{item.symbol}</span></div>
                      <div className="fx-name">{item.name}</div>
                      <div className="fx-rate">₽ {formatRate(item.rate, lang)}</div>
                      <div className="fx-rate-caption">{t.rate}</div>
                      <div className="fx-card-foot"><span>{t.rateDate}</span><strong>{formatRateDate(item.rate_date, lang)}</strong></div>
                    </article>
                  ))}
                  {!fx?.items.length && <div className="empty panel">{fxBusy ? t.loading : (fxError || t.noFx)}</div>}
                </section>
                <div className="disclaimer"><Settings size={15} /><span>{t.fxNotice}</span></div>
                <footer>MARKETPULSE <span>OFFICIAL CBR REFERENCE DATA · NOT INVESTMENT ADVICE</span></footer>
              </>
            )}
          </>
        ) : page === 'portfolio' ? (
          <>
            <header className="topbar">
              <div>
                <div className="eyebrow">PORTFOLIO · MANUAL POSITIONS</div>
                <h1>{t.portfolioTitle}<span className="dot-live" /></h1>
                <p>{t.portfolioSubtitle}</p>
                <div className={`quote-freshness quote-${quoteStatus}`} role="status" aria-live="polite">
                  <span className="quote-status-dot" />
                  <strong>{quoteStatus === 'fresh' ? t.quoteFresh : quoteStatus === 'stale' ? t.quoteStale : t.quoteUnavailable}</strong>
                  {quoteAgeSeconds !== null && portfolioData?.items.length ? <span>· {t.quoteAge}: {quoteAgeSeconds} {t.quoteAgeSeconds} ({new Date(portfolioData.updated_at!).toLocaleTimeString(lang === 'ru' ? 'ru-RU' : 'en-US')})</span> : null}
                  <small>{t.quoteAutoRefresh}</small>
                </div>
              </div>
              <button className="refresh" onClick={() => void loadPortfolio()} disabled={portfolioBusy}>
                <RefreshCw size={16} className={portfolioBusy ? 'spin' : ''} />{portfolioBusy ? '…' : t.retry}
              </button>
            </header>
            {portfolioError && <div className="error-banner"><span>{t.portfolioLoadError}: {portfolioError}</span><button onClick={() => setPortfolioError('')}>×</button></div>}
            {portfolioFormError && <div className="error-banner"><span>{portfolioFormError}</span><button onClick={() => setPortfolioFormError('')}>×</button></div>}
            {portfolioData?.warnings.map((warning, index) => <div className="stale-banner" key={`${warning}-${index}`}>{warning}</div>)}
            <section className="portfolio-summary">
              {(portfolioData?.totals_by_quote_asset ?? []).map(total => (
                <article className="metric portfolio-total" key={total.quote_asset}>
                  <span>{t.portfolioValue} · {total.quote_asset}</span>
                  <strong>{formatAmount(total.market_value)} <em>{total.quote_asset}</em></strong>
                  <small>{t.portfolioTotals} · {total.priced_positions} / {(portfolioData?.items ?? []).filter(item => item.quote_asset === total.quote_asset).length}</small>
                  {(total.cost_basis !== null || total.unrealized_pnl !== null) && <div className="portfolio-total-details">
                    {total.cost_basis !== null && <span>{t.portfolioCost}: {formatAmount(total.cost_basis)} {total.quote_asset}</span>}
                    {total.unrealized_pnl !== null && <span className={Number(total.unrealized_pnl) >= 0 ? 'positive' : 'negative'}>{t.portfolioPnl}: {Number(total.unrealized_pnl) > 0 ? '+' : ''}{formatAmount(total.unrealized_pnl)} {total.quote_asset}</span>}
                  </div>}
                </article>
              ))}
              {!portfolioData?.items.length && !portfolioBusy && !portfolioError && <div className="empty panel portfolio-empty">{t.portfolioEmpty}</div>}
            </section>
            <section className="panel portfolio-list-panel">
              <div className="panel-head"><div><span className="eyebrow">POSITIONS</span><h2>{t.portfolio}</h2></div><span className="count">{portfolioData?.items.length ?? 0}</span></div>
              {portfolioBusy && !portfolioData ? <div className="empty">{t.loading}</div> : portfolioData?.items.length ? (
                <div className="portfolio-table-wrap">
                  <table className="portfolio-table">
                    <thead><tr><th>{t.portfolioPair}</th><th>{t.portfolioQuantity}</th><th>{t.portfolioEntry}</th><th>{t.portfolioCurrentPrice}</th><th>{t.portfolioValue}</th><th>{t.portfolioPnl}</th><th /></tr></thead>
                    <tbody>{portfolioData.items.map(item => (
                      <tr key={item.id}>
                        <td><strong>{item.symbol}</strong><small>{item.base_asset ?? item.symbol} / {item.quote_asset}</small></td>
                        <td>{formatAmount(item.quantity, 12)}</td>
                        <td>{item.average_entry_price === null ? '—' : `${formatAmount(item.average_entry_price)} ${item.quote_asset}`}</td>
                        <td>{item.current_price === null ? <span className="negative">{t.portfolioUnknownPrice}</span> : `${formatAmount(item.current_price)} ${item.quote_asset}`}</td>
                        <td>{item.market_value === null ? '—' : `${formatAmount(item.market_value)} ${item.quote_asset}`}</td>
                        <td>{item.unrealized_pnl === null ? '—' : <span className={Number(item.unrealized_pnl) >= 0 ? 'positive' : 'negative'}>{Number(item.unrealized_pnl) > 0 ? '+' : ''}{formatAmount(item.unrealized_pnl)} {item.quote_asset}<small>{item.unrealized_pnl_percent === null ? '' : `${Number(item.unrealized_pnl_percent) > 0 ? '+' : ''}${formatAmount(item.unrealized_pnl_percent, 2)}%`}</small></span>}</td>
                        <td><button className="portfolio-delete" title={t.portfolioDelete} aria-label={`${t.portfolioDelete}: ${item.symbol}`} onClick={() => void deletePortfolioPosition(item.id)}><Trash2 size={15} /></button></td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              ) : <div className="empty">{portfolioError ? t.portfolioLoadError : t.portfolioEmpty}</div>}
            </section>
            <section className="panel portfolio-add-panel">
              <div className="panel-head"><div><span className="eyebrow">NEW POSITION</span><h2>{t.portfolioAdd}</h2></div><Plus size={18} /></div>
              <form className="portfolio-form" onSubmit={addPortfolioPosition}>
                <label className="portfolio-asset-field">{t.portfolioPair}
                  <div className={`portfolio-asset-picker ${positionPickerOpen ? 'is-open' : ''}`}>
                    <div className="portfolio-asset-input-wrap">
                      <Search size={16} aria-hidden="true" />
                      <input
                        value={positionSearch}
                        onFocus={() => setPositionPickerOpen(true)}
                        onBlur={() => window.setTimeout(() => setPositionPickerOpen(false), 120)}
                        onChange={event => { setPositionSearch(event.target.value); setPositionSymbol(''); setPositionPickerOpen(true); setPortfolioFormError(''); }}
                        onKeyDown={event => {
                          if (event.key === 'Escape') setPositionPickerOpen(false);
                          if (event.key === 'Enter' && positionPickerOpen && portfolioSuggestions.length) {
                            event.preventDefault();
                            choosePortfolioAsset(portfolioSuggestions[0].symbol);
                          }
                        }}
                        placeholder={t.portfolioPairHint}
                        autoComplete="off"
                        role="combobox"
                        aria-expanded={positionPickerOpen}
                        aria-controls="portfolio-asset-options"
                        aria-autocomplete="list"
                        required={!positionSymbol}
                      />
                      <button className="portfolio-picker-toggle" type="button" aria-label={t.portfolioPair} onMouseDown={event => event.preventDefault()} onClick={() => setPositionPickerOpen(open => !open)}><ChevronDown size={15} /></button>
                    </div>
                    {positionPickerOpen && <div className="portfolio-asset-dropdown" id="portfolio-asset-options" role="listbox">
                      <div className="portfolio-dropdown-heading">{positionSearch.trim() ? (lang === 'ru' ? 'РЕЗУЛЬТАТЫ ПОИСКА' : 'SEARCH RESULTS') : t.portfolioPopular}</div>
                      {marketDataError && <div className="portfolio-picker-empty portfolio-picker-error"><span>{t.portfolioMarketError}</span><small>{marketDataError}</small><button type="button" onMouseDown={event => event.preventDefault()} onClick={() => void load()} disabled={busy}>{busy ? '…' : t.retry}</button></div>}
                      {!tickers.length ? (marketDataError ? <div className="portfolio-picker-empty">{t.portfolioNoMatches}</div> : <div className="portfolio-picker-empty">{t.portfolioSearchLoading}</div>) : portfolioSuggestions.length ? portfolioSuggestions.map(item => {
                        const pair = splitTradingPair(item.symbol);
                        const exists = (portfolioData?.items ?? []).some(position => position.symbol === item.symbol);
                        return <button key={item.symbol} type="button" className={`portfolio-asset-option ${positionSymbol === item.symbol ? 'is-selected' : ''}`} role="option" aria-selected={positionSymbol === item.symbol} disabled={exists} onMouseDown={event => event.preventDefault()} onClick={() => choosePortfolioAsset(item.symbol)}>
                          <span className="portfolio-coin-mark">{pair.base.slice(0, 1)}</span>
                          <span className="portfolio-asset-identity"><strong>{coinName(pair.base, lang)}</strong><small>{pair.base} · {item.symbol}</small></span>
                          <span className="portfolio-asset-quote"><strong>{formatAmount(item.price, 8)}</strong><small className={Number(item.change_percent) >= 0 ? 'positive' : 'negative'}>{Number(item.change_percent) > 0 ? '+' : ''}{formatAmount(item.change_percent, 2)}%</small></span>
                          {exists ? <span className="portfolio-already-added">{lang === 'ru' ? 'Добавлена' : 'Added'}</span> : positionSymbol === item.symbol ? <Check size={16} className="portfolio-option-check" /> : null}
                        </button>;
                      }) : <div className="portfolio-picker-empty">{t.portfolioNoMatches}</div>}
                      <div className="portfolio-dropdown-foot">{lang === 'ru' ? 'Данные рынка · Binance Spot' : 'Market data · Binance Spot'}</div>
                    </div>}
                  </div>
                  <small>{positionSymbol ? `${t.portfolioPairCaption}: ${positionSymbol}` : t.portfolioSearchHint}</small>
                </label>
                <label>{t.portfolioQuantity}<input type="number" inputMode="decimal" min="0.000000000001" step="any" value={positionQuantity} onChange={event => setPositionQuantity(event.target.value)} placeholder="0.25" required /></label>
                <label>{t.portfolioEntry}<input type="number" inputMode="decimal" min="0.000000000001" step="any" value={positionEntryPrice} onChange={event => setPositionEntryPrice(event.target.value)} placeholder="65000" /><small>{t.portfolioEntryHint}</small></label>
                <button className="portfolio-submit" type="submit" disabled={portfolioBusy || !positionSymbol}><Plus size={16} />{t.portfolioSave}</button>
              </form>
            </section>
            <div className="disclaimer"><Settings size={15} /><span>{t.portfolioInfo}</span></div>
            <footer>MARKETPULSE <span>PORTFOLIO VALUATION · BINANCE SPOT</span></footer>
          </>
        ) : (
          <>
            <header className="topbar">
              <div><div className="eyebrow">{t.live}</div><h1>{t.terminal}<span className="dot-live" /></h1><p>{t.subtitle}</p></div>
              <button className="refresh" onClick={() => void load()} disabled={busy}><RefreshCw size={16} className={busy ? 'spin' : ''} />{busy ? '…' : t.retry}</button>
            </header>
            {error && <div className="error-banner"><span>{error}</span><button onClick={() => setError('')}>×</button></div>}
            <div className="metrics">
              <div className="metric"><span>TRACKED ASSETS</span><strong>{tickers.length.toLocaleString()}</strong><small>Binance Spot · API</small></div>
              <div className="metric"><span>SELECTED PAIR</span><strong>{selected.replace('USDT', '')}<em>/ USDT</em></strong><small>{current ? `${t.price} · ${Number(current.price).toLocaleString(undefined, { maximumFractionDigits: 6 })}` : t.loading}</small></div>
              <div className="metric"><span>DATA STATUS</span><strong className={error ? 'negative' : 'positive'}>{error ? 'DEGRADED' : 'CONNECTED'}</strong><small>{error || 'Latest API response received'}</small></div>
            </div>
            <div className="content-grid">
              <section className="panel chart-panel">
                <div className="panel-head"><div><span className="eyebrow">MARKET OVERVIEW</span><h2>{selected.replace('USDT', '')} <span className="pair">/ USDT</span></h2></div><div className="price-block"><strong>{current ? Number(current.price).toLocaleString(undefined, { maximumFractionDigits: 8 }) : '—'}</strong><span className={current && Number(current.change_percent) >= 0 ? 'positive' : 'negative'}>{current ? `${Number(current.change_percent) > 0 ? '+' : ''}${Number(current.change_percent).toFixed(2)}%` : ''}</span></div></div>
                <div className="chart-tools"><span>{t.chart} · 1H</span><span className="source-label">● {t.source}: Binance</span></div>
                {candles.length ? <Chart candles={candles} dark={dark} /> : <div className="chart-empty">{busy ? t.loading : chartError || error || t.noData}</div>}
                <div className="chart-foot"><span>● {t.source}: Binance Spot</span><span>{candles.length ? new Date(candles[candles.length - 1].time * 1000).toLocaleString() : ''}</span></div>
              </section>
              <section className="panel watch-panel" id="markets">
                <div className="panel-head"><div><span className="eyebrow">DISCOVER</span><h2>{t.markets}</h2></div><span className="count">{filtered.length}</span></div>
                <label className="search"><Search size={16} /><input placeholder={t.search} value={search} onChange={event => setSearch(event.target.value)} /></label>
                <div className="table-head"><span>ASSET</span><span>{t.price}</span><span>{t.change}</span><span /></div>
                <div className="market-list">
                  {filtered.map(item => <div key={item.symbol} className={`market-row ${selected === item.symbol ? 'selected' : ''}`}>
                    <button className="asset" onClick={() => setSelected(item.symbol)}><span className="coin">{item.symbol.slice(0, 1)}</span><span><b>{item.symbol.replace('USDT', '')}</b><small>{item.symbol}</small></span></button>
                    <button className="market-price" onClick={() => setSelected(item.symbol)}>{Number(item.price).toLocaleString(undefined, { maximumFractionDigits: 6 })}</button>
                    <span className={Number(item.change_percent) >= 0 ? 'positive' : 'negative'}>{Number(item.change_percent) > 0 ? '+' : ''}{Number(item.change_percent).toFixed(2)}%</span>
                    <button className={`fav ${favorites.includes(item.symbol) ? 'on' : ''}`} title={favorites.includes(item.symbol) ? t.remove : t.add} onClick={() => void toggle(item.symbol)}><Star size={15} fill={favorites.includes(item.symbol) ? 'currentColor' : 'none'} /></button>
                  </div>)}
                  {!filtered.length && !error && <div className="empty">{busy ? t.loading : t.noData}</div>}
                  {error && !tickers.length && <div className="empty"><p>{t.error}</p><button onClick={() => void load()}>{t.retry}</button></div>}
                </div>
              </section>
            </div>
            <div className="disclaimer"><Settings size={15} /><span>{t.notice}</span></div>
            <footer>MARKETPULSE <span>v0.4.6 · NOT INVESTMENT ADVICE</span></footer>
          </>
        )}
      </section>
      {converterPicker && createPortal(
        <div className={`currency-picker-backdrop ${dark ? 'is-dark' : 'is-light'}`} onMouseDown={(event) => { if (event.target === event.currentTarget) setConverterPicker(null); }}>
          <section className="currency-picker-dialog" role="dialog" aria-modal="true" aria-labelledby="currency-picker-title">
            <header className="currency-picker-header">
              <div>
                <span className="eyebrow">MARKETPULSE · FX</span>
                <h2 id="currency-picker-title">{t.converterChooseCurrency}</h2>
                <p>{converterPicker === 'from' ? t.converterFrom : t.converterTo}</p>
              </div>
              <button className="currency-picker-close" type="button" aria-label={t.converterClosePicker} onClick={() => setConverterPicker(null)}><X size={22} /></button>
            </header>
            <label className="currency-picker-search">
              <Search size={19} aria-hidden="true" />
              <input autoFocus type="search" value={converterCurrencySearch} onChange={event => setConverterCurrencySearch(event.target.value)} placeholder={t.converterSearchCurrency} aria-label={t.converterSearchCurrency} />
            </label>
            <div className="currency-picker-list-heading">{lang === 'ru' ? `ВАЛЮТЫ · ${converterPickerResults.length}` : `CURRENCIES · ${converterPickerResults.length}`}</div>
            <div className="currency-picker-list" role="listbox" aria-label={t.converterChooseCurrency}>
              {converterPickerResults.map(currency => {
                const selectedCode = converterPicker === 'from' ? converterFrom : converterTo;
                const selectedCurrency = selectedCode === currency.code;
                return <button key={currency.code} type="button" role="option" aria-selected={selectedCurrency} className={`currency-picker-option ${selectedCurrency ? 'is-selected' : ''}`} onClick={() => chooseConverterCurrency(currency.code)}>
                  <span className="currency-picker-option-code">{currency.code}</span>
                  <span className="currency-picker-option-name"><strong>{currency.name}</strong><small>{currency.symbol ? `${lang === 'ru' ? 'Символ' : 'Symbol'}: ${currency.symbol}` : (lang === 'ru' ? 'Символ не указан' : 'No symbol listed')}</small></span>
                  {selectedCurrency && <Check size={21} className="currency-picker-selected-check" aria-hidden="true" />}
                </button>;
              })}
              {!converterPickerResults.length && <div className="currency-picker-empty">{t.converterNoCurrencies}</div>}
            </div>
            <footer className="currency-picker-footer">{lang === 'ru' ? 'Нажми на строку валюты для выбора · Esc — закрыть' : 'Tap a currency to select · Esc to close'}</footer>
          </section>
        </div>,
        document.body,
      )}
    </main>
  );
}
