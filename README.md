# JudgeX

JudgeX is an evidence-led hackathon judging application. The current build includes a local API and database for identity, event and team setup, project submissions, consented evidence processing, rubric-based AI recommendations, human judging, result publication, appeals, and privacy requests.

## Start locally

Follow the [backend setup guide](backend/README.md). On Windows, run backend/start.ps1, create an organizer account from a second PowerShell window, then open the URL printed by the startup script. The API serves the frontend.

The startup script prints the actual local URL. Open that URL; do not open index.html directly, because a file:// page cannot use the API or complete Google sign-in. If port 8000 is in use, the script selects an available port from 8000–8010.

For a read-only sample preview, open index.html and choose **View sample workspace (preview)**. The preview uses local sample data; real login and saved changes require the API server.

## Available now

- Participant registration, password login, email OTP and reset flows, optional Google OAuth, and role-based access.
- Organizer event setup and editing, tracks, deadlines, document requirements, team limits, and registration/judging status transitions.
- Participant team creation, invite-code joining, leadership transfer, member removal, draft editing, event-scoped document uploads, link checks, and final submission.
- Private file storage, document extraction and OCR, GitHub README/commit/source retrieval, secret redaction, consent-gated evidence indexing, and local possible-overlap flags for human review.
- Consent-gated browser pitch recording with camera/screen composition, private uploads, screen-share duration metadata, provider transcription, quoted pitch-claim extraction, and evidence-grounded question suggestions.
- Independently versioned rubrics for up to 10 rounds, judge assignments, evidence-grounded AI recommendations, citations, judge overrides, review flags, and approval.
- Per-round publication gates, leaderboards and participant feedback, certificates, appeals, CSV and print-to-PDF reports, and event analytics.
- Institution and user-role administration, scheduled participant/judge reminders, in-app notifications with optional SMTP delivery, profile and privacy tools.
- Responsive organizer, participant, and judge screens backed by the API.

## Remaining production work

This is a functional local pilot build, not a production-ready deployment. The automated tests cover round publication, participant visibility, team leadership, institution administration, document-overlap review, and reminder scheduling. The overlap scan only compares text within one event and creates a human-review signal; it does not establish plagiarism. Pitch analysis extracts quoted claims, but it does not perform computer-vision feature verification or external originality research. Production still needs deployment, durable schema migrations, monitoring, load/security review, and a managed database and object store. Live Google sign-in needs OAuth client credentials; OTP and outbound email need SMTP credentials. AI scoring, OCR, embeddings, transcription, and question generation need an OpenAI API key and the relevant participant consent. Put credentials only in backend/.env, never in browser code.

### Enable Google sign-in

Create a **Web application** OAuth client in Google Cloud Console. Add the exact local origin and callback URL printed by backend/start.ps1 to the OAuth client's authorized origins and redirect URIs. Put the client ID and client secret in backend/.env as GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, then restart JudgeX. You can pin a stable port by setting $env:JUDGEX_PORT=8000 before starting the backend. Never paste the client secret into the browser or chat.

Use a modern browser with JavaScript enabled. Event, account, team, rubric, submission, and document data are stored by the local API.
