import { useEffect, useRef } from 'react';
import { Activity, ArrowLeftRight, Bell, ChartCandlestick, ChevronRight, LayoutGrid, ListFilter, Moon, Newspaper, Star, Sun, Wallet, X, Globe } from 'lucide-react';

export type Page = 'terminal' | 'markets' | 'currencies' | 'portfolio' | 'signals' | 'alerts' | 'news' | 'plans';
type Props = {
  page: Page; lang: 'ru' | 'en'; dark: boolean; unreadCount: number; open: boolean; onOpenChange: (open: boolean) => void;
  onNavigate: (page: Page) => void; onMarkets: (favorites: boolean) => void;
  onTheme: () => void; onLanguage: () => void;
};

export default function Navigation({ page, lang, dark, unreadCount, open, onOpenChange, onNavigate, onMarkets, onTheme, onLanguage }: Props) {
  const ru = lang === 'ru';
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const items = [
    { id: 'terminal' as Page, label: ru ? 'Главная' : 'Home', icon: ChartCandlestick },
    { id: 'markets' as Page, label: ru ? 'Рынки' : 'Markets', icon: ListFilter },
    { id: 'signals' as Page, label: ru ? 'Сигналы' : 'Signals', icon: Activity },
    { id: 'portfolio' as Page, label: ru ? 'Портфель' : 'Portfolio', icon: Wallet },
    { id: 'alerts' as Page, label: ru ? 'Уведомления' : 'Alerts', icon: Bell },
    { id: 'currencies' as Page, label: ru ? 'Валюты' : 'Currencies', icon: ArrowLeftRight },
    { id: 'news' as Page, label: ru ? 'Новости' : 'News', icon: Newspaper },
    { id: 'plans' as Page, label: ru ? 'Подписка' : 'Membership', icon: Star },
  ];
  const primary = items.filter(item => ['terminal', 'markets', 'signals', 'portfolio'].includes(item.id));
  const secondary = items.filter(item => !primary.includes(item) && item.id !== 'alerts');
  useEffect(() => {
    if (!open) return;
    dialog.current?.showModal();
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { dialog.current?.close(); document.body.style.overflow = previous; };
  }, [open]);
  useEffect(() => { if (open) onOpenChange(false); }, [page]);
  function close() { onOpenChange(false); trigger.current?.focus(); }
  function navigate(next: Page) { close(); onNavigate(next); }

  const preferences = <div className="nav-preferences">
    <button onClick={onTheme} aria-label={ru ? 'Переключить тему' : 'Switch theme'}>{dark ? <Sun size={19}/> : <Moon size={19}/>}<span>{ru ? (dark ? 'Светлая тема' : 'Тёмная тема') : (dark ? 'Light theme' : 'Dark theme')}</span></button>
    <button onClick={onLanguage} aria-label={ru ? 'Переключить язык' : 'Switch language'}><Globe size={19}/><span>{ru ? 'Русский · RU' : 'English · EN'}</span></button>
  </div>;

  return <>
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Activity size={23}/></div><span>Market<span className="brand-accent">Pulse</span><small>{ru ? 'Ваш взгляд на рынок' : 'Your view of the market'}</small></span></div>
      <span className="navigation-caption">{ru ? 'ПРОСТРАНСТВО' : 'WORKSPACE'}</span>
      <nav className="desktop-navigation" aria-label={ru ? 'Основные разделы' : 'Main navigation'}>
        {items.map(({ id, label, icon: Icon }) => <button key={id} className={`nav ${page === id ? 'active' : ''}`} aria-current={page === id ? 'page' : undefined} onClick={() => onNavigate(id)}><Icon size={20}/><span>{label}</span>{id === 'alerts' && unreadCount > 0 ? <span className="nav-unread-count">{unreadCount > 99 ? '99+' : unreadCount}</span> : page === id && <span className="nav-active-dot"/>}</button>)}
        <button className="nav" onClick={() => onMarkets(true)}><Star size={20}/><span>{ru ? 'Избранное' : 'Watchlist'}</span></button>
      </nav>
      <div className="side-bottom">{preferences}<div className="chart-credit">MarketPulse · Binance Spot<br/>Charts by TradingView · Apache 2.0</div></div>
      <div className="mobile-actions">
        <button className={`mobile-alert-shortcut ${page === 'alerts' ? 'active' : ''}`} onClick={() => onNavigate('alerts')} aria-label={ru ? `Уведомления${unreadCount ? `: ${unreadCount} новых` : ''}` : `Alerts${unreadCount ? `: ${unreadCount} new` : ''}`} aria-current={page === 'alerts' ? 'page' : undefined}><Bell size={21}/>{unreadCount > 0 && <span className="alert-unread-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>}</button>
        <button className="mobile-theme" onClick={onTheme} aria-label={ru ? 'Переключить тему' : 'Switch theme'}>{dark ? <Sun size={20}/> : <Moon size={20}/>}</button>
      </div>
    </aside>
    <nav className="mobile-dock" aria-label={ru ? 'Основные разделы' : 'Main navigation'}>
      {primary.map(({ id, label, icon: Icon }) => <button key={id} aria-label={label} className={page === id ? 'active' : ''} aria-current={page === id ? 'page' : undefined} onClick={() => onNavigate(id)}><Icon size={21}/><span>{label}</span></button>)}
      <button ref={trigger} className={secondary.some(item => item.id === page) ? 'active' : ''} onClick={() => onOpenChange(true)} aria-haspopup="dialog" aria-expanded={open}><LayoutGrid size={21}/><span>{ru ? 'Ещё' : 'More'}</span></button>
    </nav>
    <dialog ref={dialog} className={`navigation-sheet ${dark ? 'is-dark' : 'is-light'}`} onCancel={close} onClose={() => onOpenChange(false)} onClick={event => { if (event.target === event.currentTarget) close(); }} aria-labelledby="navigation-title">
      <div className="sheet-body"><header><div><span className="eyebrow">MARKETPULSE</span><h2 id="navigation-title">{ru ? 'Все инструменты' : 'All tools'}</h2></div><button className="icon-button" aria-label={ru ? 'Закрыть меню' : 'Close menu'} onClick={close}><X size={22}/></button></header>
        <nav>{secondary.map(({ id, label, icon: Icon }) => <button key={id} onClick={() => navigate(id)}><Icon size={22}/><span>{label}</span><ChevronRight size={17}/></button>)}<button onClick={() => { close(); onMarkets(true); }}><Star size={22}/><span>{ru ? 'Избранное' : 'Watchlist'}</span><ChevronRight size={17}/></button></nav>
        <div className="sheet-settings"><span className="eyebrow">{ru ? 'НАСТРОЙКИ' : 'SETTINGS'}</span>{preferences}</div>
      </div>
    </dialog>
  </>;
}
