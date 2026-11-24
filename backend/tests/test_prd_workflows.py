import os
import asyncio
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select

DB_PATH = Path(tempfile.gettempdir()) / f"judgex-tests-{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "test-only-secret-not-for-production"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from judgex.config import Settings, settings
from judgex.database import Base, SessionLocal, engine, normalize_database_url
from judgex.main import app, dispatch_due_reminders
from judgex.models import (Document, Hackathon, PitchSession, Rubric, RubricCriterion, Scorecard, Submission, Team,
                           TeamMember, User)
from judgex.security import create_access_token


class PRDWorkflowTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        DB_PATH.unlink(missing_ok=True)

    def add_user(self, name, email, role):
        user = User(name=name, email=email, password_hash="test", role=role)
        return user

    def test_render_database_url_google_callback_and_initial_organizer(self):
        self.assertEqual(normalize_database_url("postgres://u:p@db.example/judgex"),
            "postgresql+psycopg://u:p@db.example/judgex")
        self.assertEqual(normalize_database_url("postgresql://u:p@db.example/judgex"),
            "postgresql+psycopg://u:p@db.example/judgex")
        self.assertEqual(Settings(public_base_url="https://judge.example").effective_google_redirect_uri,
            "https://judge.example/api/v1/auth/google/callback")

        original = (settings.bootstrap_organizer_name, settings.bootstrap_organizer_email,
            settings.bootstrap_organizer_institution, settings.bootstrap_organizer_password)
        try:
            settings.bootstrap_organizer_name = "First Organizer"
            settings.bootstrap_organizer_email = "owner@example.test"
            settings.bootstrap_organizer_institution = "Launch Institution"
            settings.bootstrap_organizer_password = "long-test-password"
            from judgex.main import provision_initial_organizer
            provision_initial_organizer()
            provision_initial_organizer()
            with SessionLocal() as db:
                account = db.scalar(select(User).where(User.email == "owner@example.test"))
                self.assertIsNotNone(account)
                self.assertEqual(account.role, "organizer")
                self.assertEqual(account.institution.name, "Launch Institution")
                self.assertEqual(len(db.scalars(select(User).where(User.role == "organizer")).all()), 1)
        finally:
            (settings.bootstrap_organizer_name, settings.bootstrap_organizer_email,
                settings.bootstrap_organizer_institution, settings.bootstrap_organizer_password) = original

    def test_rounds_publish_and_become_visible_independently(self):
        with SessionLocal() as db:
            organizer = self.add_user("Organizer", "organizer@example.test", "organizer")
            participant = self.add_user("Participant", "participant@example.test", "participant")
            db.add_all([organizer, participant])
            db.flush()
            event = Hackathon(organizer_id=organizer.id, title="Round Event", status="completed")
            db.add(event)
            db.flush()
            team = Team(hackathon_id=event.id, name="Team One")
            db.add(team)
            db.flush()
            db.add(TeamMember(team_id=team.id, user_id=participant.id, role="leader"))
            submission = Submission(team_id=team.id, title="Project One", status="submitted")
            db.add(submission)
            db.flush()
            pitch = PitchSession(submission_id=submission.id, recording_consent_at=datetime.now(timezone.utc),
                ai_processing_consent_at=datetime.now(timezone.utc), claims_json='[{"kind":"feature","text":"Image upload","quote":"Users can upload an image."}]',
                demo_signals_json='{"screen_share_detected":true,"screen_share_seconds":42}')
            db.add(pitch)
            for round_number in (1, 2):
                rubric = Rubric(hackathon_id=event.id, round_number=round_number, name=f"Round {round_number}", version=1)
                db.add(rubric)
                db.flush()
                db.add(RubricCriterion(rubric_id=rubric.id, name="Impact", weight=100, max_score=10))
                db.add(Scorecard(submission_id=submission.id, rubric_id=rubric.id, final_score=80 + round_number,
                    status="approved" if round_number == 1 else "needs_review"))
            db.commit()
            event_id, submission_id = event.id, submission.id
            organizer_id, participant_id = organizer.id, participant.id

        organizer_headers = {"Authorization": f"Bearer {create_access_token(organizer_id)}"}
        participant_headers = {"Authorization": f"Bearer {create_access_token(participant_id)}"}
        response = self.client.patch(f"/api/v1/hackathons/{event_id}/status", headers=organizer_headers,
                                     json={"status": "published", "round_number": 1})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["published_rounds"], [1])
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(self.client.get(f"/api/v1/hackathons/{event_id}/leaderboard?round_number=1").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/hackathons/{event_id}/leaderboard?round_number=2").status_code, 404)
        cards = self.client.get(f"/api/v1/submissions/{submission_id}/scorecards", headers=participant_headers)
        self.assertEqual([card["round_number"] for card in cards.json()], [1])
        dashboard = self.client.get(f"/api/v1/hackathons/{event_id}/dashboard", headers=participant_headers)
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        self.assertEqual(dashboard.json()["approved_count"], 1)
        pitch_response = self.client.get(f"/api/v1/submissions/{submission_id}/pitch-sessions", headers=participant_headers)
        self.assertEqual(pitch_response.json()[0]["claims"][0]["text"], "Image upload")
        self.assertEqual(pitch_response.json()[0]["demo_signals"]["screen_share_seconds"], 42)

        response = self.client.patch(f"/api/v1/hackathons/{event_id}/status", headers=organizer_headers,
                                     json={"status": "published", "round_number": 2})
        self.assertEqual(response.status_code, 409)
        with SessionLocal() as db:
            round_two_rubric = db.scalar(select(Rubric.id).where(Rubric.hackathon_id == event_id, Rubric.round_number == 2))
            pending = db.scalar(select(Scorecard).where(Scorecard.submission_id == submission_id, Scorecard.rubric_id == round_two_rubric))
            pending.status = "approved"
            db.commit()
        response = self.client.patch(f"/api/v1/hackathons/{event_id}/status", headers=organizer_headers,
                                     json={"status": "published", "round_number": 2})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["published_rounds"], [1, 2])
        self.assertEqual(response.json()["status"], "published")
        cards = self.client.get(f"/api/v1/submissions/{submission_id}/scorecards", headers=participant_headers)
        self.assertEqual({card["round_number"] for card in cards.json()}, {1, 2})

    def test_admin_team_and_scheduled_reminder_flows(self):
        with SessionLocal() as db:
            admin = self.add_user("Admin", "admin@example.test", "super_admin")
            organizer = self.add_user("Organizer", "org@example.test", "organizer")
            leader = self.add_user("Leader", "leader@example.test", "participant")
            member = self.add_user("Member", "member@example.test", "participant")
            db.add_all([admin, organizer, leader, member])
            db.flush()
            event = Hackathon(organizer_id=organizer.id, title="Team Event", status="registration_open")
            db.add(event)
            db.commit()
            ids = {account.email: account.id for account in [admin, organizer, leader, member]}
            event_id = event.id

        auth = {email: {"Authorization": f"Bearer {create_access_token(user_id)}"} for email, user_id in ids.items()}
        institution = self.client.post("/api/v1/admin/institutions", headers=auth["admin@example.test"], json={"name": "North College"})
        self.assertEqual(institution.status_code, 201, institution.text)
        update = self.client.patch(f"/api/v1/admin/users/{ids['member@example.test']}", headers=auth["admin@example.test"],
                                   json={"role": "judge", "institution_id": institution.json()["id"], "is_active": True})
        self.assertEqual(update.status_code, 200, update.text)
        self.assertEqual(self.client.patch(f"/api/v1/admin/users/{ids['admin@example.test']}", headers=auth["admin@example.test"],
                                           json={"role": "organizer", "institution_id": None, "is_active": True}).status_code, 404)

        # Keep the test member a participant so the invite-code join is permitted.
        with SessionLocal() as db:
            db.get(User, ids["member@example.test"]).role = "participant"
            db.commit()
        team = self.client.post("/api/v1/teams", headers=auth["leader@example.test"], json={"hackathon_id": event_id, "name": "Builders"})
        self.assertEqual(team.status_code, 201, team.text)
        team_id, join_code = team.json()["id"], team.json()["join_code"]
        self.assertEqual(self.client.post("/api/v1/teams/join", headers=auth["member@example.test"], json={"join_code": join_code}).status_code, 200)
        self.assertEqual(self.client.patch(f"/api/v1/teams/{team_id}/members/{ids['member@example.test']}", headers=auth["leader@example.test"],
                                           json={"role": "leader"}).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/teams/{team_id}/members/{ids['leader@example.test']}", headers=auth["member@example.test"]).status_code, 204)

        reminder = self.client.post(f"/api/v1/hackathons/{event_id}/reminders", headers=auth["org@example.test"], json={
            "audience": "all", "subject": "Deadline reminder", "body": "Your project submission deadline is approaching.",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()})
        self.assertEqual(reminder.status_code, 201, reminder.text)
        self.assertEqual(self.client.get(f"/api/v1/hackathons/{event_id}/reminders", headers=auth["org@example.test"]).json()[0]["status"], "scheduled")
        with SessionLocal() as db:
            from judgex.models import ScheduledReminder
            due = db.get(ScheduledReminder, reminder.json()["id"])
            due.scheduled_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        asyncio.run(dispatch_due_reminders())
        self.assertEqual(self.client.get(f"/api/v1/hackathons/{event_id}/reminders", headers=auth["org@example.test"]).json()[0]["status"], "sent")
        notifications = self.client.get("/api/v1/notifications", headers=auth["member@example.test"]).json()
        self.assertTrue(any(item["subject"] == "Deadline reminder" for item in notifications))

    def test_document_overlap_is_only_a_human_review_signal(self):
        shared_text = " ".join(f"event platform project judging evidence participant feedback transparency innovation collaboration requirementitem{index} details" for index in range(30))
        with SessionLocal() as db:
            organizer = self.add_user("Organizer", "overlap-org@example.test", "organizer")
            db.add(organizer)
            db.flush()
            event = Hackathon(organizer_id=organizer.id, title="Overlap Event", status="judging")
            db.add(event)
            db.flush()
            ids = []
            for index in range(2):
                team = Team(hackathon_id=event.id, name=f"Team {index}")
                db.add(team)
                db.flush()
                submission = Submission(team_id=team.id, title=f"Project {index}", status="submitted")
                db.add(submission)
                db.flush()
                db.add(Document(submission_id=submission.id, kind="prd", filename=f"project-{index}.txt",
                    storage_key=f"unused/project-{index}.txt", extracted_text=shared_text))
                ids.append(submission.id)
            db.commit()
            organizer_id = organizer.id
        headers = {"Authorization": f"Bearer {create_access_token(organizer_id)}"}
        response = self.client.post(f"/api/v1/submissions/{ids[0]}/integrity-check", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["review_required"])
        self.assertIn("not a plagiarism finding", response.json()["message"])
        self.assertEqual(response.json()["findings"][0]["submission_id"], ids[1])
        flags = self.client.get(f"/api/v1/submissions/{ids[0]}/review-flags", headers=headers)
        self.assertEqual(flags.status_code, 200)
        self.assertIn("Possible documentation overlap", flags.json()[0]["note"])


if __name__ == "__main__":
    unittest.main()
