from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config import SessionLocal
from app.models import User

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/ranking")
def get_ranking(db: Session = Depends(get_db)):
    # Busca os 10 usuários com mais vitórias, ordenados decrescente
    top_10 = db.query(User).order_by(User.vitorias.desc()).limit(10).all()

    # Formata resposta simples
    ranking = [{"id": u.id, "username": u.username, "vitorias": u.vitorias} for u in top_10]

    return {"ranking": ranking}
