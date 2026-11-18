from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints
from typing import Annotated

Username = Annotated[str, StringConstraints(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")]
Password = Annotated[str, StringConstraints(min_length=6, max_length=128)]

class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: Username
    password: Password

class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    password: str

class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    destino: Username
    valor: StrictInt = Field(gt=0)
