"""
Shared slowapi rate limiter instance.

Kept in its own module rather than defined in main.py so router modules
(backend/routers/analyze.py) can import it and apply @limiter.limit(...)
decorators without a circular import — main.py itself imports those router
modules to register them.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# headers_enabled=True makes successful responses carry X-RateLimit-* /
# Retry-After headers too (not just the 429), which requires each limited
# endpoint to accept a `response: Response` parameter — see
# backend/routers/analyze.py.
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
