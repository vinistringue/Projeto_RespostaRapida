from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.config import SessionLocal
from app.models import Tournament, TournamentMatch, User, Match, MatchPlayer
from datetime import datetime
import random

router = APIRouter()

# ────────────────────────────────
# DEPENDÊNCIA DO BANCO DE DADOS
# ────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ────────────────────────────────
# VALIDAÇÃO DE POTÊNCIA DE 2
# ────────────────────────────────
def is_power_of_two(n: int) -> bool:
    return (n & (n - 1) == 0) and n != 0

# ────────────────────────────────
# FUNÇÃO: MONTAR CHAVES INICIAIS
# ────────────────────────────────
def montar_chaves(db: Session, tournament: Tournament, inscritos: list[int], minimo_jogadores: int):
    random.shuffle(inscritos)

    for i in range(0, minimo_jogadores, 2):
        user1_id = inscritos[i]
        user2_id = inscritos[i + 1]

        match = Match()
        db.add(match)
        db.commit()
        db.refresh(match)

        mp1 = MatchPlayer(match_id=match.id, user_id=user1_id, status="playing")
        mp2 = MatchPlayer(match_id=match.id, user_id=user2_id, status="playing")
        db.add_all([mp1, mp2])

        tournament_match = TournamentMatch(
            tournament_id=tournament.id,
            match_id=match.id,
            round_number=1,
            player1_id=user1_id,
            player2_id=user2_id
        )
        db.add(tournament_match)

    db.commit()

# ────────────────────────────────
# ROTA: ENTRAR NO TORNEIO
# ────────────────────────────────
@router.post("/tournament/join")
def join_tournament(user_id: int, db: Session = Depends(get_db), minimo_jogadores: int = 4):
    if not is_power_of_two(minimo_jogadores):
        raise HTTPException(status_code=400, detail="Número de jogadores deve ser potência de 2 (ex: 4, 8, 16...)")

    tournament = db.query(Tournament).filter(Tournament.status == "esperando").first()
    if not tournament:
        tournament = Tournament(status="esperando", tipo="eliminatorio")
        db.add(tournament)
        db.commit()
        db.refresh(tournament)

    inscritos = []
    for match in tournament.matches:
        if match.player1_id:
            inscritos.append(match.player1_id)
        if match.player2_id:
            inscritos.append(match.player2_id)

    if user_id in inscritos:
        raise HTTPException(status_code=400, detail="Usuário já inscrito no torneio")

    inscritos.append(user_id)

    if len(inscritos) < minimo_jogadores:
        return {"message": f"Inscrito no torneio. Aguardando mais jogadores. {len(inscritos)}/{minimo_jogadores}"}

    montar_chaves(db, tournament, inscritos, minimo_jogadores)

    tournament.status = "em_andamento"
    db.commit()

    return {"message": f"Torneio iniciado com {minimo_jogadores} jogadores"}

# ────────────────────────────────
# ROTA: STATUS DO TORNEIO
# ────────────────────────────────
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

# ────────────────────────────────
# FUNÇÃO: DEFINIR VENCEDOR DE PARTIDA
# ────────────────────────────────
def set_match_winner(db: Session, tournament_match_id: int, winner_user_id: int):
    tmatch = db.query(TournamentMatch).filter(TournamentMatch.id == tournament_match_id).first()
    if not tmatch:
        raise ValueError("Partida do torneio não encontrada")
    if tmatch.winner_id is not None:
        raise ValueError("Partida já tem vencedor definido")
    if winner_user_id not in (tmatch.player1_id, tmatch.player2_id):
        raise ValueError("Vencedor informado não é jogador desta partida")

    tmatch.winner_id = winner_user_id
    vencedor = db.query(User).get(winner_user_id)
    if vencedor:
        vencedor.vitorias = (vencedor.vitorias or 0) + 1

    db.commit()

    tournament = db.query(Tournament).get(tmatch.tournament_id)
    if not tournament:
        raise ValueError("Torneio não encontrado")

    rodada_atual = tmatch.round_number

    partidas_rodada = db.query(TournamentMatch).filter(
        and_(
            TournamentMatch.tournament_id == tournament.id,
            TournamentMatch.round_number == rodada_atual
        )
    ).all()

    if not all(p.winner_id is not None for p in partidas_rodada):
        return f"Vencedor registrado. Aguardando término das outras partidas da rodada {rodada_atual}."

    max_round = db.query(TournamentMatch.round_number).filter(
        TournamentMatch.tournament_id == tournament.id
    ).order_by(TournamentMatch.round_number.desc()).first()[0]

    if rodada_atual == max_round:
        final_match = partidas_rodada[0]
        tournament.winner_id = final_match.winner_id
        tournament.status = "finalizado"

        vencedor_torneio = db.query(User).get(tournament.winner_id)
        if vencedor_torneio:
            vencedor_torneio.vitorias = (vencedor_torneio.vitorias or 0) + 1

        db.commit()
        return f"Torneio finalizado! Vencedor: usuário {tournament.winner_id}."

    # Montar próxima rodada
    vencedores = [p.winner_id for p in partidas_rodada]
    proxima_rodada = rodada_atual + 1

    for i in range(0, len(vencedores), 2):
        player1 = vencedores[i]
        player2 = vencedores[i + 1] if i + 1 < len(vencedores) else None

        nova_match = Match()
        db.add(nova_match)
        db.commit()
        db.refresh(nova_match)

        novo_tmatch = TournamentMatch(
            tournament_id=tournament.id,
            match_id=nova_match.id,
            round_number=proxima_rodada,
            player1_id=player1,
            player2_id=player2
        )
        db.add(novo_tmatch)

        mp1 = MatchPlayer(match_id=nova_match.id, user_id=player1, status="waiting")
        db.add(mp1)
        if player2:
            mp2 = MatchPlayer(match_id=nova_match.id, user_id=player2, status="waiting")
            db.add(mp2)

    db.commit()
    return f"Rodada {rodada_atual} finalizada. Próxima rodada {proxima_rodada} iniciada."

# ────────────────────────────────
# ROTA: DEFINIR VENCEDOR DE UMA PARTIDA
# ────────────────────────────────
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
