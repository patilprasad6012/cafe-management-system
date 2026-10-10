"""
Create a Chef account in the configured King Cafe database.

Run this script from the project root in an environment configured to use
the intended Railway database:
    python create_chef.py
"""
from getpass import getpass

from app import create_app, db, bcrypt
from app.models.models import User


def main():
    app = create_app()
    with app.app_context():
        print("=== King Cafe: Create Chef Account ===")
        name = input("Chef name: ").strip()
        email = input("Chef email: ").strip().lower()
        mobile = input("Chef mobile: ").strip()
        password = getpass("Choose a new Chef password: ")
        confirm = getpass("Confirm Chef password: ")

        if not all((name, email, mobile, password)):
            print("ERROR: All fields are required.")
            return
        if password != confirm:
            print("ERROR: Passwords do not match.")
            return
        if len(password) < 10:
            print("ERROR: Use a password with at least 10 characters.")
            return

        existing_email = db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none()
        if existing_email:
            print("ERROR: This email is already registered. No changes made.")
            return

        existing_mobile = db.session.execute(
            db.select(User).filter_by(mobile=mobile)
        ).scalar_one_or_none()
        if existing_mobile:
            print("ERROR: This mobile number is already registered. No changes made.")
            return

        chef = User(
            name=name,
            email=email,
            mobile=mobile,
            role="chef",
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        )
        try:
            db.session.add(chef)
            db.session.commit()
        except Exception:
            db.session.rollback()
            print("ERROR: Account creation failed. Review the console error.")
            raise

        print(f"SUCCESS: Chef account created for {chef.email}.")
        print("You can now sign in through the King Cafe login page.")


if __name__ == "__main__":
    main()
