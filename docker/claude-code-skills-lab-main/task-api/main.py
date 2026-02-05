# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session, select
import logging
from typing import Optional
from datetime import datetime
import asyncio

from models import Task, TaskCreate, TaskRead
from database import create_db_and_tables, get_session

# Import Dapr modules for service invocation
from dapr.ext.fastapi import DaprApp
from dapr.clients import DaprClient
from dapr.clients.exceptions import DaprInternalError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Task API", lifespan=lifespan)

# Wrap the FastAPI app with Dapr extension
dapr_app = DaprApp(app)


@app.get("/")
def root():
    return {"message": "Hello from Docker!"}


@app.get("/health")
def health_check():
    """Health check endpoint for container orchestrators."""
    return {"status": "healthy", "service": "task-api"}


@app.get("/version")
def get_version():
    return {"version": "1.0.0"}


@app.post("/tasks", response_model=TaskRead)
def create_task(task: TaskCreate, session: Session = Depends(get_session)):
    db_task = Task.model_validate(task)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


@app.get("/tasks", response_model=list[TaskRead])
def list_tasks(session: Session = Depends(get_session)):
    tasks = session.exec(select(Task)).all()
    return tasks


@app.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, task_update: TaskCreate, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get original task status to check if it's being marked as complete
    original_status = task.status
    task_data = task_update.model_dump(exclude_unset=True)

    # Update task fields
    for key, value in task_data.items():
        setattr(task, key, value)

    session.add(task)
    session.commit()
    session.refresh(task)

    # Check if the task is being marked as complete and wasn't already complete
    if task.status == "complete" and original_status != "complete":
        # Trigger billing service invocation asynchronously
        asyncio.create_task(invoke_billing_service(task))

    return task


async def invoke_billing_service(task: Task):
    """
    Asynchronously invoke the billing service when a task is marked complete.
    This is called in the background to avoid blocking the main update operation.
    """
    billing_data = {
        "taskId": task.id,
        "userId": getattr(task, 'assigned_to', 'unknown'),  # Assuming there's an assigned_to field
        "projectId": getattr(task, 'project_id', 'default'),  # Assuming there's a project_id field
        "taskType": getattr(task, 'task_type', 'standard'),  # Assuming there's a task_type field
        "estimatedHours": getattr(task, 'estimated_hours', 0),  # Assuming there's an estimated_hours field
        "actualHours": getattr(task, 'actual_hours', 0),  # Assuming there's an actual_hours field
        "completedAt": datetime.utcnow().isoformat()
    }

    try:
        # Use Dapr client to invoke the billing service
        with DaprClient() as client:
            logger.info(f"Invoking billing service for completed task: {task.id}")

            # Call the billing service via Dapr service invocation
            response = client.invoke_method(
                app_id='billing-service',  # Target app id as defined in billing service deployment
                method_name='webhook/task-completed',  # The endpoint in the billing service
                data=billing_data,
                http_verb='POST',
                content_type='application/json'
            )

            # Log the response from the billing service
            response_data = response.json()
            logger.info(f"Billing service response for task {task.id}: {response_data}")

    except DaprInternalError as e:
        # Handle Dapr-specific errors
        error_msg = f"Error invoking billing service for task {task.id}: {str(e)}"
        logger.error(error_msg)

        # Check for specific error types
        if "ERR_DIRECT_INVOKE" in str(e):
            logger.error(f"Service invocation failed - billing-service may be unreachable: {e}")
        elif "connection refused" in str(e).lower():
            logger.error(f"Connection refused when contacting billing-service: {e}")

        # In a production system, you might want to queue this for retry
        # or store it for later processing

    except Exception as e:
        # Handle other exceptions
        logger.error(f"Unexpected error during billing service invocation for task {task.id}: {str(e)}")


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    session.commit()
    return {"message": "Task deleted"}
