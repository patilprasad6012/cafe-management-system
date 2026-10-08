import os
import getpass
from app import create_app, db, bcrypt
from app.models.models import User

def create_admin():
    app = create_app()
    with app.app_context():
        print("=== King Cafe Admin Setup ===")
        name = input("Enter Admin Name: ")
        email = input("Enter Admin Email: ")
        mobile = input("Enter Admin Mobile: ")
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            print("Error: That email is already registered.")
            return
            
        password = getpass.getpass("Enter Admin Password: ")
        confirm = getpass.getpass("Confirm Password: ")
        
        if password != confirm:
            print("Error: Passwords do not match.")
            return
            
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        
        admin = User(
            name=name,
            email=email,
            mobile=mobile,
            password_hash=hashed_pw,
            role='admin'
        )
        
        try:
            db.session.add(admin)
            db.session.commit()
            print(f"Success! Admin account for {email} created.")
        except Exception as e:
            db.session.rollback()
            print(f"Failed to create admin: {e}")

if __name__ == "__main__":
    create_admin()
