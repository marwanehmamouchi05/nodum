"""Read-only discovery of explicitly configured synthetic demo controls."""
import os
from fastapi import APIRouter, Depends
from app.api.authorization import require_scoped_context
from app.models.authorization import Permission as P
from app.services.authorization import authorization_mode
from app.config import boolean

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.get("/context")
def demo_context(auth=Depends(require_scoped_context)):
    # Never advertise simulation controls for an ordinary production installation.
    if (authorization_mode() != "scoped" or (os.getenv("APP_ENV", "development") != "development" and not boolean("NODUM_JUDGE_DEMO"))
            or os.getenv("RING_MODE") != "simulation"):
        return {"available": False}
    binding = auth.repository.get_resource_binding("simulation", "ring")
    node = auth.repository.get_structure_node(binding.scope_id) if binding else None
    if not node or not node.demo or not auth.allowed(P.SIMULATION_RUN, "simulation", "ring"):
        return {"available": False}
    return {"available": True, "building": node.name}
