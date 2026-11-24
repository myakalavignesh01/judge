"""Create an organizer account interactively: python -m judgex.create_admin."""
import argparse
from getpass import getpass

from sqlalchemy import select

from .database import Base, SessionLocal, engine, upgrade_legacy_schema
from .models import Institution, User
from .security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a JudgeX event organizer account")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--institution", required=True)
    parser.add_argument("--role", choices=["organizer", "judge", "mentor", "viewer", "super_admin"], default="organizer")
    args = parser.parse_args()
    password = getpass("Password (10+ characters): ")
    if len(password) < 10:
        raise SystemExit("Password must be at least 10 characters.")
    Base.metadata.create_all(bind=engine)
    upgrade_legacy_schema()
    with SessionLocal() as db:
        email = args.email.strip().lower()
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("That email already has an account.")
        institution = db.scalar(select(Institution).where(Institution.name == args.institution.strip()))
        if not institution:
            institution = Institution(name=args.institution.strip())
            db.add(institution)
            db.flush()
        user = User(name=args.name.strip(), email=email, password_hash=hash_password(password), role=args.role, institution_id=institution.id)
        db.add(user)
        db.commit()
    print(f"{args.role.capitalize()} account created for {email}. Sign in from the JudgeX page.")


if __name__ == "__main__":
    main()
