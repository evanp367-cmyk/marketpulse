# MarketPulse 0.4.8 — отчёт QA и ограничения production

## Что входит в пакет

- GitHub Actions workflow для публикации frontend в GitHub Pages с Vite base path `/<repository-name>/`.
- `VITE_API_URL` как публичная GitHub Actions repository variable.
- Docker image для FastAPI и Docker Compose для API, Telegram polling bot и Caddy reverse proxy.
- Порт API `8000` не опубликован напрямую на VPS; наружу выставлены только 80/443 через Caddy.
- Бесплатный hostname через DuckDNS, HTTPS через автоматический Caddy ACME workflow.
- PostgreSQL через Supabase shared session pooler, production-проверки конфигурации.
- Подписка Pro за 250 Telegram Stars за период 30 дней.
- Русский пошаговый гайд: `VPS_GITHUB_PAGES_GUIDE.md`.

## Проверки, выполненные в этой среде

- `python3 -m compileall -q backend`: пройдено.
- `python3 -m pytest -q`: **56 passed**.
- `frontend/package.json`: JSON parse пройден.
- `compose.yaml` и `.github/workflows/deploy-pages.yml`: YAML parse пройден.
- Проверены наличие Dockerfile, Compose, Caddyfile и GitHub Pages workflow.
- Проверены workflow action references на текущие официальные releases, доступные на момент подготовки.
- ZIP после финальной сборки требуется проверить командой `unzip -t`.

## Что не удалось выполнить в этой среде

- `npm install --no-audit --no-fund` не завершился в лимит времени из-за сетевого/реестрового доступа. Поэтому production-сборка frontend (`npm run build`) здесь **не подтверждена**; выполнить её локально на Mac или дать GitHub Actions успешно выполнить workflow.
- В этой среде нет Docker CLI, поэтому `docker compose config`, `docker build` и контейнерный запуск не были выполнены.
- Не выполнялись реальные операции на аккаунтах владельца: публикация в GitHub Pages, настройка VPS, выдача TLS-сертификата, соединение с фактической базой Supabase.
- Реальный Telegram Mini App авторизационный/платёжный lifecycle не проходил end-to-end тестирование. Перед продажей Pro требуется безопасный тест в выделенной тестовой среде Telegram.

## Важные ограничения перед запуском для пользователей

- При GitHub Free Pages репозиторий должен быть публичным; при едином репозитории backend-код тоже виден. Ни один секрет не должен попадать в git.
- PostgreSQL schema в этом релизе создаётся через SQLAlchemy `create_all`; это не замена управляемым Alembic migrations при изменении схемы в production.
- Сохранённые правила alert пока не имеют фонового worker, который исполняет их и доставляет уведомления.
- Настройте резервные копии и проверьте коммерческие условия поставщиков данных.
- Бесплатный Supabase может приостанавливать неактивные проекты; проверьте актуальный тариф и ограничения.
