from jose import jwt, JWTError

SECRET_KEY = "sua_chave_secreta"  # Substitua por uma chave forte e segura
ALGORITHM = "HS256"

def create_access_token(data: dict, is_admin: bool):
    to_encode = data.copy()
    to_encode.update({"is_admin": is_admin})  # adiciona ao payload
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
    
    
