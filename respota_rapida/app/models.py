from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

# Base declarativa
Base = declarative_base()

# Tabela de usuários
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    matches_won = relationship("Match", back_populates="winner", foreign_keys="Match.winner_id")
    match_players = relationship("MatchPlayer", back_populates="user", foreign_keys="MatchPlayer.user_id")
    answered_questions = relationship("MatchQuestion", back_populates="answered_by_user", foreign_keys="MatchQuestion.answered_by_user_id")


# Tabela de partidas
class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    player1_id = Column(Integer, ForeignKey('match_players.id'))
    player2_id = Column(Integer, ForeignKey('match_players.id'))
    start_time = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    winner = relationship("User", back_populates="matches_won", foreign_keys=[winner_id])
    players = relationship("MatchPlayer", back_populates="match")
    questions = relationship("MatchQuestion", back_populates="match")
    player1 = relationship("MatchPlayer", foreign_keys=[player1_id])
    player2 = relationship("MatchPlayer", foreign_keys=[player2_id])


# Jogadores em uma partida
class MatchPlayer(Base):
    __tablename__ = "match_players"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    score = Column(Integer, default=0)
    connected_at = Column(DateTime, default=datetime.utcnow)
    name = Column(String, index=True)
    status = Column(String, default="waiting")  # status do jogador ("waiting", "playing")

    # Relacionamentos
    match = relationship("Match", back_populates="players")
    user = relationship("User", back_populates="match_players")


# Perguntas
class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String(191), nullable=False)  # reduzido
    options = Column(String(1000), nullable=False)        # JSON com várias opções, tamanho maior
    correct_option = Column(String(100), nullable=False)  # reduzido
    tip = Column(String(255), nullable=True)              # reduzido
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    match_questions = relationship("MatchQuestion", back_populates="question")


# Relação entre partidas e perguntas
class MatchQuestion(Base):
    __tablename__ = "match_questions"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    answered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    selected_option = Column(String(100), nullable=True)  # reduzido
    time_taken = Column(Float, nullable=True)
    is_correct = Column(Boolean, nullable=True)

    # Relacionamentos
    match = relationship("Match", back_populates="questions")
    question = relationship("Question", back_populates="match_questions")
    answered_by_user = relationship("User", back_populates="answered_questions", foreign_keys=[answered_by_user_id])
