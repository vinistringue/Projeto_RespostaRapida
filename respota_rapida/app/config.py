from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Carrega variáveis do .env
load_dotenv()

# Lê a variável DB_URL do .env
DB_URL = os.getenv("DB_URL")

# Cria o engine do SQLAlchemy
engine = create_engine(DB_URL, echo=True)

# Cria a sessão para interagir com o banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()
