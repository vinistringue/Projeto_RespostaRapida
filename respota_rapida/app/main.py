from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import init_db, get_db
from app.models import MatchPlayer, Match
from app.schemas import MatchPlayerCreate, MatchPlayerOut, MatchOut

# Criação da instância do FastAPI
app = FastAPI()

# Inicializa as tabelas do banco de dados ao iniciar o app
init_db()

# Rota POST para criar novo registro de MatchPlayer
@app.post("/matchplay/", response_model=MatchPlayerOut)
def create_match_player(match_player: MatchPlayerCreate, db: Session = Depends(get_db)):
    db_match_player = MatchPlayer(name=match_player.name, status="waiting")  # Status inicial é "waiting"
    db.add(db_match_player)
    db.commit()
    db.refresh(db_match_player)
    return db_match_player

# Rota GET para listar todos os registros MatchPlayer
@app.get("/matchplay/", response_model=list[MatchPlayerOut])
def get_all_matchplayers(db: Session = Depends(get_db)):
    return db.query(MatchPlayer).all()

# Endpoint para conectar jogadores e criar partida 1x1
@app.post("/connect", response_model=MatchOut)
def connect_players(db: Session = Depends(get_db)):
    # Buscar jogadores disponíveis (status "waiting")
    waiting_players = db.query(MatchPlayer).filter(MatchPlayer.status == "waiting").all()

    if len(waiting_players) < 2:
        return {"message": "Não há jogadores suficientes para criar uma partida."}

    # Conectar os dois primeiros jogadores disponíveis
    player1 = waiting_players[0]
    player2 = waiting_players[1]

    # Criar partida
    match = Match(player1_id=player1.id, player2_id=player2.id)
    db.add(match)
    db.commit()
    db.refresh(match)

    # Atualizar o status dos jogadores para "playing"
    player1.status = "playing"
    player2.status = "playing"
    db.commit()

    return match

# Rota opcional para avisar sobre a documentação
@app.get("/docs-info")
def docs_info():
    return {"message": "A documentação Swagger está disponível em /docs"}
