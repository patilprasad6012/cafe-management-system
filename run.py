from app import create_app, db
import os

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created/verified successfully.")
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1']
    app.run(debug=debug, host='0.0.0.0', port=5000)
