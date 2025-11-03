from typing import Dict, Any, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from mindiv.config import get_config

router = APIRouter()


class ModelInfo(BaseModel):
    id: str
    provider: str
    model: str
    level: Optional[str] = None
    features: Optional[Dict[str, Any]] = None


@router.get("/v1/models")
async def list_models() -> Dict[str, Any]:
    cfg = get_config()
    items: List[ModelInfo] = []
    for mid, model_config in cfg.models.items():
        items.append(ModelInfo(
            id=mid,
            provider=model_config.provider,
            model=model_config.model,
            level=model_config.level,
            features={
                "max_iterations": model_config.max_iterations,
                "required_verifications": model_config.required_verifications,
                "enable_planning": model_config.enable_planning,
                "enable_parallel_check": model_config.enable_parallel_check,
            },
        ))
    return {"data": [m.model_dump() for m in items]}

