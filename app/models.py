"""SQLAlchemy ORM models (database tables)."""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


class Exercise(Base):
    """Exercise library. min_reps/max_reps define the target rep range
    used by the double-progression algorithm; increment_weight is how
    much weight is added once that range is hit at low RIR."""
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    muscle_group = Column(String, default="")
    min_reps = Column(Integer, default=8)
    max_reps = Column(Integer, default=12)
    increment_weight = Column(Float, default=2.5)
    tip = Column(Text, default="")
    is_custom = Column(Boolean, default=False)

    day_links = relationship("ProgramDayExercise", back_populates="exercise")
    set_logs = relationship("SetLog", back_populates="exercise")


class Program(Base):
    """A weekly training split, e.g. 'PPL — Push/Pull/Legs'."""
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    days = relationship(
        "ProgramDay", back_populates="program",
        order_by="ProgramDay.order_index", cascade="all, delete-orphan"
    )


class ProgramDay(Base):
    """One day within a program's weekly rotation (order_index 0..N-1)."""
    __tablename__ = "program_days"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    muscles = Column(String, default="")
    is_rest = Column(Boolean, default=False)

    program = relationship("Program", back_populates="days")
    exercises = relationship(
        "ProgramDayExercise", back_populates="day",
        order_by="ProgramDayExercise.order_index", cascade="all, delete-orphan"
    )


class ProgramDayExercise(Base):
    """Links an Exercise to a ProgramDay with a target set count."""
    __tablename__ = "program_day_exercises"

    id = Column(Integer, primary_key=True, index=True)
    day_id = Column(Integer, ForeignKey("program_days.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    target_sets = Column(Integer, default=3)

    day = relationship("ProgramDay", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="day_links")


class Workout(Base):
    """One training session (a logged instance of a ProgramDay)."""
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    day_id = Column(Integer, ForeignKey("program_days.id"), nullable=True)
    program_name = Column(String, default="")
    day_name = Column(String, default="")
    readiness_score = Column(Integer, nullable=True)  # 1-5
    notes = Column(Text, default="")
    duration_seconds = Column(Integer, default=0)
    volume = Column(Float, default=0.0)
    finished = Column(Boolean, default=False)

    set_logs = relationship(
        "SetLog", back_populates="workout", cascade="all, delete-orphan"
    )


class SetLog(Base):
    """A single logged set: weight, reps, and RIR (reps in reserve).
    is_effective is precomputed (RIR <= 3) so weekly-volume queries
    can filter warm-up sets out cheaply."""
    __tablename__ = "set_logs"

    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    set_index = Column(Integer, default=0)
    weight = Column(Float, default=0.0)
    reps = Column(Integer, default=0)
    rir = Column(Integer, nullable=True)  # 0-4, null = not set
    is_effective = Column(Boolean, default=True)

    workout = relationship("Workout", back_populates="set_logs")
    exercise = relationship("Exercise", back_populates="set_logs")


class BodyWeight(Base):
    """Daily body-weight log."""
    __tablename__ = "body_weights"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    weight = Column(Float, nullable=False)


class Settings(Base):
    """Single-row table holding the user's current program/day choice."""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, default=1)
    current_program_id = Column(Integer, ForeignKey("programs.id"), nullable=True)
    current_day_index = Column(Integer, default=0)
