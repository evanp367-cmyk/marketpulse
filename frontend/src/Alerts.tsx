import { useEffect, useState, type FormEvent } from 'react';
import { Bell, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { api } from './api';

type Rule = {
  id: number; name: string; symbol: string; enabled: boolean; cooldown_seconds: number;
  condition: { type: string; direction: string; threshold: string };
  last_triggered_at: string | null;
};
type Event = { id: number; symbol: string; price: string; status: string; created_at: string };
type Props = { lang: 'ru' | 'en'; selectedSymbol: string };

export default function Alerts({ lang, selectedSymbol }: Props) {
  const ru = lang === 'ru';
  const [rules, setRules] = useState<Rule[]>([]);
  const [evaluationEnabled, setEvaluationEnabled] = useState(false);
  const [history, setHistory] = useState<Event[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState<number | null>(null);
  const [name, setName] = useState('');
  const [symbol, setSymbol] = useState(selectedSymbol);
  const [direction, setDirection] = useState<'above' | 'below'>('above');
  const [threshold, setThreshold] = useState('');
  const [cooldown, setCooldown] = useState(900);

  async function reload() {
    setError('');
    try {
      const [r, h] = await Promise.all([
        api<{ items: Rule[]; evaluation_enabled: boolean }>('/api/alerts'),
        api<{ items: Event[] }>('/api/alerts/history'),
      ]);
      setRules(r.items); setEvaluationEnabled(r.evaluation_enabled); setHistory(h.items);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }
  useEffect(() => { void reload(); }, []);

  function reset() {
    setEditing(null); setName(''); setSymbol(selectedSymbol); setDirection('above');
    setThreshold(''); setCooldown(900);
  }
  function edit(rule: Rule) {
    setEditing(rule.id); setName(rule.name); setSymbol(rule.symbol);
    setDirection(rule.condition.direction === 'below' ? 'below' : 'above');
    setThreshold(String(rule.condition?.threshold ?? '')); setCooldown(rule.cooldown_seconds);
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const body = { name: name.trim(), symbol: symbol.trim().toUpperCase(),
        condition: { type: 'price', direction, threshold }, cooldown_seconds: cooldown };
      if (editing === null) await api('/api/alerts', { method: 'POST', body: JSON.stringify(body) });
      else await api(`/api/alerts/${editing}`, { method: 'PUT', body: JSON.stringify({ ...body, enabled: rules.find(x => x.id === editing)?.enabled ?? true }) });
      reset(); await reload();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  async function toggle(rule: Rule) {
    setBusy(true); setError('');
    try {
      await api(`/api/alerts/${rule.id}`, { method: 'PATCH', body: JSON.stringify({ enabled: !rule.enabled }) });
      await reload();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  async function remove(rule: Rule) {
    if (!window.confirm(ru ? `Удалить правило «${rule.name}»?` : `Delete rule “${rule.name}”?`)) return;
    setBusy(true); setError('');
    try { await api(`/api/alerts/${rule.id}`, { method: 'DELETE' }); await reload(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  return <section className="panel alert-panel">
    <div className="panel-head"><div><span className="eyebrow">TELEGRAM · PRICE ALERTS</span>
      <h2>{ru ? 'Уведомления о цене' : 'Price alerts'}</h2>
      <p>{ru ? 'Сообщение придёт при пересечении порога. После возврата цены правило снова готово.' : 'A message arrives when the price crosses your threshold. The rule rearms after price returns.'}</p>
    </div><button className="refresh" onClick={() => void reload()} disabled={busy}><RefreshCw size={15}/>{ru ? 'Обновить' : 'Refresh'}</button></div>
    {error && <div className="error-banner">{error}</div>}
    {!evaluationEnabled && <div className="error-banner">{ru ? 'Уведомления ещё не включены на сервере. Правила можно сохранить, но сообщения пока не отправляются.' : 'Notifications are not yet enabled on the server. Rules can be saved, but messages are not sent yet.'}</div>}
    <form className="alert-form" onSubmit={e => void save(e)}>
      <label>{ru ? 'Название' : 'Name'}<input value={name} onChange={e => setName(e.target.value)} required maxLength={120} placeholder={ru ? 'Например, BTC выше 100 000' : 'For example, BTC above 100,000'} /></label>
      <label>{ru ? 'Пара Binance Spot' : 'Binance Spot pair'}<input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} required pattern="[A-Za-z0-9]{5,30}" maxLength={30} /></label>
      <label>{ru ? 'Условие' : 'Condition'}<select value={direction} onChange={e => setDirection(e.target.value as 'above' | 'below')}><option value="above">{ru ? 'Цена ≥' : 'Price ≥'}</option><option value="below">{ru ? 'Цена ≤' : 'Price ≤'}</option></select></label>
      <label>{ru ? 'Порог' : 'Threshold'}<input value={threshold} onChange={e => setThreshold(e.target.value)} required inputMode="decimal" type="number" min="0.000000000001" step="any" placeholder="100000" /></label>
      <label>{ru ? 'Пауза между срабатываниями' : 'Cooldown'}<select value={cooldown} onChange={e => setCooldown(Number(e.target.value))}><option value={900}>15 {ru ? 'минут' : 'minutes'}</option><option value={3600}>1 {ru ? 'час' : 'hour'}</option><option value={86400}>24 {ru ? 'часа' : 'hours'}</option></select></label>
      <div className="alert-actions"><button className="refresh" disabled={busy} type="submit"><Plus size={15}/>{editing === null ? (ru ? 'Добавить' : 'Add alert') : (ru ? 'Сохранить' : 'Save')}</button>{editing !== null && <button type="button" className="refresh" onClick={reset}>{ru ? 'Отмена' : 'Cancel'}</button>}</div>
    </form>
    <p className="alert-note">{ru ? 'Бесплатно: до 2 правил; Pro: до 20. Проверка примерно раз в 30 секунд при доступности Binance. Бот должен быть открыт через /start, чтобы получать сообщения.' : 'Free: up to 2 rules; Pro: up to 20. Checks run about every 30 seconds when Binance is available. Open the bot with /start to receive messages.'}</p>
    <div className="alert-list">{rules.map(rule => <div className="alert-row" key={rule.id}>
      <div><strong>{rule.name}</strong><small>{rule.symbol} · {rule.condition?.type === 'price' ? `${rule.condition.direction === 'below' ? '≤' : '≥'} ${rule.condition.threshold}` : (ru ? 'Устаревшее условие — измените правило' : 'Legacy condition — edit the rule')} · {rule.enabled ? (ru ? 'Включено' : 'On') : (ru ? 'Выключено' : 'Off')}</small></div>
      <div className="alert-actions"><button className="refresh" disabled={busy} onClick={() => void toggle(rule)}>{rule.enabled ? (ru ? 'Выключить' : 'Disable') : (ru ? 'Включить' : 'Enable')}</button><button className="refresh" disabled={busy} onClick={() => edit(rule)}>{ru ? 'Изменить' : 'Edit'}</button><button className="refresh" disabled={busy} onClick={() => void remove(rule)} aria-label={ru ? 'Удалить' : 'Delete'}><Trash2 size={14}/></button></div>
    </div>)}{rules.length === 0 && <p>{ru ? 'Правил пока нет.' : 'No rules yet.'}</p>}</div>
    <div className="alert-history"><h3><Bell size={16}/>{ru ? 'История уведомлений' : 'Notification history'}</h3>
      {history.map(item => <div className="alert-row" key={item.id}><span>{item.symbol} · {item.price}</span><small>{new Date(item.created_at).toLocaleString()} · {item.status === 'delivered' ? (ru ? 'Доставлено' : 'Delivered') : item.status === 'failed' ? (ru ? 'Не доставлено' : 'Failed') : item.status === 'pending' ? (ru ? 'Ожидает' : 'Pending') : (ru ? 'Отменено' : 'Cancelled')}</small></div>)}
      {history.length === 0 && <p>{ru ? 'Срабатываний пока нет.' : 'No triggers yet.'}</p>}
    </div>
  </section>;
}
