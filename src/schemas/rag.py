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

class DocumentChunk(BaseModel):
    chunk_id: str = Field(..., description="Stable unique identifier for the chunk")
    document_id: str = Field(..., description="ID of the parent document")
    source_title: str = Field(..., description="Title of the source document")
    section_or_page: str = Field(..., description="Heading path or page reference")
    content: str = Field(..., description="The chunk text")
    word_count: int = Field(..., description="Number of words in the chunk")


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    source_title: str
    section_or_page: str
    content: str
    score: float
