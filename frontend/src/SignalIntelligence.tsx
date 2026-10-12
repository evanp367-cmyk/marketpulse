import { useEffect, useState } from 'react';
import { ArrowDownRight, ArrowUpRight, Bell, BellOff, ChartCandlestick, Clock3, ExternalLink, History, Star } from 'lucide-react';
import { api } from './api';
import './signal-intelligence.css';

type Lang = 'ru' | 'en';
type SignalEvent = {
  key: string; type: 'price_surge' | 'price_drop' | 'volume_anomaly'; symbol: string; interval: string;
  source: string; detected_at: string; price: number; change_percent: number; direction: 'up' | 'down' | 'flat';
  high: number; low: number; quote_volume: number; quote_asset: string | null; volume_ratio: number;
  baseline_candles: number; duration_seconds: number; age_seconds: number; strength: number;
  strength_components: { momentum: number; volume: number; range: number; freshness: number };
  reason_codes: string[]; warnings: string[];
};
type Subscription = { id: number; enabled: boolean; symbol: string; interval: string; cooldown_seconds: number };
type Response = { source: string; symbol: string; interval: string; computed_at: string; latest_closed_at: string | null;
  current: SignalEvent | null; history: SignalEvent[]; subscription: Subscription | null; delivery_enabled: boolean;
  rules: { price_change_percent: number; price_event_min_volume_ratio: number; volume_anomaly_ratio: number; volume_baseline_candles: number; strength_formula: string } };

const titles = {
  price_surge: { ru: 'Резкий рост', en: 'Price surge' },
  price_drop: { ru: 'Резкое снижение', en: 'Price drop' },
  volume_anomaly: { ru: 'Аномальный объём', en: 'Volume anomaly' },
};
function exchangeUrl(symbol: string) {
  const quote = ['USDT', 'USDC', 'FDUSD', 'BTC', 'ETH', 'BNB', 'EUR', 'TRY', 'BRL'].find(item => symbol.endsWith(item));
  return quote ? `https://www.binance.com/en/trade/${symbol.slice(0, -quote.length)}_${quote}?type=spot` : null;
}
function amount(value: number, lang: Lang, digits = 8) {
  return new Intl.NumberFormat(lang === 'ru' ? 'ru-RU' : 'en-US', { maximumSignificantDigits: digits }).format(value);
}
function date(value: string, lang: Lang) {
  return new Date(value).toLocaleString(lang === 'ru' ? 'ru-RU' : 'en-US', { dateStyle: 'short', timeStyle: 'short', timeZone: 'UTC' }) + ' UTC';
}

