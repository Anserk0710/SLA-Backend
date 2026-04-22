import os
import sys
from pathlib import Path

from a2wsgi import ASGIMiddleware

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("PYTHON_EGG_CACHE", str(BASE_DIR / ".python-eggs"))

from app.main import app as asgi_app

application = ASGIMiddleware