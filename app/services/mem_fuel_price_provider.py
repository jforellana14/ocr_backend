from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag


MEM_URL = (
    "https://mem.gob.gt/que-hacemos/hidrocarburos/"
    "comercializacion-downstream/precios-combustible-nacionales/"
)

SCRAPINGBEE_API_URL = "https://app.scrapingbee.com/api/v1/"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MemFuelPriceResult:
    fecha: date
    precio_diesel: float
    fuente: str
    vigencia_inicio: Optional[date] = None
    vigencia_fin: Optional[date] = None


def normalize_text(value: object) -> str:
    text = str(value or "").strip().upper()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def parse_date_value(value: object) -> Optional[date]:
    text = str(value or "").strip()

    match = re.search(
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        text,
    )

    if not match:
        return None

    raw_date = match.group(1)

    for date_format in (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(
                raw_date,
                date_format,
            ).date()
        except ValueError:
            continue

    return None


def parse_price(value: object) -> Optional[float]:
    text = (
        str(value or "")
        .replace(",", "")
        .replace("Q.", "Q")
        .strip()
    )

    match = re.search(
        r"Q?\s*([0-9]{1,3}(?:\.[0-9]{1,2})?)",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    try:
        price = round(float(match.group(1)), 2)
    except (TypeError, ValueError):
        return None

    if 5.00 <= price <= 100.00:
        return price

    return None


def find_autoservice_table(
    soup: BeautifulSoup,
) -> Optional[Tag]:
    """
    Encuentra el encabezado 'Modalidad: autoservicio'
    y devuelve la primera tabla que aparece después.
    """

    headings = soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    )

    for heading in headings:
        heading_text = normalize_text(
            heading.get_text(" ", strip=True)
        )

        if (
            "MODALIDAD" in heading_text
            and "AUTOSERVICIO" in heading_text
        ):
            table = heading.find_next("table")

            if isinstance(table, Tag):
                return table

    # Respaldo: buscar cualquier nodo que contenga el texto.
    autoservice_node = soup.find(
        string=re.compile(
            r"MODALIDAD\s*:?\s*AUTOSERVICIO",
            flags=re.IGNORECASE,
        )
    )

    if autoservice_node:
        parent = autoservice_node.parent

        if isinstance(parent, Tag):
            table = parent.find_next("table")

            if isinstance(table, Tag):
                return table

    return None


def extract_latest_autoservice_diesel(
    page_html: str,
) -> tuple[date, float]:
    soup = BeautifulSoup(
        page_html,
        "html.parser",
    )

    table = find_autoservice_table(soup)

    if table is None:
        raise RuntimeError(
            "No se encontró la tabla de modalidad autoservicio."
        )

    rows = table.find_all("tr")

    if len(rows) < 2:
        raise RuntimeError(
            "La tabla de autoservicio no contiene suficientes filas."
        )

    header_cells = rows[0].find_all(
        ["th", "td"]
    )

    if not header_cells:
        raise RuntimeError(
            "La tabla de autoservicio no tiene encabezados."
        )

    dated_columns: list[tuple[int, date]] = []

    for column_index, cell in enumerate(
        header_cells
    ):
        header_text = normalize_text(
            cell.get_text(" ", strip=True)
        )

        if "PRECIOS MONITOREADOS" not in header_text:
            continue

        header_date = parse_date_value(
            header_text
        )

        if header_date:
            dated_columns.append(
                (
                    column_index,
                    header_date,
                )
            )

    if not dated_columns:
        raise RuntimeError(
            "No se encontraron columnas con fechas "
            "de precios monitoreados."
        )

    latest_column_index, latest_date = max(
        dated_columns,
        key=lambda item: item[1],
    )

    for row in rows[1:]:
        cells = row.find_all(
            ["th", "td"]
        )

        if not cells:
            continue

        product_name = normalize_text(
            cells[0].get_text(
                " ",
                strip=True,
            )
        )

        if product_name not in {
            "DIESEL",
            "COMBUSTIBLE DIESEL",
            "ACEITE COMBUSTIBLE DIESEL",
        }:
            continue

        if latest_column_index >= len(cells):
            raise RuntimeError(
                "La fila de diésel no contiene "
                "la columna más reciente."
            )

        price_text = cells[
            latest_column_index
        ].get_text(
            " ",
            strip=True,
        )

        latest_price = parse_price(
            price_text
        )

        if latest_price is None:
            raise RuntimeError(
                "No fue posible interpretar el precio "
                f"de diésel: {price_text!r}"
            )

        logger.info(
            "Diésel autoservicio detectado: "
            "fecha=%s precio=Q%.2f",
            latest_date,
            latest_price,
        )

        return latest_date, latest_price

    raise RuntimeError(
        "No se encontró la fila 'Combustible Diesel' "
        "dentro de la tabla de autoservicio."
    )


class MemFuelPriceProvider:

    @staticmethod
    def _request_attempts(
        api_key: str,
    ) -> list[dict]:
        common = {
            "api_key": api_key,
            "url": MEM_URL,
            "render_js": "true",
            "block_resources": "false",
            "wait_browser": "networkidle2",
        }

        return [
            {
                "name": "premium_proxy",
                "params": {
                    **common,
                    "wait": "8000",
                    "premium_proxy": "true",
                },
            },
            {
                "name": "stealth_proxy",
                "params": {
                    **common,
                    "wait": "12000",
                    "stealth_proxy": "true",
                },
            },
        ]

    @staticmethod
    def _save_successful_response(
        html_content: str,
        attempt_name: str,
    ) -> None:
        output_path = (
            Path.cwd()
            / f"mem_response_{attempt_name}.html"
        )

        output_path.write_text(
            html_content,
            encoding="utf-8",
        )

        logger.info(
            "HTML exitoso guardado en %s",
            output_path,
        )

    @staticmethod
    def _download_page(
        api_key: str,
    ) -> str:
        errors: list[str] = []

        with httpx.Client(
            timeout=httpx.Timeout(
                connect=30.0,
                read=180.0,
                write=30.0,
                pool=30.0,
            ),
            follow_redirects=True,
        ) as client:

            for attempt in (
                MemFuelPriceProvider
                ._request_attempts(api_key)
            ):
                attempt_name = attempt["name"]

                logger.info(
                    "Consultando MEM con ScrapingBee: %s",
                    attempt_name,
                )

                try:
                    response = client.get(
                        SCRAPINGBEE_API_URL,
                        params=attempt["params"],
                    )
                except httpx.RequestError as exc:
                    errors.append(
                        f"{attempt_name}: "
                        f"error de conexión: {exc}"
                    )
                    continue

                if (
                    response.status_code == 200
                    and response.text.strip()
                ):
                    logger.info(
                        "ScrapingBee respondió correctamente "
                        "usando %s.",
                        attempt_name,
                    )

                    MemFuelPriceProvider._save_successful_response(
                        response.text,
                        attempt_name,
                    )

                    return response.text

                preview = (
                    response.text[:500]
                    .replace("\n", " ")
                )

                errors.append(
                    f"{attempt_name}: "
                    f"HTTP {response.status_code}: "
                    f"{preview}"
                )

                logger.warning(
                    "Intento %s falló: HTTP %s",
                    attempt_name,
                    response.status_code,
                )

        raise RuntimeError(
            "ScrapingBee no pudo obtener la página del MEM. "
            + " | ".join(errors)
        )

    @staticmethod
    def fetch_current_diesel_price(
    ) -> MemFuelPriceResult:
        api_key = os.getenv(
            "SCRAPINGBEE_API_KEY",
            "",
        ).strip()

        if not api_key:
            raise RuntimeError(
                "Falta la variable de entorno "
                "SCRAPINGBEE_API_KEY."
            )

        page_html = (
            MemFuelPriceProvider
            ._download_page(api_key)
        )

        latest_date, latest_price = (
            extract_latest_autoservice_diesel(
                page_html
            )
        )

        return MemFuelPriceResult(
            fecha=latest_date,
            precio_diesel=latest_price,
            fuente=MEM_URL,
            vigencia_inicio=latest_date,
            vigencia_fin=latest_date,
        )