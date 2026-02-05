from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="Task API", version="1.0.0")

# In-memory task storage (production would use database)
tasks: dict[str, dict] = {}

class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: int = 1

class Task(BaseModel):
    id: str
    title: str
    description: str | None
    priority: int
    created_at: datetime
    completed: bool = False

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "task-api"}

@app.post("/tasks", response_model=Task)
def create_task(task: TaskCreate):
    task_id = f"task_{len(tasks) + 1}"
    new_task = {
        "id": task_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "created_at": datetime.now(),
        "completed": False
    }
    tasks[task_id] = new_task
    return new_task

@app.get("/tasks")
def list_tasks():
    return list(tasks.values())

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@app.patch("/tasks/{task_id}/complete")
def complete_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    tasks[task_id]["completed"] = True
    return tasks[task_id]