from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime

from app.config import get_db
from app.models import Question, MatchQuestion, User
from app.services.openai_service import gerar_pergunta

router = APIRouter()

# ------------------------------
# 1. Gerar nova pergunta
# ------------------------------
@router.get("/question")
def get_next_question(match_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Gera uma nova pergunta via API do ChatGPT, salva no banco e vincula à partida.
    Limita a 10 perguntas respondidas por jogador na partida.
    """
    # Conta quantas perguntas esse usuário já respondeu nessa partida (incluindo extra rounds)
    respostas_usuario = db.query(MatchQuestion).filter_by(
        match_id=match_id,
        answered_by_user_id=user_id
    ).count()

    if respostas_usuario >= 10:
        return {"message": "Você já respondeu 10 perguntas nesta partida."}

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

    # Cria vínculo com a partida, registrando o momento do envio (timestamp)
    match_question = MatchQuestion(
        match_id=match_id,
        question_id=question_db.id,
        is_extra_round=False,
        sent_at=datetime.utcnow()
    )
    db.add(match_question)
    db.commit()
    db.refresh(match_question)

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
    time_taken: Optional[float] = None  # opcional, será calculado com base no sent_at

@router.post("/answer")
def submit_answer(answer: AnswerRequest, db: Session = Depends(get_db)):
    """
    Recebe a resposta de um usuário a uma pergunta específica.
    Atualiza o vínculo com a partida incluindo se acertou e tempo de resposta.
    Considera resposta fora do tempo (mais de 10 segundos) como errada.
    """
    # Busca a pergunta vinculada à partida (independente se já respondida)
    match_question = db.query(MatchQuestion).filter_by(
        match_id=answer.match_id,
        question_id=answer.question_id
    ).first()

    if not match_question:
        raise HTTPException(status_code=404, detail="Partida/Pergunta não encontrada")

    # Verifica se a pergunta já foi respondida por qualquer jogador
    if match_question.answered_by_user_id is not None:
        raise HTTPException(status_code=400, detail="Essa pergunta já foi respondida.")

    # Verifica se o user_id está correto para essa resposta (pode ser checagem extra)
    # Se precisar que o usuário responda, validar aqui se é permitido

    question = db.query(Question).filter(Question.id == answer.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")

    # Calcula o tempo decorrido desde o envio da pergunta
    if not match_question.sent_at:
        raise HTTPException(status_code=500, detail="Timestamp de envio não registrado")

    tempo_agora = datetime.utcnow()
    tempo_decorrido = (tempo_agora - match_question.sent_at).total_seconds()

    # Checa se resposta está dentro do limite (ex: 10 segundos)
    limite_tempo = 10
    acertou = (answer.selected_option.strip().upper() == question.correct_option.strip().upper())
    if tempo_decorrido > limite_tempo:
        acertou = False  # Resposta fora do tempo é considerada incorreta

    # Atualiza registro no banco
    match_question.answered_by_user_id = answer.user_id
    match_question.selected_option = answer.selected_option
    match_question.time_taken = round(tempo_decorrido, 2)
    match_question.is_correct = acertou

    db.commit()

    return {
        "message": "Resposta registrada com sucesso" if tempo_decorrido <= limite_tempo else "Tempo esgotado! Resposta considerada incorreta.",
        "correct": acertou,
        "correct_option": question.correct_option,
        "tip": question.tip,
        "tempo_decorrido": round(tempo_decorrido, 2)
    }

# ------------------------------
# 3. Ver resultado da partida
# ------------------------------
@router.get("/result")
def get_result(match_id: int, db: Session = Depends(get_db)):
    """
    Retorna as pontuações dos jogadores em uma partida e identifica o(s) vencedor(es).
    Considera apenas perguntas que não sejam da rodada extra.
    """
    respostas = db.query(MatchQuestion).filter(
        MatchQuestion.match_id == match_id,
        MatchQuestion.is_extra_round == False,
        MatchQuestion.answered_by_user_id.isnot(None)  # só respostas respondidas
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

    # Aqui você pode atualizar o campo vitorias do User se quiser registrar no banco, por exemplo:
    # if len(vencedores) == 1:
    #     vencedor = db.query(User).filter(User.id == vencedores[0]).first()
    #     if vencedor:
    #         vencedor.vitorias += 1
    #         db.commit()

    return {
        "pontuacoes": pontuacao,
        "empate": len(vencedores) > 1,
        "vencedores": vencedores
    }