export default function SignalIntelligence({ symbol, interval, lang, favorite, onChart, onFavorite, onAlert }: {
  symbol: string; interval: string; lang: Lang; favorite: boolean;
  onChart: () => void; onFavorite: () => void; onAlert: () => void;
}) {
  const ru = lang === 'ru';
  const [data, setData] = useState<Response | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [revision, setRevision] = useState(0);
  const [showHistory, setShowHistory] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setBusy(true); setError('');
    void api<Response>(`/api/signals/movements?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}`, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) setData(result); })
      .catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : String(reason)); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [symbol, interval, revision]);

  async function toggleSubscription() {
    if (!data || saving) return;
    setSaving(true); setError('');
    try {
      if (data.subscription?.enabled) {
        await api(`/api/signals/subscriptions/${data.subscription.id}`, { method: 'DELETE' });
        setData({ ...data, subscription: { ...data.subscription, enabled: false } });
      } else {
        const subscription = await api<Subscription>('/api/signals/subscriptions', {
          method: 'POST', body: JSON.stringify({ symbol, interval }),
        });
        setData({ ...data, subscription });
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally { setSaving(false); }
  }

  const matching = data?.symbol === symbol && data?.interval === interval ? data : null;
  const event = matching?.current;
  const marketUrl = exchangeUrl(symbol);
  const reasons = event?.reason_codes.map(code => code === 'price_change_at_least_3pct'
    ? (ru ? 'Закрытая свеча изменила цену минимум на 3%.' : 'The closed candle moved at least 3%.')
    : code === 'volume_at_least_1_5x'
      ? (ru ? 'Объём выше медианы 20 предыдущих свечей минимум в 1,5 раза.' : 'Volume is at least 1.5× the median of the prior 20 candles.')
      : (ru ? 'Объём выше медианы 20 предыдущих свечей минимум в 3 раза.' : 'Volume is at least 3× the median of the prior 20 candles.'));

  return <section className="signal-intelligence" aria-label="MarketPulse Signal Intelligence">
    <header className="signal-intelligence-head"><div><span className="eyebrow">MARKETPULSE / SIGNAL INTELLIGENCE</span><h2>{ru ? 'Движения рынка' : 'Market movements'}</h2><p>{ru ? 'События только по закрытым свечам Binance Spot. Данные других бирж не смешиваются.' : 'Events from closed Binance Spot candles only. No cross-exchange prices.'}</p></div><button className="refresh" onClick={() => setRevision(value => value + 1)} disabled={busy}>{ru ? 'Обновить события' : 'Refresh events'}</button></header>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {busy && !matching && <div className="panel signal-intelligence-empty" role="status">{ru ? 'Проверяем закрытые свечи…' : 'Checking closed candles…'}</div>}
    {matching && <>
      {event ? <article className="panel signal-event-card">
        <header className="signal-event-header"><div className="signal-event-asset">{symbol.slice(0, 2)}</div><div><span className="eyebrow">{event.source}</span><h3>{symbol.replace(/(USDT|USDC|FDUSD|BTC|ETH|BNB|EUR|TRY|BRL)$/, ' / $1')}</h3><span>{titles[event.type][lang]} · {date(event.detected_at, lang)}</span></div></header>
        <div className="signal-event-main"><div><span>{ru ? 'Цена закрытия подтверждённой свечи' : 'Confirmed candle close'}</span><strong>{amount(event.price, lang, 10)}</strong></div><div className={event.direction === 'down' ? 'negative' : 'positive'}>{event.direction === 'down' ? <ArrowDownRight size={23}/> : <ArrowUpRight size={23}/>}<strong>{event.change_percent > 0 ? '+' : ''}{amount(event.change_percent, lang, 5)}%</strong><small>{ru ? 'за выбранное окно' : 'over selected window'}</small></div></div>
        <div className="signal-event-facts"><div><span>High / Low</span><strong>{amount(event.high, lang)} / {amount(event.low, lang)}</strong></div><div><span>{ru ? 'Объём свечи' : 'Candle volume'}</span><strong>{amount(event.quote_volume, lang)} {event.quote_asset ?? (ru ? 'котируемой валюты' : 'quote units')}</strong></div><div><span>{ru ? 'К медиане объёма' : 'Vs median volume'}</span><strong>{amount(event.volume_ratio, lang, 4)}×</strong></div><div><span>{ru ? 'Длительность' : 'Duration'}</span><strong>{event.interval}</strong></div></div>
        <div className="signal-event-explanation"><div><h4>{ru ? 'Почему появился сигнал' : 'Why this event appeared'}</h4><ul>{reasons?.map(reason => <li key={reason}>{reason}</li>)}</ul></div><div><h4>{ru ? 'Сила движения' : 'Movement strength'} · {event.strength}/100</h4><p>{ru ? 'Оценка по формуле, не вероятность прибыли:' : 'Formula score, not a profit probability:'} {event.strength_components.momentum} {ru ? 'цена' : 'price'} + {event.strength_components.volume} {ru ? 'объём' : 'volume'} + {event.strength_components.range} {ru ? 'диапазон' : 'range'} + {event.strength_components.freshness} {ru ? 'свежесть' : 'freshness'}.</p>{event.warnings.includes('wide_candle_range') && <p className="signal-event-warning">{ru ? 'Широкий диапазон свечи: повышенная волатильность.' : 'Wide candle range: elevated volatility.'}</p>}{event.warnings.includes('stale_closed_candle') && <p className="signal-event-warning">{ru ? 'Данные устарели. Обновите событие перед принятием решений.' : 'Data is stale. Refresh before using this event.'}</p>}</div></div>
        <div className="signal-event-actions"><button onClick={onChart}><ChartCandlestick size={17}/>{ru ? 'График' : 'Chart'}</button><button onClick={onFavorite}><Star size={17}/>{favorite ? (ru ? 'В избранном' : 'Saved') : (ru ? 'В избранное' : 'Watchlist')}</button><button onClick={onAlert}><Bell size={17}/>{ru ? 'Ценовой алерт' : 'Price alert'}</button>{marketUrl && <a href={marketUrl} target="_blank" rel="noreferrer"><ExternalLink size={17}/>Binance Spot</a>}</div>
      </article> : <div className="panel signal-intelligence-empty"><Clock3 size={22}/><strong>{ru ? 'Нового события на последней закрытой свече нет' : 'No event on the latest closed candle'}</strong><span>{ru ? 'Это не означает, что рынок не движется. Ниже доступна история по этой паре.' : 'This does not mean the market is still. Recent events are available below.'}</span></div>}
      <div className="signal-intelligence-tools"><button className="refresh" onClick={() => void toggleSubscription()} disabled={saving}>{matching.subscription?.enabled ? <BellOff size={17}/> : <Bell size={17}/>} {matching.subscription?.enabled ? (ru ? 'Отключить сообщения' : 'Mute events') : (ru ? 'Получать события в Telegram' : 'Get Telegram events')}</button><button className="refresh" onClick={() => setShowHistory(value => !value)} aria-expanded={showHistory}><History size={17}/>{ru ? 'История похожих событий' : 'Similar event history'} · {matching.history.length}</button></div>
      {!matching.delivery_enabled && <p className="signal-delivery-note">{ru ? 'Отправка сигналов на сервере пока выключена. Подписку можно сохранить заранее; сообщения начнут приходить после включения доставки.' : 'Signal delivery is disabled on the server. You can save a subscription now; messages will start after delivery is enabled.'}</p>}
      {showHistory && <div className="panel signal-event-history">{matching.history.length ? matching.history.map(item => <div key={item.key}><strong>{titles[item.type][lang]}</strong><span>{item.change_percent > 0 ? '+' : ''}{amount(item.change_percent, lang, 5)}% · {amount(item.price, lang)} · {date(item.detected_at, lang)}</span></div>) : <p>{ru ? 'За последние свечи пороги событий не сработали.' : 'No events crossed the thresholds in the recent candles.'}</p>}</div>}
      <p className="signal-method-note">{ru ? 'Рост/падение: не менее ±3% за свечу и объём ≥1,5× медианы 20 предыдущих свечей. Аномальный объём: ≥3× медианы. Источник: Binance Spot klines. Причины движения и ликвидность без дополнительных данных неизвестны. Технические индикаторы для этой пары — ниже. Это описание прошлого движения, а не прогноз.' : 'Price event: at least ±3% per candle and volume ≥1.5× the median of the prior 20 candles. Volume anomaly: ≥3× median. Source: Binance Spot klines. The cause and liquidity are unknown without additional data. Technical indicators for this pair appear below. This describes past movement, not a forecast.'}</p>
    </>}
  </section>;
}
