# app/services/tournament_service.py

from sqlalchemy.orm import Session
from app.models import Tournament, TournamentMatch, Match, User
from datetime import datetime
from typing import List

def set_match_winner(db: Session, tournament_match_id: int, winner_user_id: int):
    """
    Atualiza o vencedor da partida no torneio,
    e avança o torneio se necessário.
    """

    tm = db.query(TournamentMatch).get(tournament_match_id)
    if not tm:
        raise ValueError("TournamentMatch não encontrado")

    if tm.winner_id:
        raise ValueError("Vencedor já definido")

    # Define o vencedor
    tm.winner_id = winner_user_id
    db.commit()

    # Checa se toda rodada está completa
    tournament = tm.tournament
    round_num = tm.round_number

    all_matches_round = db.query(TournamentMatch).filter_by(
        tournament_id=tournament.id,
        round_number=round_num
    ).all()

    # Se algum duelo não tiver vencedor, ainda não avança
    if any(m.winner_id is None for m in all_matches_round):
        return "Aguardando conclusão de todas partidas da rodada"

    # Se for a rodada final, termina o torneio
    if len(all_matches_round) == 1:
        tournament.status = "finalizado"
        tournament.winner_id = all_matches_round[0].winner_id
        db.commit()
        return f"Torneio finalizado. Campeão: usuário {tournament.winner_id}"

    # Senão, monta próxima rodada
    montar_proxima_rodada(db, tournament, round_num + 1)
    return f"Avançou para rodada {round_num + 1}"

def montar_proxima_rodada(db: Session, tournament: Tournament, round_number: int):
    """
    Monta as partidas da próxima rodada com os vencedores da rodada anterior.
    """

    # Pega vencedores da rodada anterior
    prev_round_matches = db.query(TournamentMatch).filter_by(
        tournament_id=tournament.id,
        round_number=round_number - 1
    ).all()

    vencedores = [m.winner_id for m in prev_round_matches]

    # Embaralha para aleatorizar duelos (opcional)
    import random
    random.shuffle(vencedores)

    # Cria partidas da próxima rodada (duplas)
    for i in range(0, len(vencedores), 2):
        user1 = vencedores[i]
        user2 = vencedores[i+1]

        # Cria partida 1x1 (Match)
        match = Match()
        db.add(match)
        db.commit()
        db.refresh(match)

        # Adiciona jogadores na partida
        from app.models import MatchPlayer
        mp1 = MatchPlayer(match_id=match.id, user_id=user1, status="playing")
        mp2 = MatchPlayer(match_id=match.id, user_id=user2, status="playing")
        db.add_all([mp1, mp2])
        db.commit()

        # Cria registro do duelo no torneio
        tm = TournamentMatch(
            tournament_id=tournament.id,
            match_id=match.id,
            round_number=round_number,
            player1_id=user1,
            player2_id=user2
        )
        db.add(tm)
    db.commit()
