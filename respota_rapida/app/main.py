# app/main.py

from fastapi import FastAPI
from app.database import init_db
from app.routers import connect  # import da rota conect

app = FastAPI(title="Resposta Rápida")

# Cria as tabelas no banco ao iniciar
init_db()

# Inclui as rotas
app.include_router(connect.router, prefix="/api", tags=["Jogadores"])

@app.get("/")
def read_root():
    return {"message": "API do jogo Resposta Rápida ativa!"}
