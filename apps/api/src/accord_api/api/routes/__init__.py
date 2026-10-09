from .agreements import router as agreements_router
from .assignments import router as assignments_router
from .constraints import router as constraints_router
from .demo import router as demo_router
from .drift import router as drift_router
from .households import router as households_router
from .interviews import router as interviews_router
from .monitoring import router as monitoring_router

__all__ = [
    "households_router",
    "interviews_router",
    "constraints_router",
    "agreements_router",
    "assignments_router",
    "monitoring_router",
    "drift_router",
    "demo_router",
]
