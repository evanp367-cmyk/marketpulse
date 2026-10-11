# MarketPulse 0.4.9 — полный гайд для новичка (PostgreSQL на VPS)

Цель: запустить MarketPulse для тестировщиков. Интерфейс бесплатный на GitHub Pages, API и бот работают на REG.RU VPS, база PostgreSQL размещена **на том же VPS внутри Docker**, API доступен по HTTPS через бесплатный DuckDNS. Supabase не нужен и оплачивать красивый домен не требуется.

## Карта компонентов

- **GitHub Pages:** React/Vite-интерфейс, например `https://YOUR_GITHUB_USERNAME.github.io/marketpulse/`.
- **REG.RU VPS:** Docker Compose запускает API, бота, PostgreSQL и Caddy.
- **DuckDNS:** бесплатное DNS-имя, например `marketpulse-api.duckdns.org`, указывающее на IP VPS.
- **Caddy:** проксирует HTTPS-запросы на API и автоматически обслуживает сертификат.
- **PostgreSQL 16:** данные сохраняются в Docker volume `postgres_data`. База не имеет открытого порта 5432.
- **Telegram:** Mini App и Stars-подписка Pro за 250 ⭐ на 30 дней.

> Важно: если VPS удалить/потерять, можно потерять и базу. Docker volume не является резервной копией. В этой инструкции есть команда backup, а копию нужно скачать на Mac или хранить в другом защищённом месте.

## Этап 0. Проверь локальную версию на Mac

Распакуй архив в `~/Downloads/marketpulse-v0.4.9`, открой Terminal и выполни команды по очереди:

```bash
cd ~/Downloads/marketpulse-v0.4.9
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m compileall -q backend
python3 -m pytest -q
```

Потом frontend во второй части проверки:

```bash
cd ~/Downloads/marketpulse-v0.4.9/frontend
npm install
npm run build
```

Если `npm run build` выдаёт ошибку — сначала реши её, не переходи на VPS. Локальный запуск API (первый Terminal):

```bash
cd ~/Downloads/marketpulse-v0.4.9
source .venv/bin/activate
python3 -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Второй Terminal:

```bash
cd ~/Downloads/marketpulse-v0.4.9/frontend
npm run dev
```

Открой `http://localhost:5173`. Для локальной работы оба Terminal должны оставаться открытыми.

## Этап 1. Создай бесплатный API-домен в DuckDNS

1. Открой https://www.duckdns.org/ и войди.
2. Создай свободное имя, например `marketpulse-api-evanp367` (имя может быть занято; выбери любое свободное).
3. Получится адрес вида `marketpulse-api-evanp367.duckdns.org`.
4. Сохрани DuckDNS token приватно. Не публикуй его и не вставляй в GitHub.
5. IP пока не выдумывай: сначала купим VPS, а затем укажем реальный публичный IPv4.

## Этап 2. Создай GitHub-репозиторий и включи Pages

**Важное ограничение:** на GitHub Free Pages для этого простого workflow нужен public-репозиторий, поэтому backend-код тоже будет виден. `.env`, ключи, пароли, токены, дампы базы и приватные файлы публиковать нельзя. Если нельзя раскрывать backend-код, остановись и измени схему хостинга до публикации.

1. Открой https://github.com/new.
2. Название репозитория: `marketpulse`; выбери **Public**.
3. Не ставь галочки добавления README, `.gitignore` или License — файлы уже есть в проекте.
4. После создания открой **Settings → Pages** и выбери **GitHub Actions** как источник публикации.
5. Открой **Settings → Secrets and variables → Actions → Variables → New repository variable**.
6. Создай переменную `VITE_API_URL` со значением `https://YOUR_DUCKDNS_SUBDOMAIN.duckdns.org` без завершающего `/`. Замени пример на своё имя DuckDNS. API ещё может быть не запущен — переменная нужна сборке.

На Mac, в корне проекта:

```bash
cd ~/Downloads/marketpulse-v0.4.9
git init
git branch -M main
git add .
git status --short
```

Внимательно проверь список. В нём **не должно быть** `.env`, файлов базы (`.db`, `.sqlite`), `.venv`, `node_modules`, `dist`, токенов и резервных копий. Дополнительная проверка:

```bash
git diff --cached --name-only | grep -E '(^|/)\.env$|(^|/)\.venv/|(^|/)node_modules/|\.db$|\.sqlite3?$|\.sql\.gz$' || true
```

Если вывод не пустой, остановись и удали секретные файлы из staging, прежде чем продолжить. Потом:

```bash
git commit -m "Prepare MarketPulse 0.4.9 deployment"
git remote add origin git@github.com:YOUR_GITHUB_USERNAME/marketpulse.git
git push -u origin main
```

