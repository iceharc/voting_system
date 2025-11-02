from flask import Flask,send_from_directory,session
from flask_login import LoginManager
from models import User, db
from datetime import datetime, timedelta
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
import os
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize DB
db.init_app(app)

# Setup login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@admin_bp.before_request
def make_session_permanent():
    session.permanent = True
    session.modified = True
    # Keeps session active for 6 hours
    admin_bp.permanent_session_lifetime = timedelta(hours=6)










# Register blueprints
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)

# ✅ Create tables automatically if missing
with app.app_context():
    db.create_all()
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )
if __name__ == '__main__':
    app.run(debug=True)
