import os
from typing import List, Optional, Any
import requests
from pydantic import Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from src.utils.config import get_config

class OllamaChatModel(BaseChatModel):
    """
    Lightweight, native LangChain-compatible ChatModel for local Ollama instances.
    Requires no extra dependencies beyond requests and langchain-core.
    """
    model_name: str = Field(default="qwen3.8:27b")
    base_url: str = Field(default="http://localhost:11434")
    temperature: float = Field(default=0.3)
    timeout_sec: int = Field(default=300)

    @property
    def _llm_type(self) -> str:
        return "ollama-local"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            elif isinstance(msg, SystemMessage):
                role = "system"
            else:
                role = "user"

            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            formatted_messages.append({"role": role, "content": content})

        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "stream": True,
            "options": {
                "temperature": self.temperature
            }
        }
        if stop:
            payload["options"]["stop"] = stop

        endpoint = f"{self.base_url.rstrip('/')}/api/chat"
        try:
            import json
            resp = requests.post(endpoint, json=payload, stream=True, timeout=self.timeout_sec)
            resp.raise_for_status()

            reply_text = ""
            prompt_tokens = 0
            completion_tokens = 0

            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    part = chunk.get("message", {}).get("content", "")
                    reply_text += part
                    if chunk.get("done"):
                        prompt_tokens = chunk.get("prompt_eval_count", 0)
                        completion_tokens = chunk.get("eval_count", 0)

            reply_text = reply_text.strip()

            generation = ChatGeneration(
                message=AIMessage(
                    content=reply_text,
                    usage_metadata={
                        "input_tokens": prompt_tokens,
                        "output_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens
                    }
                )
            )
            return ChatResult(generations=[generation])

        except Exception as e:
            raise RuntimeError(f"Failed to query Ollama at {endpoint}: {e}")

def get_chat_model(tier: str = "standard", temperature: Optional[float] = None) -> BaseChatModel:
    """
    Get a chat model instance based on the requested tier ('fast', 'standard', 'deep').
    Configured in config/settings.yaml (default: Ollama qwen3.8:27b).
    """
    cfg = get_config().get("llm", {})
    tier_cfg = cfg.get("tiers", {}).get(tier, {})

    provider = tier_cfg.get("provider", cfg.get("default_provider", "ollama")).lower()
    temp = temperature if temperature is not None else tier_cfg.get("temperature", 0.3)

    if provider == "ollama":
        ollama_cfg = cfg.get("ollama", {})
        base_url = os.getenv("OLLAMA_BASE_URL", ollama_cfg.get("base_url", "http://localhost:11434"))
        model_name = tier_cfg.get("model", ollama_cfg.get("default_model", "qwen3.8:27b"))
        return OllamaChatModel(
            model_name=model_name,
            base_url=base_url,
            temperature=temp
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        model_name = tier_cfg.get("model", "gemini-2.5-flash")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temp
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        model_name = tier_cfg.get("model", "gpt-4o-mini")
        return ChatOpenAI(
            model=model_name,
            temperature=temp
        )

    else:
        # Default fallback to Ollama
        return OllamaChatModel(model_name="qwen3.8:27b", temperature=temp)
