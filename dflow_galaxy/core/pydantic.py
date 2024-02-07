import pydantic

class BaseModel(pydantic.BaseModel):
    class Config:
        extra = 'forbid'
