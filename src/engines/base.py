from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel

class EngineResult(BaseModel):
    answer: str
    citations: List[Dict[str, Any]] = []
    latency_sec: float
    token_usage: Dict[str, int] = {}
    engine_name: str

class BaseDataEngine(ABC):
    @abstractmethod
    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Index or prepare documents for retrieval."""
        pass

    @abstractmethod
    def query(self, question: str) -> EngineResult:
        """Synthesize answer with source citations."""
        pass
