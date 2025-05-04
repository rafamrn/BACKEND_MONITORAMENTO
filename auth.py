# backend_v2/auth.py
from jose import jwt, JWTError

SECRET_KEY = "sua_chave_secreta"  # Substitua por uma chave forte e segura
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    # Não inclui expiração — o token nunca expira
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
