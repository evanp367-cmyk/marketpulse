# Telegram API через Cloudflare Worker

На REG.RU VPS соединение с `api.telegram.org:443` иногда обрывается до HTTPS. Этот Worker направляет **только запросы Telegram Bot API** через Cloudflare. Он не заменяет доступ к Binance или ЦБ. Для развёртывания нужен ваш аккаунт Cloudflare; код Worker есть в `workers/telegram-api.mjs`. Сам код публичный, но секретный ключ маршрута должен храниться только в Cloudflare и приватном `.env` на VPS.

## 1. Создайте Worker на Mac

Зарегистрируйтесь в Cloudflare, подтвердите почту и включите бесплатный адрес `workers.dev`, если Cloudflare его предложит. В Terminal выполните команды из актуального Git-клона MarketPulse:

```bash
cd /Users/livangogoryan/Downloads/marketpulse-current
git pull --ff-only origin main
cd workers
npx wrangler login
npx wrangler deploy
```

Команда `login` откроет браузер для входа в Cloudflare. После `deploy` запишите выданный адрес вида `https://marketpulse-telegram-api.<ваш-поддомен>.workers.dev`. Пока секрет не добавлен, Worker возвращает HTTP 503 — это ожидаемо.

Создайте случайный ключ длиной 64 шестнадцатеричных символа:

```bash
openssl rand -hex 32
```

Скопируйте результат **только в свои приватные настройки**. В той же папке `workers` выполните:

```bash
npx wrangler secret put ROUTE_KEY
```

На приглашение вставьте созданный ключ. Не добавляйте его в `wrangler.toml`, GitHub, сообщения или скриншоты. Адрес для MarketPulse будет `https://marketpulse-telegram-api.<ваш-поддомен>.workers.dev/<ваш-ключ>` без завершающего `/`.

## 2. Подключите VPS

В SSH-сессии сервера:

```bash
cd /opt/marketpulse
git pull --ff-only origin main
cp -p .env ".env.backup-$(date +%Y%m%d-%H%M%S)"
nano .env
```

В `.env` оставьте `TELEGRAM_PROXY_URL=` пустым и добавьте строку `TELEGRAM_API_BASE_URL=` с вашим полным адресом Worker и секретным путём. Сохраните файл, затем:

```bash
chmod 600 .env
docker compose config --quiet
docker compose up -d --build api bot
docker compose ps
```

Не публикуйте `.env` или полный адрес Worker. Не удаляйте том PostgreSQL. Бот и API используют один и тот же маршрут; он нужен также для создания счёта Telegram Stars.

## 3. Проверьте связь без раскрытия токена

Следующая команда не печатает токен и адрес Worker. Запускайте её на VPS из `/opt/marketpulse`:

```bash
docker compose exec -T api python - <<'PY'
import httpx
from backend.app.core.config import settings

base = settings.telegram_api_base_url.strip().rstrip("/")
if not base:
    print("TELEGRAM_API_BASE_URL не задан")
else:
    try:
        response = httpx.get(
            f"{base}/bot{settings.telegram_bot_token}/getMe",
            timeout=15,
            trust_env=False,
        )
        result = response.json()
        print("Telegram HTTP:", response.status_code)
        print("getMe:", result.get("ok"))
        if result.get("ok"):
            print("Имя бота:", result["result"].get("username"))
    except Exception as exc:
        print("Ошибка связи:", type(exc).__name__)
PY
```

Ожидается `Telegram HTTP: 200`, `getMe: True`, имя `marketpulse_livan_bot`. Затем напишите боту `/start`; он должен ответить ссылкой на Mini App. `docker compose ps bot` должен показывать устойчивый статус `Up`, а не постоянные перезапуски. Реальную оплату Stars проверяйте отдельно после проверки `/start`.

Если Worker недоступен с VPS, сначала проверьте HTTPS-доступ к своему `workers.dev`-домену. Возможность маршрута зависит от доступности Cloudflare в сети провайдера; само развёртывание не гарантирует работу до живого `getMe` и `/start`.
