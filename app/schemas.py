"""Pydantic request/response schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class SetLogIn(BaseModel):
    exercise_id: int
    set_index: int = 0
    weight: float = 0
    reps: int = 0
    rir: Optional[int] = Field(default=None, ge=0, le=4)


class ExerciseIn(BaseModel):
    name: str
    muscle_group: str = ""
    min_reps: int = 8
    max_reps: int = 12
    increment_weight: float = 2.5
    tip: str = ""


class BodyWeightIn(BaseModel):
    weight: float = Field(gt=20, lt=300)


class FinishWorkoutIn(BaseModel):
    readiness_score: Optional[int] = Field(default=None, ge=1, le=5)
    notes: str = ""
