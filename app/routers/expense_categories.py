from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import ExpenseCategoryCreate, ExpenseCategoryResponse
from auth import get_current_user, require_roles
from app.services.expense_category_service import ExpenseCategoryService


router = APIRouter(
    prefix="/expense-categories",
    tags=["Expense Categories"]
)


@router.get("", response_model=list[ExpenseCategoryResponse])
def get_expense_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ExpenseCategoryService.get_all(db)


@router.get("/{item_id}", response_model=ExpenseCategoryResponse)
def get_expense_category(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ExpenseCategoryService.get_by_id(db, item_id)


@router.post("", response_model=ExpenseCategoryResponse)
def create_expense_category(
    payload: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return ExpenseCategoryService.create(db, payload)


@router.delete("/{item_id}")
def delete_expense_category(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    return ExpenseCategoryService.delete(db, item_id)