from app import create_app, db

app = create_app()

with app.app_context():
    from app import models
    db.create_all()
    print("DATABASE TABLES CREATED SUCCESSFULLY")
