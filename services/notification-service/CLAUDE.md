# CLAUDE.md — Notification Service

> Read the root [CLAUDE.md](../../CLAUDE.md) first.

## Responsibilities

- Accept dispatch requests from the backend (when an alert rule fires)
- Send via Email (SMTP), Telegram (Bot API), or generic Webhook
- Retry transient failures with exponential backoff
- Never block the caller — return 202-style "queued" semantics

## Adding a New Channel

1. Create `app/channels/<name>.py` with a `Channel` subclass.
2. Add it to the `_channels` dict in `app/main.py`.
3. Document the expected `target` shape in the channel docstring.
4. Add an env-var feature flag in `app/config.py`.

## Templating

Use Jinja2 (already a dep) for richer email/Telegram bodies. Keep templates in
`app/templates/`. Don't auto-load templates yet — the backend currently builds
the body string itself, but this is the right place to push that responsibility
later.
