import time
import re
from typing import List, Dict, Any
from src.engines.base import BaseDataEngine, EngineResult
from src.providers.llm import get_chat_model

class BaselineDataEngine(BaseDataEngine):
    """
    Baseline DLS Engine:
    Direct full-text prompt stuffing into LLM context window.
    """
    def __init__(self, provider: str = "opencode", model: str = None):
        self.provider = provider
        self.model = model
        self.documents: List[Dict[str, Any]] = []
        self.llm = get_chat_model(provider=provider, model=model)

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        self.documents = documents

    def query(self, question: str) -> EngineResult:
        start_time = time.perf_counter()

        context_blocks = []
        for i, doc in enumerate(self.documents, 1):
            title = doc.get("title", f"출처 {i}")
            url = doc.get("url", "")
            content = doc.get("content", "")[:2500]
            context_blocks.append(f"[출처 {i}: {title}]\nURL: {url}\n본문:\n{content}\n")

        context_str = "\n".join(context_blocks)
        prompt = f"""당신은 전문 리서치 애널리스트입니다.
아래 제공된 출처 데이터만을 근거로 다음 질문에 대해 정밀하게 답변하고, 문장 끝에 반드시 출처 각주 [^번호]를 명시하세요.

질문: {question}

참고 데이터:
{context_str}

답변 끝에 사용한 각주 번호와 URL 목록을 작성하세요:
[^1]: URL
"""
        response = self.llm.invoke(prompt)
        raw_text = response.content if isinstance(response.content, str) else str(response.content)
        answer = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()

        latency = time.perf_counter() - start_time

        # Extract citations
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
            engine_name="Baseline (Prompt Stuffing)"
        )
