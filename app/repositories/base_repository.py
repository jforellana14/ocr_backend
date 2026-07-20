from sqlalchemy.orm import Session


class BaseRepository:

    model = None

    @classmethod
    def get_all(cls, db: Session):
        return db.query(cls.model).all()

    @classmethod
    def get_by_id(cls, db: Session, item_id: int):
        return (
            db.query(cls.model)
            .filter(cls.model.id == item_id)
            .first()
        )

    @classmethod
    def create(cls, db: Session, item):
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def update(cls, db: Session):
        db.commit()

    @classmethod
    def delete(cls, db: Session, item):
        db.delete(item)
        db.commit()