const API = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000').replace(/\/+$/, '');
declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData?: string;
        colorScheme?: string;
        ready?: () => void;
        expand?: () => void;
        openInvoice?: (url: string, callback?: (status: 'paid' | 'cancelled' | 'failed' | 'pending') => void) => void;
      };
    };
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const initData = window.Telegram?.WebApp?.initData;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  };
  if (initData) headers['X-Telegram-Init-Data'] = initData;
  else if (import.meta.env.DEV) headers['X-Dev-User'] = 'local-dev';

  let response: Response;
  try {
    response = await fetch(`${API}${path}`, { ...init, headers });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(`Cannot connect to MarketPulse API at ${API}. Start the backend and open the frontend from localhost:5173 or 127.0.0.1:5173.`);
    }
    throw error;
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export type Ticker = {
  symbol: string;
  price: string;
  change_percent: string;
  quote_volume: string;
  source: string;
  updated_at: string;
};

export type Candle = {
  time: number;
  close_time?: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  closed: boolean;
};

export type OfficialFxRate = {
  symbol: string;
  base: string;
  quote: 'RUB';
  name: string;
  nominal: string;
  official_value: string;
  rate: string;
  source: 'Bank of Russia';
  rate_type: 'official_daily_reference';
  rate_date: string;
};

export type OfficialFxResponse = {
  source: 'Bank of Russia';
  rate_type: 'official_daily_reference';
  rate_date: string;
  items: OfficialFxRate[];
  stale?: boolean;
  warning?: string;
  unsupported_symbols?: string[];
};

export type FxCurrency = {
  code: string;
  name: string;
  symbol: string;
  numeric_code: string | null;
  start_date: string | null;
  end_date: string | null;
};

export type FxCurrencyCatalog = {
  source: 'Frankfurter';
  count: number;
  items: FxCurrency[];
  cached?: boolean;
  stale?: boolean;
  warning?: string;
};

export type WorldFxRate = {
  symbol: string;
  base: string;
  quote: string;
  rate: string;
  source: 'Frankfurter';
  rate_type: 'daily_reference';
  rate_date: string;
};

export type WorldFxResponse = {
  source: 'Frankfurter';
  source_description: string;
  rate_type: 'daily_reference';
  base: string;
  rate_date: string | null;
  items: WorldFxRate[];
  unsupported_quotes: string[];
  stale?: boolean;
  warning?: string;
};

export type PortfolioPosition = {
  id: number;
  symbol: string;
  base_asset: string | null;
  quote_asset: string;
  quantity: string;
  average_entry_price: string | null;
  current_price: string | null;
  market_value: string | null;
  cost_basis: string | null;
  unrealized_pnl: string | null;
  unrealized_pnl_percent: string | null;
  valuation_status: 'available' | 'unavailable';
  source: string | null;
};

export type PortfolioTotal = {
  quote_asset: string;
  market_value: string;
  cost_basis: string | null;
  unrealized_pnl: string | null;
  priced_positions: number;
  positions_with_entry_price: number;
  positions_with_pnl: number;
  unpriced_positions: number;
};

export type PortfolioResponse = {
  source: string;
  updated_at: string | null;
  items: PortfolioPosition[];
  totals_by_quote_asset: PortfolioTotal[];
  warnings: string[];
};


export type FxConversionResponse = {
  source: 'Frankfurter';
  rate_type: 'daily_reference';
  rate_date: string | null;
  from_currency: string;
  to_currency: string;
  amount: string;
  rate: string;
  converted_amount: string;
  stale?: boolean;
  warning?: string | null;
};
