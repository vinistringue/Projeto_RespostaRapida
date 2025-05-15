from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json

from app.config import get_db
from app.models import Question, MatchQuestion
from app.services.openai_service import gerar_pergunta

router = APIRouter()

# ------------------------------
# 1. Gerar nova pergunta
# ------------------------------
@router.get("/question")
def get_next_question(match_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Gera uma nova pergunta via API do ChatGPT, salva no banco e vincula à partida.
    Limita a 10 perguntas normais respondidas por jogador na partida.
    """
    respostas_usuario = db.query(MatchQuestion).filter_by(
        match_id=match_id,
        answered_by_user_id=user_id,
        is_extra_round=False
    ).count()

    if respostas_usuario >= 10:
        return {"message": "Você já respondeu 10 perguntas nesta partida."}

    pergunta = gerar_pergunta()
    if not pergunta:
        raise HTTPException(status_code=500, detail="Erro ao gerar pergunta")

    # Salva pergunta
    question_db = Question(
        question_text=pergunta["question"],
        options=json.dumps(pergunta["options"]),
        correct_option=pergunta["correct_option"],
        tip=pergunta["tip"]
    )
    db.add(question_db)
    db.commit()
    db.refresh(question_db)

    # Vincula pergunta à partida com timestamp de envio
    match_question = MatchQuestion(
        match_id=match_id,
        question_id=question_db.id,
        answered_by_user_id=None,  # Ainda não respondida
        sent_at=datetime.utcnow(),  # Timestamp do envio
        is_extra_round=False
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
    # time_taken será calculado com base no tempo de envio

@router.post("/answer")
def submit_answer(answer: AnswerRequest, db: Session = Depends(get_db)):
    """
    Recebe a resposta de um usuário a uma pergunta específica,
    valida se está no tempo limite e se a pergunta ainda não foi respondida.
    """
    match_question = db.query(MatchQuestion).filter_by(
        match_id=answer.match_id,
        question_id=answer.question_id,
        is_extra_round=False
    ).first()

    if not match_question:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada para essa partida")

    if match_question.answered_by_user_id is not None:
        raise HTTPException(status_code=400, detail="Pergunta já respondida")

    # Calcular tempo decorrido desde envio
    tempo_agora = datetime.utcnow()
    if not match_question.sent_at:
        raise HTTPException(status_code=500, detail="Timestamp de envio da pergunta não definido")
    tempo_decorrido = (tempo_agora - match_question.sent_at).total_seconds()

    # Buscar pergunta para validação da resposta correta
    question = db.query(Question).get(answer.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")

    acertou = answer.selected_option.strip().upper() == question.correct_option.strip().upper()

    # Se tempo maior que 10 segundos, resposta considerada errada
    if tempo_decorrido > 10:
        acertou = False

    # Atualiza registro da resposta
    match_question.answered_by_user_id = answer.user_id
    match_question.selected_option = answer.selected_option
    match_question.time_taken = tempo_decorrido
    match_question.is_correct = acertou

    db.commit()

    return {
        "correct_option": question.correct_option,
        "correct": acertou,
        "time_taken_seconds": round(tempo_decorrido, 2),
        "message": "Tempo esgotado! Resposta considerada incorreta." if tempo_decorrido > 10 else "Resposta registrada com sucesso."
    }

# ------------------------------
# 3. Ver resultado da partida
# ------------------------------
@router.get("/result")
def get_result(match_id: int, db: Session = Depends(get_db)):
    """
    Retorna as pontuações dos jogadores na partida.
    Se houver empate, cria rodada extra com 5 perguntas para cada empatado.
    """
    respostas = db.query(MatchQuestion).filter(
        MatchQuestion.match_id == match_id,
        MatchQuestion.is_extra_round == False,
        MatchQuestion.answered_by_user_id.isnot(None)  # Considerar só respostas dadas
    ).all()

    if not respostas:
        raise HTTPException(status_code=404, detail="Nenhuma resposta encontrada para esta partida")

    pontuacao = {}
    for r in respostas:
        if r.answered_by_user_id not in pontuacao:
            pontuacao[r.answered_by_user_id] = 0
        if r.is_correct:
            pontuacao[r.answered_by_user_id] += 1

    if not pontuacao:
        raise HTTPException(status_code=404, detail="Sem respostas válidas registradas")

    max_pontuacao = max(pontuacao.values())
    vencedores = [uid for uid, pontos in pontuacao.items() if pontos == max_pontuacao]

    # Se não há empate, retorna resultado final
    if len(vencedores) == 1:
        return {
            "pontuacoes": pontuacao,
            "empate": False,
            "vencedor": vencedores[0]
        }

    # Empate: criar rodada extra com 5 perguntas para cada empatado
    perguntas_extra = []
    for user_id in vencedores:
        for _ in range(5):
            pergunta = gerar_pergunta()
            if not pergunta:
                continue

            question_db = Question(
                question_text=pergunta["question"],
                options=json.dumps(pergunta["options"]),
                correct_option=pergunta["correct_option"],
                tip=pergunta["tip"]
            )
            db.add(question_db)
            db.commit()
            db.refresh(question_db)

            match_question = MatchQuestion(
                match_id=match_id,
                question_id=question_db.id,
                answered_by_user_id=None,
                sent_at=datetime.utcnow(),
                is_extra_round=True
            )
            db.add(match_question)
            perguntas_extra.append({
                "user_id": user_id,
                "question_id": question_db.id,
                "question": question_db.question_text,
                "options": json.loads(question_db.options),
                "tip": question_db.tip
            })
    db.commit()

    return {
        "pontuacoes": pontuacao,
        "empate": True,
        "vencedores": vencedores,
        "mensagem": "Empate detectado. Rodada extra com 5 perguntas criada para os jogadores empatados.",
        "perguntas_extra": perguntas_extra  # Pode ser útil para enviar perguntas extras aos usuários empatados
    }
