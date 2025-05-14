from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .config import Base

# Tabela de usuários
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Tabela de partidas
class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

# Jogadores em uma partida
class MatchPlayer(Base):
    __tablename__ = "match_players"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    score = Column(Integer, default=0)
    connected_at = Column(DateTime, default=datetime.utcnow)

# Perguntas
class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String, nullable=False)
    options = Column(String, nullable=False)  # JSON string com as opções
    correct_option = Column(String, nullable=False)
    tip = Column(String, nullable=True)  # Dica da pergunta
    created_at = Column(DateTime, default=datetime.utcnow)

# Relação entre partidas e perguntas
class MatchQuestion(Base):
    __tablename__ = "match_questions"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    answered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    selected_option = Column(String, nullable=True)
    time_taken = Column(Float, nullable=True)  # Tempo para responder
    is_correct = Column(Boolean, nullable=True)