Заменяй `YOUR_GITHUB_USERNAME` на реальное имя GitHub. Если `origin` уже существует, посмотри `git remote -v` вместо повторного `git remote add`. Должен пройти workflow **Deploy MarketPulse frontend to GitHub Pages** на вкладке Actions. После зелёного результата frontend будет примерно здесь:

`https://YOUR_GITHUB_USERNAME.github.io/marketpulse/`

Если workflow падает, открой failed job и читай первую ошибку. Проверь, что `VITE_API_URL` установлен и начинается с `https://`.

## Этап 3. Арендуй VPS на неделю

Для небольшого теста ориентир — KVM, 2 vCPU, 4 ГБ RAM, 30+ ГБ SSD/NVMe, Ubuntu 24.04 LTS и публичный IPv4. Это ориентир, не гарантия пропускной способности. Перед оплатой проверь минимальный оплачиваемый период, цену продления, политику возврата и стоимость IPv4. Не покупай платную панель управления.

В панели REG.RU создай сервер с Ubuntu. Сохрани IP и SSH-логин. На Mac открой Terminal:

```bash
ssh root@YOUR_VPS_IP
```

Замени `YOUR_VPS_IP`. На вопрос про fingerprint сверяй его с панелью провайдера, если он там показан; только после этого подтверждай подключение. Если логин не `root`, используй данные панели.

## Этап 4. Установи Docker на VPS и открой только нужные порты

В SSH-терминале VPS:

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl git ufw nano gzip
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sh /tmp/get-docker.sh
rm /tmp/get-docker.sh
systemctl enable --now docker
docker --version
docker compose version
```

Настрой firewall:

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw enable
ufw status
```

Если REG.RU имеет дополнительный firewall в панели, разреши входящий TCP 22, 80, 443 и UDP 443. **Не открывай наружу порты 5432 (PostgreSQL) и 8000 (API)**. Docker Compose соединяет контейнеры внутри приватной сети.

## Этап 5. Направь DuckDNS на VPS

На VPS подставь своё имя DuckDNS (без `.duckdns.org`) и токен:

```bash
install -d -m 700 /opt/duckdns
nano /opt/duckdns/update.sh
```

Вставь скрипт, заменив оба placeholder:

```sh
#!/bin/sh
set -eu
DOMAIN="YOUR_DUCKDNS_SUBDOMAIN"
TOKEN="YOUR_DUCKDNS_TOKEN"
RESPONSE="$(curl -fsS "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip=")"
if [ "$RESPONSE" != "OK" ]; then
  echo "DuckDNS update failed" >&2
  exit 1
fi
```

В nano: `Ctrl+O`, Enter, `Ctrl+X`. Затем:

```bash
chmod 700 /opt/duckdns/update.sh
/opt/duckdns/update.sh
getent ahostsv4 YOUR_DUCKDNS_SUBDOMAIN.duckdns.org
```

Если `getent` не показывает IP, проверь имя/токен в DuckDNS и подожди обновления DNS. Подставь своё имя в последнюю команду.

Добавь автоматическое обновление каждые 5 минут:

```bash
crontab -e
```

В конец добавь строку (подставлять имя внутри cron не требуется, оно уже в скрипте):

```cron
*/5 * * * * /opt/duckdns/update.sh >/dev/null 2>&1
```

Сохрани cron. Токен остаётся только в `/opt/duckdns/update.sh` на VPS с правами `700`. Не включай вывод полного URL с токеном в логи и не помещай файл в Git.

## Этап 6. Загрузить проект на VPS

В терминале VPS:

```bash
mkdir -p /opt/marketpulse
cd /opt/marketpulse
git clone https://github.com/YOUR_GITHUB_USERNAME/marketpulse.git .
```

Замени GitHub username. Если проект уже склонирован, не повторяй `git clone` в непустую папку; вместо этого выполни `cd /opt/marketpulse && git pull --ff-only`.

Создай production-конфигурацию:

```bash
cd /opt/marketpulse
cp .env.vps.example .env
chmod 600 .env
nano .env
```

### Что заполнить в `.env`

1. `POSTGRES_DB=marketpulse` — оставь как есть.
2. `POSTGRES_USER=marketpulse` — оставь как есть.
3. Сгенерируй пароль командой (можно в отдельном Terminal Mac или на VPS):

   ```bash
   openssl rand -hex 32
   ```

   Скопируй вывод в `POSTGRES_PASSWORD=`. Это 64 символа hex; не добавляй кавычки и пробелы. **Сохрани пароль в менеджере паролей.** Не используй один и тот же пароль в других сервисах.
