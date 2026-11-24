from datetime import datetime, timezone
from uuid import uuid4
import json

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def uid() -> str:
    return str(uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Institution(Base):
    __tablename__ = "institutions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    users: Mapped[list["User"]] = relationship(back_populates="institution")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("auth_provider", "auth_subject", name="uq_auth_provider_subject"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    auth_provider: Mapped[str] = mapped_column(String(30), default="password", server_default="password")
    auth_subject: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    role: Mapped[str] = mapped_column(String(30), default="participant", index=True)
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    institution: Mapped[Institution | None] = relationship(back_populates="users")
    memberships: Mapped[list["TeamMember"]] = relationship(back_populates="user")


class Hackathon(Base):
    __tablename__ = "hackathons"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organizer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    timezone: Mapped[str] = mapped_column(String(80), default="UTC")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    team_size_min: Mapped[int] = mapped_column(Integer, default=1)
    team_size_max: Mapped[int] = mapped_column(Integer, default=4)
    pitch_duration_minutes: Mapped[int] = mapped_column(Integer, default=5)
    allow_incomplete_submissions: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    required_documents_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    published_rounds_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    tracks: Mapped[list["Track"]] = relationship(back_populates="hackathon", cascade="all, delete-orphan")
    teams: Mapped[list["Team"]] = relationship(back_populates="hackathon", cascade="all, delete-orphan")

    @property
    def required_documents(self) -> list[str]:
        try:
            return json.loads(self.required_documents_json or "[]")
        except json.JSONDecodeError:
            return []

    @property
    def published_rounds(self) -> list[int]:
        try:
            return json.loads(self.published_rounds_json or "[]")
        except json.JSONDecodeError:
            return []


class Track(Base):
    __tablename__ = "tracks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    hackathon_id: Mapped[str] = mapped_column(ForeignKey("hackathons.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    hackathon: Mapped[Hackathon] = relationship(back_populates="tracks")


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    hackathon_id: Mapped[str] = mapped_column(ForeignKey("hackathons.id"), index=True)
    name: Mapped[str] = mapped_column(String(140))
    join_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, default=lambda: uuid4().hex[:8].upper())
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    hackathon: Mapped[Hackathon] = relationship(back_populates="teams")
    members: Mapped[list["TeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_user"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(30), default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    team: Mapped[Team] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    track_id: Mapped[str | None] = mapped_column(ForeignKey("tracks.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    problem_statement: Mapped[str] = mapped_column(Text, default="")
    solution_summary: Mapped[str] = mapped_column(Text, default="")
    target_users: Mapped[str] = mapped_column(Text, default="")
    tech_stack: Mapped[str] = mapped_column(Text, default="")
    repo_url: Mapped[str] = mapped_column(String(1000), default="")
    live_url: Mapped[str] = mapped_column(String(1000), default="")
    demo_video_url: Mapped[str] = mapped_column(String(1000), default="", server_default="")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    repo_check_status: Mapped[str] = mapped_column(String(30), default="not_checked")
    live_check_status: Mapped[str] = mapped_column(String(30), default="not_checked")
    demo_check_status: Mapped[str] = mapped_column(String(30), default="not_checked", server_default="not_checked")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_processing_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    team: Mapped[Team] = relationship(back_populates="submissions")
    track: Mapped[Track | None] = relationship()
    documents: Mapped[list["Document"]] = relationship(back_populates="submission", cascade="all, delete-orphan")

    @property
    def team_name(self) -> str:
        return self.team.name if self.team else ""

    @property
    def track_name(self) -> str:
        return self.track.name if self.track else ""


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    submission: Mapped[Submission] = relationship(back_populates="documents")


class PitchSession(Base):
    __tablename__ = "pitch_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), index=True)
    recording_key: Mapped[str] = mapped_column(String(500), default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    transcript: Mapped[str] = mapped_column(Text, default="")
    claims_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    demo_signals_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    transcription_status: Mapped[str] = mapped_column(String(30), default="awaiting_upload")
    recording_consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ai_processing_consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    @property
    def claims(self) -> list[dict]:
        try:
            result = json.loads(self.claims_json or "[]")
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            return []

    @property
    def demo_signals(self) -> dict:
        try:
            result = json.loads(self.demo_signals_json or "{}")
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError:
            return {}


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"
    __table_args__ = (UniqueConstraint("submission_id", "source_type", "source_ref", "ordinal", name="uq_evidence_source_chunk"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_ref: Mapped[str] = mapped_column(String(500), default="")
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    excerpt: Mapped[str] = mapped_column(Text)
    embedding_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Rubric(Base):
    __tablename__ = "rubrics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    hackathon_id: Mapped[str] = mapped_column(ForeignKey("hackathons.id"), index=True)
    round_number: Mapped[int] = mapped_column(Integer, default=1, index=True)
    name: Mapped[str] = mapped_column(String(160), default="Default judging rubric")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    rubric_id: Mapped[str] = mapped_column(ForeignKey("rubrics.id"), index=True)
    name: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text, default="")
    weight: Mapped[float] = mapped_column(Float)
    max_score: Mapped[int] = mapped_column(Integer, default=10)
    evidence_requirements: Mapped[str] = mapped_column(Text, default="")
    ai_prompt: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)


class JudgeAssignment(Base):
    __tablename__ = "judge_assignments"
    __table_args__ = (UniqueConstraint("hackathon_id", "judge_id", name="uq_event_judge"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    hackathon_id: Mapped[str] = mapped_column(ForeignKey("hackathons.id"), index=True)
    judge_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Scorecard(Base):
    __tablename__ = "scorecards"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), index=True)
    rubric_id: Mapped[str] = mapped_column(ForeignKey("rubrics.id"), index=True)
    ai_score: Mapped[float] = mapped_column(Float, default=0)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="needs_review", index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CriterionScore(Base):
    __tablename__ = "criterion_scores"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    scorecard_id: Mapped[str] = mapped_column(ForeignKey("scorecards.id"), index=True)
    criterion_id: Mapped[str] = mapped_column(ForeignKey("rubric_criteria.id"), index=True)
    ai_score: Mapped[float] = mapped_column(Float)
    judge_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rationale: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    strengths_json: Mapped[str] = mapped_column(Text, default="[]")
    weaknesses_json: Mapped[str] = mapped_column(Text, default="[]")
    human_comment: Mapped[str] = mapped_column(Text, default="")


class EvidenceCitation(Base):
    __tablename__ = "evidence_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    criterion_score_id: Mapped[str] = mapped_column(ForeignKey("criterion_scores.id"), index=True)
    chunk_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_chunks.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40))
    source_ref: Mapped[str] = mapped_column(String(500), default="")
    excerpt: Mapped[str] = mapped_column(Text)


class JudgeReview(Base):
    __tablename__ = "judge_reviews"
    __table_args__ = (UniqueConstraint("scorecard_id", "judge_id", name="uq_scorecard_judge"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    scorecard_id: Mapped[str] = mapped_column(ForeignKey("scorecards.id"), index=True)
    judge_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    comments: Mapped[str] = mapped_column(Text, default="")
    final_score: Mapped[float] = mapped_column(Float)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ReviewFlag(Base):
    __tablename__ = "review_flags"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    note: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    response: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class Appeal(Base):
    __tablename__ = "appeals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    scorecard_id: Mapped[str] = mapped_column(ForeignKey("scorecards.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="submitted")
    resolution: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    request_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserNotification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    subject: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    failure_detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScheduledReminder(Base):
    __tablename__ = "scheduled_reminders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    hackathon_id: Mapped[str] = mapped_column(ForeignKey("hackathons.id"), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    audience: Mapped[str] = mapped_column(String(20), default="participants")
    subject: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", index=True)
    failure_detail: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class OTPChallenge(Base):
    __tablename__ = "otp_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(30), index=True)
    code_hash: Mapped[str] = mapped_column(String(255))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
