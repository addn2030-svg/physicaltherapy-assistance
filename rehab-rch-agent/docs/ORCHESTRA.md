# Agent v4 Orchestra — Proactive Operations Manual

The bot is no longer just reactive. Six support agents run on a schedule
inside the bot process, find gaps, push briefings, nudge therapists,
escalate to supervisors → head → higher admin, and auto-generate reports.

## Support agents (`agents.py`)

| Agent | Job | Produces |
|---|---|---|
| GapAgent | Every gap scan | Missing supervisor/staff reports, missing roles, missing Chat IDs, unverified capabilities, ownerless actions, stale equipment (7d+), overdue actions |
| WatchdogAgent | Every 30 min | CRITICAL equipment, uncovered/partial coverage, due-today actions, expired training |
| EscalationAgent | After 15:00 cutoff | Direct therapist nudges for missing `/daily` reports |
| BriefingAgent | 07:30 | Morning briefing push → head + all supervisors |
| ReportAgent | 17:00 + Sunday 08:00 | Evening rollup (Supervisor_Briefings rows + Drive `.docx`); weekly auto-fill (Weekly_Summary rows + Drive `.docx` + admin summary) |
| InsightAgent | On demand | Gemini narrative over pre-computed stats (AI polish — numbers fixed, never invented) |

## Escalation ladder (`messenger.py`)

```
therapist → unit supervisor → section head → higher admin
```

- Recipients resolve from `Telegram_Users` (Chat IDs), `Units` (supervisors),
  `Supervisors` (head), and `HIGHER_ADMIN_CHAT_IDS` (admin).
- Unknown Chat ID → escalates one level up with a "(for X — no Chat ID on
  file)" note, and the gap is flagged to the head.
- Higher admin receives **weekly summary + critical alerts only**.

## Timetable (`scheduler.py`, tz `SCHED_TZ` = Asia/Riyadh)

| Time | Job | Audience |
|---|---|---|
| 07:30 | Briefing push | Head + supervisors |
| 09:00 / 12:00 / 15:00 | Gap scans | Supervisors + head |
| ≥15:00 | Cutoff nudges | Therapists missing `/daily` |
| 17:00 | Evening rollup + archive | Head (+ Drive `.docx`) |
| SUN 08:00 | Weekly auto-draft | Head + higher admin (+ Drive `.docx`) |
| Every 30 min | Watchdog | By severity |
| 22:00–06:30 | Quiet hours | Critical only, rest held |

## Anti-noise rules

- **Dedup**: each finding has a stable key (`gap:sup:2026-09-13:U02`) and a
  window (critical 2h, warning 6h via `ALERT_DEDUP_HOURS`, info 24h).
  State file: `output/orchestra_state.json` (survives restarts).
- **Quiet hours**: non-critical held overnight (never dropped — retried).
- **Deterministic numbers**: agents compute; Gemini only narrates.
- **Audit**: every tick logs a summary; every critical + unroutable alert
  is individually audited (local JSONL + `Agent_Audit_Log` tab).

## Provisioning flow

1. Staff send `/register` → name + unit → row in `Telegram_Users`
   (`Active=FALSE`, pending).
2. Admins get a nudge → `/approve` lists pending → `/approve <name>`.
3. User gets a ✅ DM and can immediately use the bot + receive alerts.
4. Offboard: set `Active=FALSE` in the sheet (or `/approve` only approves —
   suspension is a sheet edit), access drops on next message.

## Live operations (24/7)

Systemd (Oracle, recommended):
```bash
sudo systemctl status rehab-agent
sudo journalctl -u rehab-agent -f
bash scripts/go_live.sh        # update + self-test + restart
```

Docker alternative:
```bash
docker compose up -d --build
docker compose ps              # health: heartbeat fresh < 5 min
```

Monitoring:
- `output/heartbeat.txt` — bot writes `alive <ts>` every 60s. Stale = down.
- `/schedule` in Telegram — timetable + status.
- `/audit` (admin) — recent events incl. `orchestra_tick` summaries.
- `Agent_Audit_Log` tab — sheet-side trail.

Tuning: all times/windows in `.env` (`BRIEFING_TIME`, `GAP_SCAN_TIMES`,
`REPORT_CUTOFF`, `ROLLUP_TIME`, `WEEKLY_DAY/TIME`, `WATCHDOG_MINUTES`,
`QUIET_HOURS`, `ALERT_DEDUP_HOURS`, `HIGHER_ADMIN_CHAT_IDS`) → restart.
Set `SCHED_ENABLED=false` to run reactive-only.
