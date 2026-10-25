# Gestor de Inventario Inteligente
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
Abrir http://127.0.0.1:8000  (demo: admin@atelier.es / admin123) · API docs: /docs
