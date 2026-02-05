# models.py
from sqlmodel import SQLModel, Field
from typing import Optional


class TaskBase(SQLModel):
    title: str
    completed: bool = False
    assigned_to: Optional[str] = None
    project_id: Optional[str] = "default"
    task_type: Optional[str] = "standard"
    estimated_hours: Optional[float] = 0.0
    actual_hours: Optional[float] = 0.0
    status: str = "pending"


class Task(TaskBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase):
    id: int
