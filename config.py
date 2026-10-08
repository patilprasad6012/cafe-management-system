import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'kingcafe_dev_secret_key_change_in_prod'

    # Railway may provide a database URL or individual MySQL variables.
    # Keep SQLite as a zero-config fallback for local development.
    _db_url = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')
    if _db_url and _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    elif _db_url and _db_url.startswith('mysql://'):
        _db_url = _db_url.replace('mysql://', 'mysql+pymysql://', 1)

    if not _db_url:
        mysql_host = os.environ.get('MYSQLHOST') or os.environ.get('MYSQL_HOST')
        mysql_database = os.environ.get('MYSQLDATABASE') or os.environ.get('MYSQL_DATABASE')
        mysql_user = os.environ.get('MYSQLUSER') or os.environ.get('MYSQL_USER')
        mysql_password = os.environ.get('MYSQLPASSWORD') or os.environ.get('MYSQL_PASSWORD', '')
        mysql_port = os.environ.get('MYSQLPORT') or os.environ.get('MYSQL_PORT', '3306')
        if mysql_host and mysql_database and mysql_user:
            _db_url = (
                f"mysql+pymysql://{quote_plus(mysql_user)}:{quote_plus(mysql_password)}"
                f"@{mysql_host}:{mysql_port}/{quote_plus(mysql_database)}"
            )

    SQLALCHEMY_DATABASE_URI = _db_url or f"sqlite:///{os.path.join(basedir, 'kingcafe.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(basedir, 'flask_session')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

    AI_API_KEY = os.environ.get('AI_API_KEY')
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
