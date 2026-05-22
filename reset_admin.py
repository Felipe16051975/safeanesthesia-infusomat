import os
import sys

# Ensure we are in the project root
target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(target_dir)

# Add project root to PYTHONPATH
sys.path.append(target_dir)

from app import app, db, bcrypt
from models import User

with app.app_context():
    admin = User.query.filter_by(username='Administrador').first()
    if admin:
        admin.password_hash = bcrypt.generate_password_hash('PartenVet2026!').decode('utf-8')
        db.session.commit()
        print('Admin password reset successfully.')
    else:
        print('Admin user not found.')
