from __future__ import annotations

from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from models import Document


class ProfitabilityRepository:
    """Acceso a los viajes utilizados por los reportes de rentabilidad.

    Este repositorio se limita a recuperar datos. Los cálculos financieros deben
    permanecer en los servicios y en ``FinancialEngine`` para conservar una sola
    fuente de verdad en todo el sistema.

    ``Document.fecha`` continúa almacenada como texto por compatibilidad con la
    aplicación móvil. Por eso el filtro SQL reduce el conjunto de resultados,
    mientras que ``ProfitabilityService`` realizará la validación definitiva de
    cada fecha antes de calcular el reporte.
    """

    @staticmethod
    def documents_for_period(
        db: Session,
        start: date,
        end: date,
    ) -> list[Document]:
        """Devuelve viajes candidatos para el período con relaciones cargadas.

        Las relaciones de cliente, camión y ruta se cargan en la misma consulta
        para evitar consultas N+1 al agrupar resultados por esas dimensiones.
        """

        iso_start = start.isoformat()
        iso_end = end.isoformat()

        return (
            db.query(Document)
            .options(
                joinedload(Document.cliente),
                joinedload(Document.camion),
                joinedload(Document.ruta),
            )
            .filter(
                or_(
                    Document.fecha.between(iso_start, iso_end),
                    Document.fecha.like("%/%"),
                    Document.fecha.like("%-%-%"),
                )
            )
            .order_by(Document.fecha.asc(), Document.id.asc())
            .all()
        )
