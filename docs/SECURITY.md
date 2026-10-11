# Security notes

- Keep `.env` out of version control; rotate a bot token immediately if it is exposed.
- Telegram `initData` is validated on the server using HMAC-SHA256 and a maximum-age check. The client-supplied `initDataUnsafe` object is never used for authentication.
- Development auth accepts a local fixed development identity only when both `ENVIRONMENT=development` and `DEV_AUTH_ENABLED=true`. This is not production authentication.
- Set `DEV_AUTH_ENABLED=false`, `ENVIRONMENT=production`, strict `CORS_ORIGINS`, HTTPS and a real Telegram bot token before deployment.
- User-scoped records must always be queried by authenticated user id. Do not add client-provided user IDs as authorization.
- No exchange API keys or trading permissions are required by this MVP. Never request withdrawal/trading scopes for an analytics-only product.
- Public market data access does not automatically permit redistribution. Obtain legal/licensing approval before launch.
- Rate limiting, persistent session/token strategy, security headers, audit trail and production migration workflow remain required before public deployment.
