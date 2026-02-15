import os

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate

from models import db, Manager, Technician, Tenant
from routes import register_routes


def _normalize_database_url(database_url: str) -> str:
    """Normalize provider URLs for SQLAlchemy."""
    if database_url.startswith('postgres://'):
        return database_url.replace('postgres://', 'postgresql://', 1)
    return database_url


app = Flask(__name__, static_folder='statics', static_url_path='/statics')

# app configuration
database_url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or 'sqlite:///database.db'
app.config['SQLALCHEMY_DATABASE_URI'] = _normalize_database_url(database_url)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'FixNext')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'statics', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Flask-Login configuration
loginmanager = LoginManager()
loginmanager.init_app(app)
loginmanager.login_view = 'login'

# database initialization
db.init_app(app)
migrate = Migrate(app, db)
with app.app_context():
    db.create_all()


@loginmanager.user_loader
def load_user(user_id):
    """Load user with role-aware IDs to prevent cross-table ID collisions."""
    if not user_id:
        return None

    if ':' in user_id:
        role, raw_id = user_id.split(':', 1)
        if not raw_id.isdigit():
            return None

        lookup = {
            'manager': Manager,
            'tenant': Tenant,
            'technician': Technician,
        }
        model = lookup.get(role)
        if not model:
            return None

        user = db.session.get(model, int(raw_id))
        return user if user and user.is_active else None

    if user_id.isdigit():
        raw_id = int(user_id)
        for model in (Manager, Tenant, Technician):
            user = db.session.get(model, raw_id)
            if user and user.is_active:
                return user

    return None


register_routes(app)


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', '5000')),
        debug=os.getenv('FLASK_DEBUG', '0') == '1',
    )
