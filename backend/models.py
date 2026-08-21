import datetime
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Float,
    Enum, Text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import uuid

from database import Base


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    users = relationship("User", back_populates="company")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="candidate")  # candidate, employer, admin
    company = relationship("Company", back_populates="users")
    sessions = relationship("TestSession", back_populates="user")


class TestSession(Base):
    __tablename__ = "test_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="active")  # active, completed, failed

    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    task_performance_score = Column(Float, default=0.0)
    prompt_craft_score = Column(Float, default=0.0)
    critical_analysis_score = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)

    public_feedback = Column(Text, nullable=True)
    internal_analytics = Column(JSONB, nullable=True)

    user = relationship("User", back_populates="sessions")
    logs = relationship("PromptLog", back_populates="session")


class UniquePrompt(Base):
    __tablename__ = "unique_prompts"
    id = Column(Integer, primary_key=True, index=True)
    prompt_hash = Column(String(64), unique=True, nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)


class UniqueSolution(Base):
    __tablename__ = "unique_solutions"
    id = Column(Integer, primary_key=True, index=True)
    solution_hash = Column(String(64), unique=True, nullable=False, index=True)
    ai_response = Column(JSONB, nullable=False)


class PromptLog(Base):
    __tablename__ = "prompt_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("test_sessions.id"), nullable=False)
    unique_prompt_id = Column(Integer, ForeignKey("unique_prompts.id"), nullable=True)
    unique_solution_id = Column(Integer, ForeignKey("unique_solutions.id"), nullable=True)

    iteration_number = Column(Integer, nullable=False, default=1)
    author_type = Column(String, nullable=False)  # 'human', 'ai'

    seconds_spent_on_step = Column(Integer, default=0)
    nesting_level = Column(Integer, default=1)

    prompt_craft_score = Column(Float, default=0.0)
    process_depth_score = Column(Float, default=0.0)
    analysis_metrics = Column(JSONB, nullable=True)
    tokens_used = Column(Integer, default=0)

    session = relationship("TestSession", back_populates="logs")