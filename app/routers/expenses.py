from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import ExpenseCreate, ExpenseResponse
from auth import get_current_user, require_roles
from app.services.expense_service import ExpenseService


router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"]
)


@router.get("", response_model=list[ExpenseResponse])
def get_expenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ExpenseService.get_all(db)


@router.get("/{item_id}", response_model=ExpenseResponse)
def get_expense(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ExpenseService.get_by_id(db, item_id)


@router.post("", response_model=ExpenseResponse)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return ExpenseService.create(db, payload, current_user)


@router.delete("/{item_id}")
def delete_expense(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    return ExpenseService.delete(db, item_id)