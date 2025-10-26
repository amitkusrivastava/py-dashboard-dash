from . import config
from .server import create_server, create_cache, create_app
from .auth import init_auth
from .data import set_cache
from .ui import serve_layout
from .callbacks import register_callbacks

# Assemble
server = create_server()
cache = create_cache(server)
app = create_app(server)

# Init subsystems
init_auth(server)
set_cache(cache)
app.layout = serve_layout
register_callbacks(app)

__all__ = ["app", "server"]
