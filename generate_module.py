import os
import sys
from pathlib import Path


BASE = Path("app")


def pascal_case(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def ensure_dirs():
    for folder in [
        BASE / "routers",
        BASE / "services",
        BASE / "repositories",
    ]:
        folder.mkdir(parents=True, exist_ok=True)
        init_file = folder / "__init__.py"
        init_file.touch(exist_ok=True)


def write_file(path: Path, content: str):
    if path.exists():
        print(f"SKIP: {path} ya existe")
        return

    path.write_text(content, encoding="utf-8")
    print(f"CREATED: {path}")


def generate(module_name: str):
    ensure_dirs()

    class_name = pascal_case(module_name)
    service_name = f"{class_name}Service"
    repo_name = f"{class_name}Repository"

    router_file = BASE / "routers" / f"{module_name}.py"
    service_file = BASE / "services" / f"{module_name}_service.py"
    repo_file = BASE / "repositories" / f"{module_name}_repository.py"

    repo_content = f'''from app.repositories.base_repository import BaseRepository
from models import {class_name}


class {repo_name}(BaseRepository):

    model = {class_name}
'''

    service_content = f'''from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import {class_name}
from schemas import {class_name}Create
from app.repositories.{module_name}_repository import {repo_name}


class {service_name}:

    @staticmethod
    def get_all(db: Session):
        return {repo_name}.get_all(db)

    @staticmethod
    def get_by_id(db: Session, item_id: int):
        item = {repo_name}.get_by_id(db, item_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="{class_name} no encontrado."
            )

        return item

    @staticmethod
    def create(db: Session, payload: {class_name}Create):
        item = {class_name}(**payload.model_dump())
        return {repo_name}.create(db, item)

    @staticmethod
    def delete(db: Session, item_id: int):
        item = {repo_name}.get_by_id(db, item_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="{class_name} no encontrado."
            )

        {repo_name}.delete(db, item)

        return {{
            "message": "{class_name} eliminado correctamente."
        }}
'''

    router_content = f'''from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import {class_name}Create, {class_name}Response
from auth import get_current_user, require_roles
from app.services.{module_name}_service import {service_name}


router = APIRouter(
    prefix="/{module_name.replace("_", "-")}",
    tags=["{class_name}"]
)


@router.get("", response_model=list[{class_name}Response])
def get_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {service_name}.get_all(db)


@router.get("/{{item_id}}", response_model={class_name}Response)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {service_name}.get_by_id(db, item_id)


@router.post("", response_model={class_name}Response)
def create_item(
    payload: {class_name}Create,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ENCARGADO"))
):
    return {service_name}.create(db, payload)


@router.delete("/{{item_id}}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    return {service_name}.delete(db, item_id)
'''

    write_file(repo_file, repo_content)
    write_file(service_file, service_content)
    write_file(router_file, router_content)

    print()
    print("Ahora agrega en main.py:")
    print(f"from app.routers import {module_name}")
    print(f"app.include_router({module_name}.router)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso:")
        print("python generate_module.py nombre_modulo")
        print()
        print("Ejemplo:")
        print("python generate_module.py fuel_station")
        sys.exit(1)

    generate(sys.argv[1].strip())