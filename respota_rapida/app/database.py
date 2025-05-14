import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv  # Importando a função load_dotenv
from app.models import Base

# Carregando as variáveis de ambiente do arquivo .env
load_dotenv()

# Carregue a URL do banco de dados diretamente do .env
DATABASE_URL = os.getenv("DB_URL")

# Verifique se a URL do banco de dados foi carregada corretamente
if DATABASE_URL is None:
    raise ValueError("A variável DB_URL não foi encontrada no arquivo .env")

# Criação da engine do banco de dados
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Função para inicializar o banco de dados
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()