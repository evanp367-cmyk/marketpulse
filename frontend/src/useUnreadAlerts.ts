import { useCallback, useEffect, useState } from 'react';
import { api } from './api';

type AlertEvent = { id: number };

function storageKey() {
  const userId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
  return `marketpulse-alerts-seen-${userId ?? 'local'}`;
}

function lastSeen() {
  try {
    const value = Number(localStorage.getItem(storageKey()) || 0);
    return Number.isFinite(value) ? value : 0;
  }
  catch { return 0; }
}

export default function useUnreadAlerts(active: boolean) {
  const [unreadCount, setUnreadCount] = useState(0);

  const markSeen = useCallback((events: AlertEvent[]) => {
    const latest = Math.max(lastSeen(), ...events.map(event => event.id));
    try { localStorage.setItem(storageKey(), String(latest)); } catch { /* Reading still works without storage. */ }
    setUnreadCount(0);
  }, []);

  useEffect(() => {
    if (active) return;
    let cancelled = false;
    async function check() {
      if (document.visibilityState === 'hidden') return;
      try {
        const response = await api<{ items: AlertEvent[] }>('/api/alerts/history');
        if (!cancelled) setUnreadCount(response.items.filter(event => event.id > lastSeen()).length);
      } catch { /* The alert screen shows API errors when opened. */ }
    }
    void check();
    const timer = window.setInterval(() => void check(), 60_000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [active]);

  return { unreadCount, markSeen };
}
