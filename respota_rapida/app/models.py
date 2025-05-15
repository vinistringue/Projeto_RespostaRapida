from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

# Usuário
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    matches_won = relationship("Match", back_populates="winner", foreign_keys="Match.winner_id")
    match_players = relationship("MatchPlayer", back_populates="user", foreign_keys="MatchPlayer.user_id")
    answered_questions = relationship("MatchQuestion", back_populates="answered_by_user", foreign_keys="MatchQuestion.answered_by_user_id")


# Partida
class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    # Vencedor da partida
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    winner = relationship("User", back_populates="matches_won", foreign_keys=[winner_id])

    # Jogadores principais (apontam para MatchPlayer)
    player1_id = Column(Integer, ForeignKey("match_players.id"))
    player2_id = Column(Integer, ForeignKey("match_players.id"))
    player1 = relationship("MatchPlayer", foreign_keys=[player1_id])
    player2 = relationship("MatchPlayer", foreign_keys=[player2_id])

    # Relacionamentos
    players = relationship("MatchPlayer", back_populates="match", foreign_keys="MatchPlayer.match_id")
    questions = relationship("MatchQuestion", back_populates="match", foreign_keys="MatchQuestion.match_id")

    # Campos adicionais
    start_time = Column(DateTime, default=datetime.utcnow)
    tipo = Column(String(10), default="normal")  # 'normal' ou 'torneio'
    status = Column(String(20), default="esperando")  # 'esperando', 'em_andamento', 'finalizado'


# Jogadores em uma partida
class MatchPlayer(Base):
    __tablename__ = "match_players"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    score = Column(Integer, default=0)
    status = Column(String, default="waiting")  # 'waiting', 'playing', etc
    connected_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    match = relationship("Match", back_populates="players", foreign_keys=[match_id])
    user = relationship("User", back_populates="match_players", foreign_keys=[user_id])


# Perguntas do sistema
class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String(191), nullable=False)
    options = Column(String(1000), nullable=False)         # JSON string
    correct_option = Column(String(100), nullable=False)
    tip = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    match_questions = relationship("MatchQuestion", back_populates="question")


# Relação entre perguntas e partidas
class MatchQuestion(Base):
    __tablename__ = "match_questions"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))

    answered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    selected_option = Column(String(100), nullable=True)
    time_taken = Column(Float, nullable=True)
    is_correct = Column(Boolean, nullable=True)

    # Relacionamentos
    match = relationship("Match", back_populates="questions", foreign_keys=[match_id])
    question = relationship("Question", back_populates="match_questions", foreign_keys=[question_id])
    answered_by_user = relationship("User", back_populates="answered_questions", foreign_keys=[answered_by_user_id])
