from pydantic import BaseModel as PydanticBaseModel

class BaseModel(PydanticBaseModel):
    """Base model for all models in the system, extends Pydantic BaseModel"""
    class Config:
        arbitrary_types_allowed = True 