4. `TELEGRAM_BOT_TOKEN` — настоящий токен из `@BotFather`.
5. `TELEGRAM_BOT_USERNAME` — username бота без `@`.
6. `TELEGRAM_PRO_PRICE_STARS=250` — оставить.
7. `SUPPORT_ADMIN_IDS` — цифровой Telegram ID админа.
8. `MINI_APP_URL=https://YOUR_GITHUB_USERNAME.github.io/marketpulse/` — укажи реальный GitHub username, сохрани завершающий `/marketpulse/`.
9. `CORS_ORIGINS=https://YOUR_GITHUB_USERNAME.github.io` — только origin; не добавляй `/marketpulse/` и завершающий `/`.
10. `API_DOMAIN=YOUR_DUCKDNS_SUBDOMAIN.duckdns.org` — hostname, без `https://` и пути.
11. `ENVIRONMENT=production`, `DEV_AUTH_ENABLED=false` — обязательно.

**Не добавляй `DATABASE_URL` в `.env`.** Compose автоматически построит внутреннее подключение к сервису `db` через `db:5432`; база не должна подключаться через публичный IP. Не коммить `.env`.

После сохранения проверь, что не осталось placeholder-значений:

```bash
grep -nE 'YOUR_|PUT_REAL|REPLACE_WITH|your_bot_username' .env
```

Команда не должна ничего вывести. Если показывает строки — исправь их. Не используй `cat .env` при копировании сюда: там находятся секреты.

## Этап 7. Запусти PostgreSQL, API, бот и HTTPS

Сначала проверь Docker Compose config:

```bash
cd /opt/marketpulse
docker compose config --quiet
```

Если ошибок нет, запускай:

```bash
docker compose up -d --build
docker compose ps
```

Первый запуск может занять несколько минут. Compose запускает:

- `db` — PostgreSQL и постоянный volume `postgres_data`;
- `api` — FastAPI, дождётся healthy базы;
- `bot` — Telegram polling-бот;
- `caddy` — принимает HTTPS и проксирует его в API.

Проверь статусы и логи:

```bash
docker compose ps
docker compose logs --tail=100 db
docker compose logs --tail=100 api
docker compose logs --tail=100 bot
docker compose logs --tail=100 caddy
```

У `db` и `api` должен быть статус healthy (или `Up` плюс успешный healthcheck). Если Caddy не выдаёт сертификат, проверь, что DuckDNS уже указывает на этот VPS и входящие TCP 80/443 разрешены. Не открывай port 8000 или 5432 в публичный firewall.

Проверь API с Mac:

```bash
curl -i --max-time 15 https://YOUR_DUCKDNS_SUBDOMAIN.duckdns.org/health
```

Заменяй имя. Ожидается HTTP 200 и JSON со статусом `ok`. Проверка через HTTPS обязательна до Mini App.

## Этап 8. Проверь связку GitHub Pages ↔ API

1. Открой `https://YOUR_GITHUB_USERNAME.github.io/marketpulse/`.
2. Открой DevTools браузера → Console и Network, если предупреждение API остаётся.
3. Убедись, что `VITE_API_URL` в GitHub Variables совпадает с адресом DuckDNS.
4. Если переменную меняли, перейди GitHub **Actions** и перезапусти workflow или отправь новый commit — переменная build-time и не изменит уже собранный сайт сама.
5. Ошибка CORS означает, что `CORS_ORIGINS` в серверном `.env` не совпадает с origin страницы, либо сервис не пересоздан после изменения.

## Этап 9. Подключи Telegram Mini App

В `@BotFather` настрой Menu Button / Mini App URL на:

`https://YOUR_GITHUB_USERNAME.github.io/marketpulse/`

Используй реальный адрес. Обнови ссылку бота и открой Mini App **из Telegram**, а не в обычном браузере. Доступ к Telegram-аккаунту и реальные платежи нельзя честно проверить только в локальном браузере. Backend должен проверять Telegram `initData`, а не доверять Telegram ID, присланному клиентом.

Проверь:

- бот отвечает на команды и приложение открывается через Telegram;
- API отдаёт котировки и валютный конвертер;
- один пользователь не видит чужие данные портфеля;
- тариф Pro показывает 250 ⭐ / 30 дней;
- `/terms` открывается;
- `/paysupport` работает только после настройки `SUPPORT_ADMIN_IDS`.

**Не проводи случайные реальные платежи ради проверки.** Сначала используйте подходящий тестовый процесс Telegram и подтвердите полный цикл pre-checkout → successful payment → подписка; настоящая оплата может списать Stars.

## Этап 10. Резервная копия PostgreSQL

Данные хранятся в named volume `postgres_data`. Это переживёт обычное пересоздание контейнеров, но не удаление volume/сервера. Делай бэкап и скачивай копию на Mac.

