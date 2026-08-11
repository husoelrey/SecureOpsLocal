from pydantic import BaseModel, Field

class IngestedDocument(BaseModel):
    filename: str = Field(..., description="The original filename")
    content: str = Field(..., description="The extracted text content")
    sha256: str = Field(..., description="SHA-256 hash of the uploaded file")
    metadata: dict[str, str | int] = Field(default_factory=dict, description="Metadata such as size, pages, format")

class IngestionResponse(BaseModel):
    message: str
    document_id: str | None = None
    sha256: str
    size: int
