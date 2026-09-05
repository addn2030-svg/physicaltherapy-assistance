# Telegram project memory and video service

This change adds guarded command handlers. It does not start a second Telegram poller and does not deploy MoneyPrinterTurbo inside the clinical application.

## Required configuration

```text
TELEGRAM_ALLOWED_CHAT_IDS=123456789
GOOGLE_DRIVE_ACCESS_TOKEN=<runtime OAuth access token>
GOOGLE_DRIVE_STATUS_FILE_ID=<Status.md file ID>
GOOGLE_DRIVE_PROGRESS_FILE_ID=<Progress.md file ID>
GOOGLE_DRIVE_DECISION_FILE_ID=<Decision.md file ID>
MONEYPRINTER_API_URL=https://private-video-service.example
MONEYPRINTER_API_KEY=<service API key>
```

Share `Status.md`, `Progress.md`, and `Decision.md` with the Google identity represented by the runtime OAuth token. The three IDs must be distinct. `/memory_check` proves that this identity can read the exact three expected filenames. It performs only Google Drive `GET` requests.

## Telegram commands

- `/status`, `/progress`, `/decision`: read the configured project-memory documents.
- `/memory_check`: verify IDs, names, and read access without modifying Drive.
- `/video_create <topic>`: submit one Arabic portrait video job.
- `/video_status <task-id>`: query an existing video job.

Wire `TelegramProjectCommands.handle(String(message.chat.id), message.text)` into the existing webhook or polling handler. Do not start an additional poller; Telegram permits only one consumer for long polling.

## MoneyPrinterTurbo boundary

Deploy the official MoneyPrinterTurbo container as a separate private service. Set `app.api_key` in its `config.toml`, pin a tested container release instead of `latest`, keep `/tasks` protected, and expose it over HTTPS. The adapter calls the upstream `/api/v1/videos` and `/api/v1/tasks/{task_id}` endpoints and sends the API key as a bearer token.

## Smallest safe acceptance test

1. Configure a non-production Telegram chat ID and read-only Google OAuth scope.
2. Send `/memory_check`.
3. Accept only `✅ Status.md`, `✅ Progress.md`, and `✅ Decision.md`.
4. Confirm Drive audit/activity shows three reads and no writes.

This tests authorization, all required IDs, exact filenames, and sharing while avoiding project-memory changes, video generation cost, and production deployment.
