from fastapi import FastAPI
from .config import Base, engine
import uvicorn

app = FastAPI()

# Cria as tabelas no banco (executar uma vez)
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"msg": "API Resposta Rápida"}

# Para rodar com: uvicorn app.main:app --reload
