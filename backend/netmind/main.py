"""
Application entry point.

Exposes the ASGI application instance for uvicorn:
  uvicorn netmind.main:app

Creates the app via factory so it is always initialized through the
same code path regardless of how it is invoked.
"""

from netmind.app import create_app

app = create_app()
