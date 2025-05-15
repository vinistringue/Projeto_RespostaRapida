# app/routers/connect.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..config import SessionLocal
from ..models import User, Match, MatchPlayer

router = APIRouter()

# Dependência para obter a sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Busca ou cria usuário (evita duplicatas)
def get_or_create_user(db: Session, username: str):
    user = db.query(User).filter_by(username=username).first()
    if user:
        return user
    user = User(username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Busca uma partida que tenha apenas um jogador
def find_waiting_match(db: Session):
    return (
        db.query(MatchPlayer.match_id)
        .join(Match, Match.id == MatchPlayer.match_id)
        .group_by(MatchPlayer.match_id)
        .having(func.count(MatchPlayer.user_id) == 1)
        .first()
    )

# Endpoint para conectar jogador
@router.post("/connect")
def connect_player(username: str, db: Session = Depends(get_db)):
    if not username:
        raise HTTPException(status_code=400, detail="Nome de usuário é obrigatório.")

    # Obtém ou cria usuário
    user = get_or_create_user(db, username)

    # Verifica se existe partida aguardando adversário
    waiting = find_waiting_match(db)

    if waiting:
        match_id = waiting.match_id
        status_msg = "Partida pronta para iniciar"
    else:
        # Cria nova partida
        new_match = Match()
        db.add(new_match)
        db.commit()
        db.refresh(new_match)
        match_id = new_match.id
        status_msg = "Aguardando adversário"

    # Registra jogador na partida
    match_player = MatchPlayer(match_id=match_id, user_id=user.id)
    db.add(match_player)
    db.commit()
    db.refresh(match_player)

    return {
        "message": "Jogador conectado com sucesso.",
        "user_id": user.id,
        "match_id": match_id,
        "status": status_msg
    }
