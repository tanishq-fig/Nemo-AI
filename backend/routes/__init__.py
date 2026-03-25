"""Routes package initialization."""
from . import auth_routes
from . import chat_routes
from . import data_routes
from . import visualization_routes
from . import live_routes

__all__ = ['auth_routes', 'chat_routes', 'data_routes', 'visualization_routes', 'live_routes']
