from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json

from app.config import SessionLocal
from app.models import Question, MatchQuestion
from app.services.openai_service import gerar_pergunta

router = APIRouter()

# Dependency para obter a sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------
# 1. Gerar nova pergunta
# ------------------------------
@router.get("/question")
def get_next_question(match_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Gera uma nova pergunta via API do ChatGPT, salva no banco e vincula à partida.
    """
    pergunta = gerar_pergunta()
    if not pergunta:
        raise HTTPException(status_code=500, detail="Erro ao gerar pergunta")

    # Salva a pergunta no banco
    question_db = Question(
        question_text=pergunta["question"],
        options=json.dumps(pergunta["options"]),
        correct_option=pergunta["correct_option"],
        tip=pergunta["tip"]
    )
    db.add(question_db)
    db.commit()
    db.refresh(question_db)

    # Cria vínculo com a partida
    match_question = MatchQuestion(
        match_id=match_id,
        question_id=question_db.id
    )
    db.add(match_question)
    db.commit()

    return {
        "question_id": question_db.id,
        "question": question_db.question_text,
        "options": json.loads(question_db.options),
        "tip": question_db.tip
    }

# ------------------------------
# 2. Responder pergunta
# ------------------------------
class AnswerRequest(BaseModel):
    match_id: int
    question_id: int
    user_id: int
    selected_option: str
    time_taken: Optional[float] = None

@router.post("/answer")
def submit_answer(answer: AnswerRequest, db: Session = Depends(get_db)):
    """
    Recebe a resposta de um usuário a uma pergunta específica.
    """
    match_question = db.query(MatchQuestion).filter_by(
        match_id=answer.match_id,
        question_id=answer.question_id
    ).first()

    if not match_question:
        raise HTTPException(status_code=404, detail="Partida/Pergunta não encontrada")

    question = db.query(Question).get(answer.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")

    is_correct = answer.selected_option.strip().upper() == question.correct_option.strip().upper()

    match_question.answered_by_user_id = answer.user_id
    match_question.selected_option = answer.selected_option
    match_question.time_taken = answer.time_taken
    match_question.is_correct = is_correct

    db.commit()

    return {
        "message": "Resposta registrada com sucesso",
        "correct": is_correct,
        "correct_option": question.correct_option,
        "tip": question.tip
    }

# ------------------------------
# 3. Ver resultado da partida
# ------------------------------
@router.get("/result")
def get_result(match_id: int, db: Session = Depends(get_db)):
    """
    Retorna as pontuações dos jogadores em uma partida e identifica o(s) vencedor(es).
    """
    respostas = db.query(MatchQuestion).filter(MatchQuestion.match_id == match_id).all()
    if not respostas:
        raise HTTPException(status_code=404, detail="Nenhuma resposta encontrada para esta partida")

    pontuacao = {}

    for r in respostas:
        if r.answered_by_user_id is None:
            continue
        if r.answered_by_user_id not in pontuacao:
            pontuacao[r.answered_by_user_id] = 0
        if r.is_correct:
            pontuacao[r.answered_by_user_id] += 1

    if not pontuacao:
        raise HTTPException(status_code=404, detail="Sem respostas válidas registradas")

    max_pontuacao = max(pontuacao.values())
    vencedores = [uid for uid, pontos in pontuacao.items() if pontos == max_pontuacao]

    return {
        "pontuacoes": pontuacao,
        "empate": len(vencedores) > 1,
        "vencedores": vencedores
    }
