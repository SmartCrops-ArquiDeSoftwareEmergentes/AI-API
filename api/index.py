# Vercel Serverless Function entrypoint for FastAPI (ASGI)
# Exposes the FastAPI `app` at the module level so Vercel can serve it.

from app.main import app as _fastapi_app

# Vercel expects a variable named `app` which is an ASGI or WSGI application.
app = _fastapi_app

