from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.config import SessionLocal
from app.models import Tournament, TournamentMatch, User, Match, MatchPlayer
from datetime import datetime
import random

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Entrar na fila do torneio e iniciar chaves quando atingir mínimo
@router.post("/tournament/join")
def join_tournament(user_id: int, db: Session = Depends(get_db)):
    # Buscar torneio esperando ou criar novo
    tournament = db.query(Tournament).filter(Tournament.status == "esperando").first()
    if not tournament:
        tournament = Tournament(status="esperando", tipo="eliminatorio")
        db.add(tournament)
        db.commit()
        db.refresh(tournament)

    # Verificar se usuário já inscrito no torneio
    inscritos = set()
    for match in tournament.matches:
        if match.player1_id:
            inscritos.add(match.player1_id)
        if match.player2_id:
            inscritos.add(match.player2_id)

    if user_id in inscritos:
        raise HTTPException(status_code=400, detail="Usuário já inscrito no torneio")

    inscritos.add(user_id)

    minimo_jogadores = 4  # pode parametrizar

    if len(inscritos) < minimo_jogadores:
        return {"message": f"Inscrito no torneio. Aguardando mais jogadores. {len(inscritos)}/{minimo_jogadores}"}

    # Montar chaves (embaralhar e criar duplas)
    inscritos_list = list(inscritos)
    random.shuffle(inscritos_list)

    for i in range(0, minimo_jogadores, 2):
        user1_id = inscritos_list[i]
        user2_id = inscritos_list[i + 1]

        # Criar partida 1x1 (Match)
        match = Match()
        db.add(match)
        db.commit()
        db.refresh(match)

        # Adicionar jogadores à partida
        mp1 = MatchPlayer(match_id=match.id, user_id=user1_id, status="playing")
        mp2 = MatchPlayer(match_id=match.id, user_id=user2_id, status="playing")
        db.add_all([mp1, mp2])
        db.commit()

        # Criar registro da partida no torneio
        tournament_match = TournamentMatch(
            tournament_id=tournament.id,
            match_id=match.id,
            round_number=1,
            player1_id=user1_id,
            player2_id=user2_id
        )
        db.add(tournament_match)

    tournament.status = "em_andamento"
    db.commit()

    return {"message": f"Torneio iniciado com {minimo_jogadores} jogadores"}


# Retorna status e chaves do torneio
@router.get("/tournament/status/{tournament_id}")
def get_tournament_status(tournament_id: int, db: Session = Depends(get_db)):
    tournament = db.query(Tournament).get(tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Torneio não encontrado")

    data = {
        "id": tournament.id,
        "status": tournament.status,
        "matches": []
    }

    for tm in tournament.matches:
        data["matches"].append({
            "match_id": tm.match_id,
            "round": tm.round_number,
            "player1_id": tm.player1_id,
            "player2_id": tm.player2_id,
            "winner_id": tm.winner_id,
        })

    return data


# Serviço para atualizar vencedor da partida e avançar torneio
def set_match_winner(db: Session, tournament_match_id: int, winner_user_id: int):
    tmatch = db.query(TournamentMatch).filter(TournamentMatch.id == tournament_match_id).first()
    if not tmatch:
        raise ValueError("Partida do torneio não encontrada")

    if tmatch.winner_id is not None:
        raise ValueError("Partida já tem vencedor definido")

    # Verificar se winner_user_id é um dos jogadores da partida
    if winner_user_id not in (tmatch.player1_id, tmatch.player2_id):
        raise ValueError("Vencedor informado não é jogador desta partida")

    # Atualizar vencedor da partida
    tmatch.winner_id = winner_user_id
    db.commit()

    tournament = db.query(Tournament).filter(Tournament.id == tmatch.tournament_id).first()
    if not tournament:
        raise ValueError("Torneio não encontrado")

    rodada_atual = tmatch.round_number

    # Verificar se todas partidas da rodada atual terminaram
    partidas_rodada = db.query(TournamentMatch).filter(
        and_(
            TournamentMatch.tournament_id == tournament.id,
            TournamentMatch.round_number == rodada_atual
        )
    ).all()

    todas_terminaram = all(pm.winner_id is not None for pm in partidas_rodada)
    if not todas_terminaram:
        return f"Vencedor atualizado para a partida {tournament_match_id}. Aguardando término das outras partidas da rodada {rodada_atual}."

    # Verificar se rodada atual é a final
    max_round = db.query(TournamentMatch.round_number).filter(
        TournamentMatch.tournament_id == tournament.id
    ).order_by(TournamentMatch.round_number.desc()).first()[0]

    if rodada_atual == max_round:
        # Definir vencedor do torneio e finalizar
        # Assumindo só uma partida na final
        final_match = partidas_rodada[0]
        tournament.winner_id = final_match.winner_id
        tournament.status = "finalizado"
        db.commit()
        return f"Torneio finalizado! Vencedor: usuário {tournament.winner_id}."

    # Montar próxima rodada com vencedores em pares
    proxima_rodada = rodada_atual + 1
    vencedores = [pm.winner_id for pm in partidas_rodada]

    for i in range(0, len(vencedores), 2):
        player1 = vencedores[i]
        player2 = vencedores[i + 1] if i + 1 < len(vencedores) else None

        # Criar nova partida Match
        nova_match = Match()
        db.add(nova_match)
        db.commit()
        db.refresh(nova_match)

        # Criar TournamentMatch para próxima rodada
        novo_tmatch = TournamentMatch(
            tournament_id=tournament.id,
            match_id=nova_match.id,
            round_number=proxima_rodada,
            player1_id=player1,
            player2_id=player2
        )
        db.add(novo_tmatch)

        # Criar MatchPlayers (status "waiting" ou "playing" pode ser definido)
        mp1 = MatchPlayer(match_id=nova_match.id, user_id=player1, status="waiting")
        db.add(mp1)
        if player2:
            mp2 = MatchPlayer(match_id=nova_match.id, user_id=player2, status="waiting")
            db.add(mp2)

    db.commit()
    return f"Rodada {rodada_atual} finalizada. Próxima rodada {proxima_rodada} iniciada."


# Rota para reportar vencedor da partida
@router.post("/tournament/match/winner")
def report_match_winner(
    tournament_match_id: int = Body(..., embed=True),
    winner_user_id: int = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    try:
        resultado = set_match_winner(db, tournament_match_id, winner_user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": resultado}
