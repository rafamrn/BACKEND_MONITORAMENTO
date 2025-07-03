from database import Base, engine
from modelos import Base

Base.metadata.create_all(bind=engine)
