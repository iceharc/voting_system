from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    u = User(username='testuser5', password=generate_password_hash('1234'), role='user')
    db.session.add(u)
    db.session.commit()
    print("Test user created.")