На VPS:

```bash
mkdir -p /opt/marketpulse-backups
chmod 700 /opt/marketpulse-backups
cd /opt/marketpulse
docker compose exec -T db sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "/opt/marketpulse-backups/marketpulse-$(date +%F-%H%M%S).sql.gz"
ls -lh /opt/marketpulse-backups
```

Для скачивания последнего файла с Mac — выполни **на Mac в другом Terminal**, не внутри SSH (замени IP и имя фактического файла):

```bash
scp root@YOUR_VPS_IP:/opt/marketpulse-backups/marketpulse-YYYY-MM-DD-HHMMSS.sql.gz ~/Downloads/
```

Не публикуй дамп на GitHub. Храни копию вне VPS. Чтобы восстановить дамп, сначала сделай новый backup текущей базы. На новой/пустой базе команда восстановления выглядит так (имя файла замени на реальное):

```bash
cd /opt/marketpulse
gunzip -c /opt/marketpulse-backups/marketpulse-YYYY-MM-DD-HHMMSS.sql.gz | docker compose exec -T db sh -lc 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Не восстанавливай поверх активной базы без понимания последствий: объекты могут уже существовать. Самый безопасный тест восстановления — в отдельный временный database/container.

## Этап 11. Обновление приложения

Изменил frontend/backend код на Mac? Перед `git add .` обязательно проверь, что `.env` не попал в staged files. Затем:

```bash
cd ~/Downloads/marketpulse-v0.4.9
git status --short
git add .
git status --short
git commit -m "Describe update"
git push
```

GitHub Pages пересоберётся автоматически. Для обновления API/бота на VPS:

```bash
ssh root@YOUR_VPS_IP
cd /opt/marketpulse
git pull --ff-only
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 api bot caddy
```

**Не запускай `docker compose down -v`** — параметр `-v` удалит Docker volume, а значит может удалить базу данных.

## Диагностика

| Симптом | Что проверить |
|---|---|
| GitHub Pages 404/пустая страница | Actions workflow, Settings → Pages, имя репозитория и путь `/marketpulse/` |
| Страница доступна, API offline | `VITE_API_URL`, `curl https://API/health`, `docker compose ps` |
| Ошибка сертификата | DuckDNS IP, порты 80/443, `docker compose logs --tail=200 caddy` |
| `db` unhealthy | пароль/пользователь в `.env`, `docker compose logs --tail=200 db` |
| API не стартует | `docker compose logs --tail=200 api`; проверь `ENVIRONMENT`, `DEV_AUTH_ENABLED`, Telegram token, URL и CORS; не публикуй вывод с секретами |
| Бот не отвечает | `docker compose logs --tail=200 bot`; проверь токен и username; не запускай локальный polling бот с тем же токеном одновременно |
| Не коннектится PostgreSQL | Compose должен использовать `db:5432`, без публичного IP и без опубликованного порта 5432 |
| Telegram показывает 401 | Открой Mini App внутри Telegram; проверь MINI_APP_URL, token и initData validation |

## Ежедневные команды обслуживания на VPS

```bash
cd /opt/marketpulse
docker compose ps
docker compose logs -f api
docker compose logs -f bot
docker compose logs -f caddy
```

`Ctrl+C` прекращает просмотр логов, но контейнеры продолжат работать. Проверяй свободное место (`df -h`) и регулярно выгружай backups за пределы сервера.

## Ограничения и безопасный тест

- Один VPS означает одну точку отказа. Регулярные off-site backups обязательны, даже для недельного теста.
- Бесплатный DNS не является гарантией доступности DNS, а HTTPS требует корректного DNS и открытых портов.
- Схема создаётся через SQLAlchemy `create_all`; это не полноценная миграционная система. Не считать любое обновление схемы безопасным автоматически.
- Источники котировок имеют свои условия использования; перед публичным/коммерческим запуском ознакомься с ними.
- Данные рынка, сигналы и индикаторы не гарантируют прибыль и не являются персональной инвестиционной рекомендацией.
- Unit-тесты не подтверждают реальную публикацию, получение сертификата или успешный платеж Telegram. Эти пункты надо проверить с учётными записями владельца.

## Официальные ссылки

- GitHub Pages: https://docs.github.com/en/pages
- Vite static deploy: https://vite.dev/guide/static-deploy.html
- DuckDNS: https://www.duckdns.org/
- Caddy Automatic HTTPS: https://caddyserver.com/docs/automatic-https
- Docker Engine: https://docs.docker.com/engine/install/ubuntu/
- Telegram Mini Apps: https://core.telegram.org/bots/webapps
- Telegram Stars: https://core.telegram.org/bots/payments-stars
