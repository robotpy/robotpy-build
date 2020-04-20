import os
from pydantic import BaseModel

# Needed because pydantic gets in the way of generating good docs
_generating_documentation = bool(os.environ.get("GENERATING_DOCUMENTATION"))
if _generating_documentation:
    BaseModel = object


class Model(BaseModel):
    class Config:
        extra = "forbid"
