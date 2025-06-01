# Load module before others to prevent partially initialized modules
from .strategy import ConnectionStrategy  # noqa: F401
