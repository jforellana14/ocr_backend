# Backend limpio Transportes JDA RC3

## Fuente única
- `main.py`: entrada de Render (`uvicorn main:app`).
- `models.py`, `schemas.py`, `database.py`, `auth.py`: únicos archivos raíz de infraestructura.
- Se eliminaron duplicados antiguos dentro de `app/`.

## Finanzas
`FinancialEngine` alimenta Dashboard y Estado de Resultados con exactamente los mismos datos.
Incluye ingresos, combustible con precio snapshot, bonificaciones, costos directos, gastos operativos, administrativos/fijos, financieros, otros gastos, ISR proyectado y utilidad neta.
Los gastos recurrentes se reconocen proporcionalmente por día para que el Dashboard diario sea realista.

## Endpoints
- `GET /reports/dashboard-summary?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`
- `GET /reports/income-statement?year=2026&month=7`
- También acepta `date_from/date_to` en income-statement.

## Despliegue
1. Configure `DATABASE_URL`, `SECRET_KEY` y credenciales de Cloudinary.
2. Instale: `pip install -r requirements.txt`.
3. Ejecute: `uvicorn main:app --host 0.0.0.0 --port 8000`.

No incluya en Git: `.env`, `venv`, `__pycache__`, bases SQLite, uploads ni exports generados.
