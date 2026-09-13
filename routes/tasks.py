# ============================================
# TASK ROUTES
# ============================================
# This file handles:
#
# 1. Create task
# 2. Get user's tasks
# 3. Update user's task
# 4. Delete user's task
#
# All task operations require JWT authentication.
# ============================================

from fastapi import APIRouter, HTTPException, Depends

from database import get_db
from models import Task, User
from schemas import TaskCreate, TaskResponse

from auth import get_current_user


# ============================================
# CREATE API ROUTER
# ============================================

router = APIRouter()


# ============================================
# 1. CREATE TASK
# ============================================

@router.post(
    "/tasks",
    response_model=TaskResponse
)
def create_task(
    task_data: TaskCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):

    # ========================================
    # CREATE NEW TASK
    # ========================================

    task = Task(
        title=task_data.title,
        completed=task_data.completed,
        user_id=current_user["user_id"]
    )

    # ========================================
    # SAVE TASK
    # ========================================

    db.add(task)
    db.commit()
    db.refresh(task)

    # ========================================
    # RETURN TASK
    # ========================================

    return task


# ============================================
# 2. GET MY TASKS
# ============================================

@router.get(
    "/tasks",
    response_model=list[TaskResponse]
)
def get_tasks(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):

    # ========================================
    # GET ONLY CURRENT USER'S TASKS
    # ========================================

    tasks = db.query(Task).filter(
        Task.user_id == current_user["user_id"]
    ).all()

    return tasks


# ============================================
# 3. UPDATE TASK
# ============================================

@router.put(
    "/tasks/{task_id}",
    response_model=TaskResponse
)
def update_task(
    task_id: int,
    task_data: TaskCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):

    # ========================================
    # FIND USER'S TASK
    # ========================================
    # We check:
    #
    # Task ID
    # +
    # Current User ID
    #
    # This prevents one user from modifying
    # another user's task.
    # ========================================

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user["user_id"]
    ).first()

    # ========================================
    # TASK NOT FOUND
    # ========================================

    if not task:

        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    # ========================================
    # UPDATE TASK
    # ========================================

    task.title = task_data.title
    task.completed = task_data.completed

    # ========================================
    # SAVE CHANGES
    # ========================================

    db.commit()
    db.refresh(task)

    return task


# ============================================
# 4. DELETE TASK
# ============================================

@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):

    # ========================================
    # FIND USER'S TASK
    # ========================================

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user["user_id"]
    ).first()

    # ========================================
    # TASK NOT FOUND
    # ========================================

    if not task:

        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    # ========================================
    # DELETE TASK
    # ========================================

    db.delete(task)
    db.commit()

    return {
        "message": "Task deleted successfully"
    }

# ============================================
# 5. TASKS WITH USERNAME
# ============================================
# This endpoint demonstrates a SQL JOIN.
#
# tasks.user_id → users.id
# ============================================

@router.get("/tasks-with-users")
def get_tasks_with_users(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):

    # ========================================
    # JOIN TASKS WITH USERS
    # ========================================

    results = (
        db.query(Task, User)
        .join(
            User,
            Task.user_id == User.id
        )
        .filter(
            Task.user_id == current_user["user_id"]
        )
        .all()
    )

    # ========================================
    # CREATE RESPONSE
    # ========================================

    return [
        {
            "task_id": task.id,
            "title": task.title,
            "completed": task.completed,
            "username": user.username
        }
        for task, user in results
    ]

# ============================================
# 6. SEARCH TASKS
# ============================================

@router.get("/tasks/search")
def search_tasks(
    keyword: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):

    # Search only inside the current user's tasks
    tasks = db.query(Task).filter(
        Task.user_id == current_user["user_id"],
        Task.title.ilike(f"%{keyword}%")
    ).all()

    return [
        {
            "id": task.id,
            "title": task.title,
            "completed": task.completed,
            "user_id": task.user_id
        }
        for task in tasks
    ]

# ============================================
# 7. FILTER AND SORT TASKS
# ============================================

@router.get("/tasks/filter")
def filter_tasks(
    completed: bool | None = None,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):

    # ========================================
    # START WITH CURRENT USER'S TASKS
    # ========================================

    query = db.query(Task).filter(
        Task.user_id == current_user["user_id"]
    )

    # ========================================
    # FILTER BY COMPLETED STATUS
    # ========================================

    if completed is not None:

        query = query.filter(
            Task.completed == completed
        )

    # ========================================
    # SORT BY ID
    # ========================================

    tasks = query.order_by(
        Task.id.desc()
    ).all()

    # ========================================
    # RESPONSE
    # ========================================

    return [
        {
            "id": task.id,
            "title": task.title,
            "completed": task.completed,
            "user_id": task.user_id
        }
        for task in tasks
    ]