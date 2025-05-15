from fastapi import FastAPI
from app.database import init_db
from app.routers import connect, question, tournament  # importa os routers

app = FastAPI(title="Resposta Rápida", version="1.0.0")


# Inicializa o banco de dados
init_db()

# Inclui as rotas da aplicação
app.include_router(connect.router, prefix="/api", tags=["Jogadores"])
app.include_router(question.router, prefix="/api", tags=["Perguntas"])
app.include_router(tournament.router, prefix="/api", tags=["Torneio"])

# Rota raiz
@app.get("/")
def read_root():
    return {"message": "API do jogo Resposta Rápida ativa!"}
