from app import app
from models import db,Manager
from werkzeug.security import generate_password_hash

with app.app_context():
    if not Manager.query.all():
        
        manager1 = Manager(name="manager1",email="manager1@gmail.com",password_hash=generate_password_hash("manager123"))
        manager2 = Manager(name="manager2",email="manager2@gmail.com",password_hash=generate_password_hash("manager231"))
        
        db.session.add_all([manager1,manager2])
        db.session.commit()
        print('manager seeded')
