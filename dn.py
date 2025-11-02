from werkzeug.security import generate_password_hash
from app import app, db
from models import User

# --------------------------------------------
# 🔹 Create a new user manually
# --------------------------------------------
def register_user(username, password, email, phone, role="user"):
    with app.app_context():
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            print("❌ User already exists with that username or email.")
            return

        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            password=hashed_password,
            email=email,
            phone=phone,
            role=role,
        )

        db.session.add(new_user)
        db.session.commit()
        print(f"✅ User '{username}' registered successfully as '{role}'!")


# --------------------------------------------
# 🔹 Example usage
# --------------------------------------------
if __name__ == "__main__":
    username = input("Enter username: ")
    password = input("Enter password: ")
    email = input("Enter email: ")
    phone = input("Enter phone number: ")
    role = input("Enter role (admin/user): ") or "user"

    register_user(username, password, email, phone, role)
