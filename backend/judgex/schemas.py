from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, StringConstraints
from typing_extensions import Annotated

Role = Literal["organizer", "judge", "participant", "mentor", "viewer", "super_admin"]


class UserCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=10, max_length=128)]
    institution_name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=2, max_length=180)] = None


class InstitutionCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=180)]


class AdminUserUpdate(BaseModel):
    role: Literal["organizer", "judge", "participant", "mentor", "viewer"]
    institution_id: str | None = None
    is_active: bool = True


class ReminderCreate(BaseModel):
    audience: Literal["participants", "judges", "all"] = "participants"
    subject: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=240)]
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=5000)]
    scheduled_at: datetime


class UserRead(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    institution_id: str | None
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OTPRequest(BaseModel):
    email: EmailStr
    purpose: Literal["login", "password_reset"] = "login"


class OTPLogin(BaseModel):
    email: EmailStr
    code: Annotated[str, StringConstraints(pattern=r"^\d{6}$")]


class PasswordResetComplete(OTPLogin):
    new_password: Annotated[str, StringConstraints(min_length=10, max_length=128)]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class TrackCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
    description: str = ""


class TrackRead(BaseModel):
    id: str
    name: str
    description: str
    model_config = ConfigDict(from_attributes=True)


class HackathonCreate(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
    description: str = ""
    timezone: str = "UTC"
    start_date: datetime | None = None
    end_date: datetime | None = None
    registration_deadline: datetime | None = None
    submission_deadline: datetime | None = None
    team_size_min: int = Field(default=1, ge=1, le=20)
    team_size_max: int = Field(default=4, ge=1, le=20)
    pitch_duration_minutes: int = Field(default=5, ge=3, le=7)
    allow_incomplete_submissions: bool = False
    required_documents: list[Literal["prd", "architecture", "slides", "screenshot", "demo_video", "other"]] = Field(default_factory=list, max_length=10)
    tracks: list[TrackCreate] = Field(default_factory=list, max_length=30)


class HackathonUpdate(BaseModel):
    title: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)] = None
    description: str | None = None
    timezone: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    registration_deadline: datetime | None = None
    submission_deadline: datetime | None = None
    team_size_min: int | None = Field(default=None, ge=1, le=20)
    team_size_max: int | None = Field(default=None, ge=1, le=20)
    pitch_duration_minutes: int | None = Field(default=None, ge=3, le=7)
    allow_incomplete_submissions: bool | None = None
    required_documents: list[Literal["prd", "architecture", "slides", "screenshot", "demo_video", "other"]] | None = Field(default=None, max_length=10)


class HackathonStatusUpdate(BaseModel):
    status: Literal["draft", "registration_open", "live", "judging", "completed", "published"]
    round_number: int = Field(default=1, ge=1, le=10)


class HackathonRead(BaseModel):
    id: str
    organizer_id: str
    institution_id: str | None
    title: str
    description: str
    timezone: str
    start_date: datetime | None
    end_date: datetime | None
    registration_deadline: datetime | None
    submission_deadline: datetime | None
    team_size_min: int
    team_size_max: int
    pitch_duration_minutes: int
    allow_incomplete_submissions: bool
    required_documents: list[str] = []
    status: str
    published_rounds: list[int] = []
    created_at: datetime
    tracks: list[TrackRead] = []
    model_config = ConfigDict(from_attributes=True)


class TeamCreate(BaseModel):
    hackathon_id: str
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=140)]


class TeamJoin(BaseModel):
    join_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=6, max_length=12)]


class TeamMemberRoleUpdate(BaseModel):
    role: Literal["leader", "member"]


class MemberRead(BaseModel):
    id: str
    name: str
    role: str


class TeamRead(BaseModel):
    id: str
    hackathon_id: str
    name: str
    join_code: str
    status: str
    members: list[MemberRead]
    model_config = ConfigDict(from_attributes=True)


class SubmissionCreate(BaseModel):
    team_id: str
    track_id: str | None = None
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
    problem_statement: str = ""
    solution_summary: str = ""
    target_users: str = ""
    tech_stack: str = ""
    repo_url: str = ""
    live_url: str = ""
    demo_video_url: str = ""


class SubmissionUpdate(BaseModel):
    track_id: str | None = None
    title: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)] = None
    problem_statement: str | None = None
    solution_summary: str | None = None
    target_users: str | None = None
    tech_stack: str | None = None
    repo_url: str | None = None
    live_url: str | None = None
    demo_video_url: str | None = None


class SubmissionStatusUpdate(BaseModel):
    status: Literal["draft", "submitted"]


class DocumentRead(BaseModel):
    id: str
    kind: str
    filename: str
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SubmissionRead(BaseModel):
    id: str
    team_id: str
    team_name: str = ""
    track_id: str | None
    track_name: str = ""
    title: str
    problem_statement: str
    solution_summary: str
    target_users: str
    tech_stack: str
    repo_url: str
    live_url: str
    demo_video_url: str
    status: str
    repo_check_status: str
    live_check_status: str
    demo_check_status: str
    submitted_at: datetime | None
    ai_processing_consent_at: datetime | None
    updated_at: datetime
    documents: list[DocumentRead] = []
    model_config = ConfigDict(from_attributes=True)


class PitchConsent(BaseModel):
    recording_consent: bool
    ai_processing_consent: bool


class PitchSessionRead(BaseModel):
    id: str
    submission_id: str
    duration_seconds: int
    transcript: str
    claims: list[dict] = []
    demo_signals: dict = {}
    transcription_status: str
    recording_consent_at: datetime
    ai_processing_consent_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EvidenceChunkRead(BaseModel):
    id: str
    source_type: str
    source_ref: str
    excerpt: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AIProcessingConsent(BaseModel):
    consent: bool


class EvidenceQuery(BaseModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    limit: int = Field(default=5, ge=1, le=10)


class RubricCriterionInput(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=140)]
    description: str = ""
    weight: float = Field(gt=0, le=100)
    max_score: int = Field(default=10, ge=1, le=100)
    evidence_requirements: str = ""
    ai_prompt: str = ""


class RubricCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)] = "Judging rubric"
    round_number: int = Field(default=1, ge=1, le=10)
    criteria: list[RubricCriterionInput] = Field(min_length=1, max_length=30)


class JudgeAssignmentCreate(BaseModel):
    judge_emails: list[EmailStr] = Field(min_length=1, max_length=100)


class CriterionScoreOverride(BaseModel):
    criterion_score_id: str
    judge_score: float = Field(ge=0, le=100)
    comment: str = ""


class JudgeReviewSubmit(BaseModel):
    comments: str = ""
    criterion_scores: list[CriterionScoreOverride] = Field(default_factory=list, max_length=30)


class ReviewFlagCreate(BaseModel):
    kind: Literal["clarification", "discussion", "integrity"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=4000)]


class ReviewFlagRespond(BaseModel):
    response: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=4000)]


class AppealCreate(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=4000)]


class AppealResolve(BaseModel):
    resolution: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=4000)]
    status: Literal["upheld", "adjusted", "denied"]


class ProfileUpdate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class PrivacyRequestCreate(BaseModel):
    request_type: Literal["account_deletion"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""


class PrivacyRequestReview(BaseModel):
    status: Literal["completed", "denied"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)]
