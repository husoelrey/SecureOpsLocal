from typing import List, Dict
from src.schemas.rag import DocumentChunk

class KnowledgeStore:
    def __init__(self):
        self.sources: Dict[str, dict] = {}
        self.chunks: List[DocumentChunk] = []

    def add_source(self, document_id: str, filename: str, sha256: str, size: int):
        self.sources[document_id] = {
            "id": document_id,
            "filename": filename,
            "sha256": sha256,
            "size": size,
        }

    def get_sources(self) -> List[dict]:
        return list(self.sources.values())
        
    def get_all_chunks(self) -> List[DocumentChunk]:
        return self.chunks
        
    def clear(self):
        self.sources.clear()
        self.chunks.clear()

global_knowledge_store = KnowledgeStore()
