from sqlalchemy.orm import Session
from database import SessionLocal
from modelos import User
from utils import hash_password

def create_user(email: str, password: str):
    db: Session = SessionLocal()
    user_exists = db.query(User).filter(User.email == email).first()
    if user_exists:
        print("Usuário já existe.")
        return

    user = User(
        email=email,
        hashed_password=hash_password(password)
    )
    db.add(user)
    db.commit()
    print("Usuário criado com sucesso.")

# Substitua pelos dados desejados
create_user("contato@rms7energia.com", "rms7@RMS")