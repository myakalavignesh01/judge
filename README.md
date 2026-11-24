# JudgeX

JudgeX is an evidence-led hackathon judging application. The current build includes a local API and database for identity, event and team setup, project submissions, consented evidence processing, rubric-based AI recommendations, human judging, result publication, appeals, and privacy requests.

## Start locally

Follow [the backend setup guide](backend/README.md). On Windows, run `backend/start.ps1`, create an organizer account from a second PowerShell window, then open the URL printed by the startup script. The API serves the frontend.

The startup script prints the actual local URL. Open that URL; do not open `index.html` directly, because a `file://` page cannot use the API. If port 8000 is in use, the script selects an available port from 8000–8010.

For a read-only sample preview, open `index.html` and choose **View sample workspace (preview)**. The preview uses local sample data; real login and saved changes require the API server.

## Deploy to Render

The repository includes [`render.yaml`](render.yaml), a **free-tier demo Blueprint** with one Python web service and a free PostgreSQL database. Use **New → Blueprint** in Render and connect this repository; no login credentials are needed during deployment.

This free configuration is for testing only. Free web services sleep after 15 minutes without traffic and their local filesystem is temporary, so uploaded documents and pitch recordings may disappear after a restart or sleep. Free Render Postgres expires 30 days after creation, so JudgeX account and event data will not remain available indefinitely. The Blueprint intentionally has no persistent disk and selects only free plans.

To make an account, choose **Participant sign up**, enter your name and Gmail address, and create a JudgeX password of at least 10 characters. Then sign in with that Gmail address and JudgeX password. Your Google account password is not used, and no OAuth credentials are required. Organizer accounts are provisioned separately by an administrator. Set optional `OPENAI_API_KEY`, SMTP, and GitHub credentials in Render only when you enable those integrations.

After deployment, verify `<service-url>/health` returns `{"status":"ok"}` and open `<service-url>/` to sign in. The Blueprint deploys new commits after the GitHub Actions checks pass.

## Available now

- Participant registration, password login, email OTP and reset flows, and role-based access.
- Organizer event setup and editing, tracks, deadlines, document requirements, team limits, and registration/judging status transitions.
- Participant team creation, invite-code joining, leadership transfer, member removal, draft editing, event-scoped document uploads, link checks, and final submission.
- Private file storage, document extraction and OCR, GitHub README/commit/source retrieval, secret redaction, consent-gated evidence indexing, and local possible-overlap flags for human review.
- Consent-gated browser pitch recording with camera/screen composition, private uploads, screen-share duration metadata, provider transcription, quoted pitch-claim extraction, and evidence-grounded question suggestions.
- Independently versioned rubrics for up to 10 rounds, judge assignments, evidence-grounded AI recommendations, citations, judge overrides, review flags, and approval.
- Per-round publication gates, leaderboards and participant feedback, certificates, appeals, CSV and print-to-PDF reports, and event analytics.
- Institution and user-role administration, scheduled participant/judge reminders, in-app notifications with optional SMTP delivery, profile and privacy tools.
- Responsive organizer, participant, and judge screens backed by the API.

## Remaining production work

This is a functional pilot build, not a production-ready deployment. The automated tests cover round publication, participant visibility, team leadership, institution administration, document-overlap review, and reminder scheduling. The overlap scan only compares text within one event and creates a human-review signal; it does not establish plagiarism. Pitch analysis extracts quoted claims, but it does not perform computer-vision feature verification or external originality research. Production still needs durable schema migrations, monitoring, load/security review, and a managed database and object store. Email OTP and password reset need SMTP credentials. AI scoring, OCR, embeddings, transcription, and question generation need an OpenAI API key and the relevant participant consent. Put credentials only in `backend/.env`, never in browser code.

Use a modern browser with JavaScript enabled. Event, account, team, rubric, submission, and document data are stored by the local API.
