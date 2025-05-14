from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..config import SessionLocal
from ..models import User, Match, MatchPlayer
from datetime import datetime

router = APIRouter()

# Dependência para obter a sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Cria novo usuário
def create_user(db: Session, username: str):
    user = User(username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Busca jogador esperando partida
def find_waiting_player(db: Session):
    # Verifica se há algum jogador sozinho em uma partida não finalizada
    result = (
        db.query(MatchPlayer.match_id)
        .join(Match, Match.id == MatchPlayer.match_id)  # Garante que a junção entre Match e MatchPlayer está correta
        .group_by(MatchPlayer.match_id)
        .having(func.count(MatchPlayer.user_id) == 1)  # Usando func.count() de forma correta
        .first()
    )
    return result

@router.post("/connect")
def connect_player(username: str, db: Session = Depends(get_db)):
    if not username:
        raise HTTPException(status_code=400, detail="Nome de usuário é obrigatório.")

    # Cria novo usuário
    user = create_user(db, username)

    # Tenta encontrar jogador esperando
    waiting = find_waiting_player(db)

    if waiting:
        # Reutiliza a partida existente
        match_id = waiting.match_id
    else:
        # Cria nova partida
        new_match = Match()
        db.add(new_match)
        db.commit()
        db.refresh(new_match)
        match_id = new_match.id

    # Registra jogador na partida
    match_player = MatchPlayer(match_id=match_id, user_id=user.id)
    db.add(match_player)
    db.commit()
    db.refresh(match_player)

    return {
        "message": "Jogador conectado",
        "user_id": user.id,
        "match_id": match_id,
        "status": "Aguardando adversário" if not waiting else "Partida pronta para iniciar"
    }
