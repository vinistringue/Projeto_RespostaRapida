import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.models import Base

# Carrega as variáveis do .env
load_dotenv()

# Lê as variáveis individualmente
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Validação das variáveis essenciais
missing_vars = [var for var in ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"] if os.getenv(var) is None]
if missing_vars:
    raise ValueError(f"As seguintes variáveis não foram encontradas no arquivo .env: {', '.join(missing_vars)}")

# Monta a URL de conexão manualmente
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Cria a engine com echo para debug
engine = create_engine(DATABASE_URL, echo=True)

# Cria o factory para sessões do banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria as tabelas no banco a partir dos models
def init_db():
    Base.metadata.create_all(bind=engine)

# Fornece a sessão de banco via dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
