# JudgeX API

The API provides email/password authentication, role-based access, event and track setup, team creation and invite-code joining, project submissions, private document upload/download, GitHub and deployment link checks, consented evidence ingestion, rubric versioning, AI-assisted scoring, judge review, publication gating, leaderboard, appeals, and audit records.

## Run locally on Windows

1. Open PowerShell in `outputs/JudgeX/backend`.
2. If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope Process Bypass` in that window.
3. Run `./start.ps1`. It creates a virtual environment, installs `requirements.txt`, creates a local `.env`, and prints the local URL where JudgeX is running. Open that URL (not `index.html` as a file). The script tries ports 8000–8010 and uses the first available one.
4. In another PowerShell window at the same folder, create an organizer account:

   ```powershell
   ./.venv/Scripts/python.exe -m judgex.create_admin --name "Your Name" --email "you@example.edu" --institution "Your Institution" --role organizer
   ```

   The command prompts for a password. Sign in at the local JudgeX page. Participants can register from the sign-in screen.

The default database is SQLite in `backend/judgex.db`; uploads are kept privately under `backend/data/private_uploads`. Those runtime files are ignored by Git. Use a second browser profile or incognito window to try a participant account.

## PostgreSQL

Set `DATABASE_URL` in `backend/.env` to a PostgreSQL SQLAlchemy URL, for example:

```text
DATABASE_URL=postgresql+psycopg://judgex:your-local-password@localhost:5432/judgex
```

PostgreSQL must be installed or run separately. The API uses SQLAlchemy and psycopg; SQLite is the easiest local start. Before production, set a unique long `JWT_SECRET`, use HTTPS, and configure `FRONTEND_ORIGINS` for exact trusted origins.

## API surface

- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- `GET /api/v1/hackathons`, organizer `GET /api/v1/hackathons/mine`, `POST /api/v1/hackathons`, status updates
- `POST /api/v1/teams`, `POST /api/v1/teams/join`, `GET /api/v1/teams/mine`; team leaders can transfer leadership or remove members under `/api/v1/teams/{id}/members/{user_id}`
- Submission create/read/update, status changes, private document upload/download, and URL checks under `/api/v1/submissions`
- `GET/PUT /api/v1/hackathons/{event_id}/rubric?round_number=1`; organizer `POST /api/v1/hackathons/{event_id}/judges`; `GET /api/v1/judges/assignments`. Rubrics are independently versioned per round (1–10).
- `POST /api/v1/submissions/{id}/ingest` and `/evaluate?round_number=1`; evidence search under `/api/v1/submissions/{id}/evidence`
- `GET /api/v1/submissions/{id}/scorecards`; judge `POST /api/v1/scorecards/{id}/review`. Scorecards record the round of their rubric.
- `GET /api/v1/hackathons/{id}/leaderboard?round_number=1` after results are published; participant appeals and organizer appeal listing/resolution under `/api/v1/scorecards/{id}/appeals`, `/api/v1/hackathons/{id}/appeals`, and `/api/v1/appeals/{id}`
- Organizer reminders: `POST/GET /api/v1/hackathons/{id}/reminders`; cancel a scheduled reminder with `DELETE /api/v1/hackathons/{id}/reminders/{reminder_id}`. The API process checks due reminders every 15 seconds and queues in-app notifications plus email when SMTP is configured.
- Super-admin institution and role management: `GET/POST /api/v1/admin/institutions`, `GET /api/v1/admin/users`, and `PATCH /api/v1/admin/users/{user_id}`. Super-admin accounts remain provisioned outside this endpoint.
- Participant pitch question generation: `POST /api/v1/submissions/{id}/pitch-questions`; extracted transcript claims and browser screen-share timing signals are returned with pitch sessions. AI functions require participant processing consent and provider configuration. Screen-share timing is review context only and never changes a score.
- Judge/organizer document overlap review: `POST /api/v1/submissions/{id}/integrity-check`; compares same-event extracted material and records possible overlaps as human-review flags.
- `GET /api/v1/audit-logs?entity_id=...` and `GET /health`
- Interactive API reference: `http://127.0.0.1:8000/docs`

Publicly registered accounts are participants. Use the admin command to provision organizer, judge, mentor, or viewer accounts. Team member email addresses are not exposed to teammates. Judge assignment currently requires an active judge account in the event's institution. Configure `OPENAI_API_KEY` in `.env` to enable transcription, embeddings, and scorecard generation. Project processing requires recorded participant AI consent; evaluations remain advisory until a judge approves the card. Results cannot be published until every submitted project has an approved scorecard.

## Current scope and production work

Run the included integration checks from the repository root with `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v`; check frontend syntax with `node --check app.js` and `node --check phase2.js`. The local SQLite setup is intended for development. Production still requires durable schema migrations, deployment and monitoring, a managed database/object store, and load/security review. Google sign-in requires OAuth credentials, email delivery requires SMTP settings, and AI scoring/transcription/OCR/question generation requires an OpenAI API key plus the appropriate participant consent.
