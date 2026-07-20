# Ejecutar localmente (Windows PowerShell)

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

Pruebas:

```powershell
python -m pytest -q
```
