from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session
from flask_bcrypt import Bcrypt
from config import Config

db = SQLAlchemy()
migrate = Migrate()
session = Session()
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    session.init_app(app)
    bcrypt.init_app(app)

    # Ensure required directories exist
    import os
    os.makedirs(os.path.join(app.root_path, 'static', 'uploads', 'food_images'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static', 'uploads', 'qrcodes'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, '..', 'flask_session'), exist_ok=True)

    # Register blueprints here
    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.admin import admin_bp
    from app.routes.chef import chef_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.routes.table import table_bp
    from app.routes.menu import menu_bp
    app.register_blueprint(table_bp, url_prefix='/admin/tables')
    app.register_blueprint(menu_bp, url_prefix='/admin/menu')
    
    app.register_blueprint(chef_bp, url_prefix='/chef')

    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    return app
