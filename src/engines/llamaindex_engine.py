import time
import re
from typing import List, Dict, Any
from src.engines.base import BaseDataEngine, EngineResult
from src.providers.llm import get_chat_model

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter

class LlamaIndexDataEngine(BaseDataEngine):
    """
    LlamaIndex-Enhanced Engine:
    In-memory chunking (SentenceSplitter), relevance scoring, and citation tracking.
    """
    def __init__(self, provider: str = "opencode", model: str = None, chunk_size: int = 512):
        self.provider = provider
        self.model = model
        self.chunk_size = chunk_size
        self.documents: List[Document] = []
        self.nodes = []
        self.splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=50)
        self.llm = get_chat_model(provider=provider, model=model)

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        self.documents = []
        for i, doc in enumerate(documents, 1):
            title = doc.get("title", f"출처 {i}")
            url = doc.get("url", "")
            content = doc.get("content", "")
            if content:
                self.documents.append(
                    Document(
                        text=content,
                        metadata={
                            "doc_id": i,
                            "title": title,
                            "url": url
                        }
                    )
                )

        # Parse into sentence-level nodes
        self.nodes = self.splitter.get_nodes_from_documents(self.documents)

    def _rank_nodes(self, question: str, top_k: int = 4) -> List[Any]:
        """Simple TF-IDF / term-overlap ranking to select highest relevance nodes."""
        q_terms = set(re.findall(r'\w+', question.lower()))
        scored_nodes = []
        for node in self.nodes:
            node_terms = re.findall(r'\w+', node.text.lower())
            if not node_terms:
                continue
            # Overlap score
            overlap = sum(1 for t in node_terms if t in q_terms)
            score = overlap / len(node_terms)
            scored_nodes.append((score, node))

        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        return [node for score, node in scored_nodes[:top_k]]

    def query(self, question: str) -> EngineResult:
        start_time = time.perf_counter()

        selected_nodes = self._rank_nodes(question, top_k=4)
        if not selected_nodes and self.nodes:
            selected_nodes = self.nodes[:4]

        # Format context with citation markers
        context_blocks = []
        seen_urls = {}
        for node in selected_nodes:
            url = node.metadata.get("url", "")
            title = node.metadata.get("title", "")
            doc_id = node.metadata.get("doc_id", len(seen_urls) + 1)
            if url not in seen_urls:
                seen_urls[url] = len(seen_urls) + 1
            ref_idx = seen_urls[url]
            context_blocks.append(f"[출처 {ref_idx}: {title}]\nURL: {url}\n발췌문:\n{node.text}\n")

        context_str = "\n".join(context_blocks)
        prompt = f"""당신은 LlamaIndex 기반 정밀 인용 리서치 엔진입니다.
아래 선별된 고순도 발췌 데이터만을 바탕으로 질문에 대해 명확하게 답변하고, 각 팩트마다 출처 번호 각주 [^{{번호}}]를 매핑하세요.

질문: {question}

선별된 발췌 데이터:
{context_str}

답변 끝에 사용한 각주 번호와 URL 목록을 작성하세요:
[^1]: URL
"""
        response = self.llm.invoke(prompt)
        raw_text = response.content if isinstance(response.content, str) else str(response.content)
        answer = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()

        latency = time.perf_counter() - start_time

        citations = []
        for m in re.finditer(r'\[\^(\d+)\]:\s*(\S+)', answer):
            citations.append({
                "index": int(m.group(1)),
                "url": m.group(2)
            })

        tokens = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens = response.usage_metadata

        return EngineResult(
            answer=answer,
            citations=citations,
            latency_sec=latency,
            token_usage=tokens,
            engine_name="LlamaIndex (Chunking & Reranked)"
        )
