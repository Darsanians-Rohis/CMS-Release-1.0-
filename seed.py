"""
seed.py — First-run setup for ManageSpace
==========================================
Creates the initial admin user so you can log in and manage
the rest of the organization through the app itself.

Usage:
    python seed.py

Options (via environment variables or interactive prompts):
    SEED_NAME     Admin's full name
    SEED_EMAIL    Admin's email address
    SEED_PASSWORD Admin's password (min 6 chars)
"""

import os
import sys
import getpass
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Validate DATABASE_URL before importing anything Flask-related
# ---------------------------------------------------------------------------
if not os.environ.get("DATABASE_URL"):
    print("\n[ERROR] DATABASE_URL is not set in your environment or .env file.")
    print("        Please configure it before running this script.\n")
    sys.exit(1)


from app import create_app
from extensions import db, bcrypt
from models import User

app = create_app()


def _prompt(label: str, env_key: str, secret: bool = False) -> str:
    """Read from env var or fall back to interactive prompt."""
    value = os.environ.get(env_key, "").strip()
    if value:
        masked = value if not secret else "*" * len(value)
        print(f"  {label}: {masked}  (from env)")
        return value
    if secret:
        value = getpass.getpass(f"  {label}: ").strip()
    else:
        value = input(f"  {label}: ").strip()
    return value


def seed():
    with app.app_context():
        # ----------------------------------------------------------------
        # Run pending migrations so the schema is up to date
        # ----------------------------------------------------------------
        try:
            from flask_migrate import upgrade as db_upgrade
            db_upgrade()
            print("[OK] Database migrations applied.")
        except Exception as e:
            print(f"[WARN] Could not run migrations automatically: {e}")
            print("       Run `flask db upgrade` manually if needed.")

        # ----------------------------------------------------------------
        # Check if any admin already exists
        # ----------------------------------------------------------------
        existing_admin = User.query.filter_by(role="admin").first()
        if existing_admin:
            print(f"\n[INFO] An admin user already exists: {existing_admin.email}")
            confirm = input("       Create another admin anyway? [y/N]: ").strip().lower()
            if confirm != "y":
                print("       Aborted. No changes made.\n")
                sys.exit(0)

        # ----------------------------------------------------------------
        # Collect admin details
        # ----------------------------------------------------------------
        print("\n=== ManageSpace — Create First Admin ===\n")

        name = _prompt("Full name", "SEED_NAME")
        if not name:
            print("[ERROR] Name cannot be empty.")
            sys.exit(1)

        email = _prompt("Email address", "SEED_EMAIL").lower()
        if not email or "@" not in email:
            print("[ERROR] A valid email address is required.")
            sys.exit(1)

        if User.query.filter_by(email=email).first():
            print(f"[ERROR] A user with email '{email}' already exists.")
            sys.exit(1)

        password = _prompt("Password (min 6 chars)", "SEED_PASSWORD", secret=True)
        if len(password) < 6:
            print("[ERROR] Password must be at least 6 characters.")
            sys.exit(1)

        # Confirm password (skip if supplied via env)
        if not os.environ.get("SEED_PASSWORD"):
            confirm_pw = getpass.getpass("  Confirm password: ").strip()
            if password != confirm_pw:
                print("[ERROR] Passwords do not match.")
                sys.exit(1)

        # ----------------------------------------------------------------
        # Create the user
        # ----------------------------------------------------------------
        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        admin = User(
            name=name,
            email=email,
            password=hashed,
            role="admin",
            must_change_password=False,
        )

        try:
            db.session.add(admin)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Failed to create admin: {e}\n")
            sys.exit(1)

        print(f"\n[SUCCESS] Admin created!")
        print(f"          Name  : {admin.name}")
        print(f"          Email : {admin.email}")
        print(f"          Role  : {admin.role}")
        print(f"\n  Log in to the app and add your members from the dashboard.\n")


if __name__ == "__main__":
    seed()