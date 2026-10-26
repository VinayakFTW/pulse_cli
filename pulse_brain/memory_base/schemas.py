from pydantic import BaseModel

class RemoteRequest(BaseModel):
    secret_key: str
    directory: str
    query: str