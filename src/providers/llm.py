import os
from typing import List, Optional, Any
import requests
from pydantic import Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils.config import get_config

class OllamaChatModel(BaseChatModel):
    """
    Lightweight, native LangChain-compatible ChatModel for local Ollama instances.
    """
    model_name: str = Field(default="qwen3.8:27b")
    base_url: str = Field(default="http://localhost:11434")
    temperature: float = Field(default=0.3)
    timeout_sec: int = Field(default=600)
    num_predict: Optional[int] = Field(default=3500)
    num_ctx: int = Field(default=16384)

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

        options = {
            "temperature": self.temperature,
            "num_ctx": self.num_ctx
        }
        if self.num_predict is not None:
            options["num_predict"] = self.num_predict
        if stop:
            options["stop"] = stop

        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "stream": True,
            "options": options
        }

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

class OpenCodeChatModel(BaseChatModel):
    """
    ChatModel integrating with OpenCode API Server (REST) or CLI fallback.
    Default model: opencode/muse-spark-1.3-contributor-free (Free Muse Spark).
    """
    model_name: str = Field(default="opencode/muse-spark-1.3-contributor-free")
    base_url: Optional[str] = Field(default=None)
    agent: str = Field(default="build")
    timeout_sec: int = Field(default=180)

    @property
    def _llm_type(self) -> str:
        return "opencode-api"

    def _discover_base_url(self) -> Optional[str]:
        def _is_server_alive(url: str) -> bool:
            try:
                r = requests.get(f"{url}/api/health", timeout=0.3)
                return r.status_code == 200
            except Exception:
                return False

        if self.base_url:
            clean = self.base_url.rstrip("/")
            if _is_server_alive(clean):
                return clean

        env_url = os.getenv("OPENCODE_BASE_URL")
        if env_url:
            clean = env_url.rstrip("/")
            if _is_server_alive(clean):
                return clean

        env_port = os.getenv("OPENCODE_PORT")
        if env_port:
            clean = f"http://127.0.0.1:{env_port}"
            if _is_server_alive(clean):
                return clean

        # Try to detect from running processes (e.g. opencode --port 36629)
        try:
            ps_out = subprocess.check_output(["ps", "aux"], text=True, stderr=subprocess.DEVNULL)
            for line in ps_out.splitlines():
                if "opencode" in line and "--port" in line:
                    match = re.search(r"--port\s+(\d+)", line)
                    if match:
                        port = match.group(1)
                        clean = f"http://127.0.0.1:{port}"
                        if _is_server_alive(clean):
                            return clean
        except Exception:
            pass

        # Try common ports
        candidate_ports = [36629, 4000, 3000, 8080]
        for port in candidate_ports:
            clean = f"http://127.0.0.1:{port}"
            if _is_server_alive(clean):
                return clean

        return None

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        import subprocess, requests, json, time, re, shutil

        prompt_texts = []
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if isinstance(msg, SystemMessage):
                prompt_texts.append(f"[System Instruction]\n{content}")
            elif isinstance(msg, HumanMessage):
                prompt_texts.append(content)
            elif isinstance(msg, AIMessage):
                prompt_texts.append(f"[Assistant]\n{content}")
            else:
                prompt_texts.append(content)

        full_prompt = chr(10).join(prompt_texts)
        active_url = self._discover_base_url()

        # Method 1: If OpenCode HTTP API Server is reachable
        if active_url:
            try:
                clean_model_id = self.model_name.replace("opencode/", "")
                session_payload = {
                    "agent": self.agent,
                    "model": {
                        "id": clean_model_id,
                        "providerID": "opencode",
                        "variant": "default"
                    }
                }
                res = requests.post(f"{active_url}/api/session", json=session_payload, timeout=10)
                if res.status_code != 200:
                    raise RuntimeError(f"Failed to create session: {res.text}")
                session_id = res.json()["data"]["id"]

                prompt_payload = {
                    "prompt": {
                        "text": full_prompt
                    }
                }
                res = requests.post(f"{active_url}/api/session/{session_id}/prompt", json=prompt_payload, timeout=10)
                if res.status_code != 200:
                    raise RuntimeError(f"Failed to send prompt: {res.text}")

                start_time = time.time()
                reply_text = None
                tokens_info = {}

                while time.time() - start_time < self.timeout_sec:
                    time.sleep(0.5)
                    hist_res = requests.get(f"{active_url}/api/session/{session_id}/history", timeout=10)
                    if hist_res.status_code == 200:
                        events = hist_res.json().get("data", [])
                        for ev in events:
                            if ev.get("type") == "session.next.text.ended":
                                reply_text = ev["data"].get("text", "")
                            if ev.get("type") == "session.next.step.ended":
                                tokens_info = ev["data"].get("tokens", {})

                        if reply_text is not None:
                            break

                if reply_text is None:
                    raise TimeoutError(f"OpenCode API timed out after {self.timeout_sec}s waiting for response.")

                generation = ChatGeneration(
                    message=AIMessage(
                        content=reply_text.strip(),
                        usage_metadata={
                            "input_tokens": tokens_info.get("input", 0),
                            "output_tokens": tokens_info.get("output", 0),
                            "total_tokens": tokens_info.get("input", 0) + tokens_info.get("output", 0)
                        }
                    )
                )
                return ChatResult(generations=[generation])

            except Exception as e:
                try:
                    print(f"[OpenCode API Warning: {e}] -> opencode CLI로 대체 시도합니다...")
                except (OSError, IOError):
                    pass

        # Method 2: Fallback to CLI opencode run
        try:
            opencode_bin = shutil.which("opencode") or "/Users/boon/.opencode/bin/opencode"
            cmd = [opencode_bin, "run", full_prompt, "-m", self.model_name]
            result = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec
            )
            if result.returncode == 0:
                raw_out = result.stdout.strip()
                clean_lines = [l for l in raw_out.splitlines() if not l.startswith("> ") and not l.startswith("timestamp=")]
                reply_text = chr(10).join(clean_lines).strip()
                generation = ChatGeneration(
                    message=AIMessage(content=reply_text)
                )
                return ChatResult(generations=[generation])
            else:
                raise RuntimeError(f"OpenCode CLI failed: {result.stderr}")
        except Exception as cli_err:
            raise RuntimeError(f"Failed to query OpenCode via both API and CLI: {cli_err}")


class NormalizedGeminiChat(ChatGoogleGenerativeAI):
    """
    Wrapper around ChatGoogleGenerativeAI ensuring message.content is always
    a clean string, and automatically falls back if quota is exhausted.
    """
    def _generate(self, *args, **kwargs):
        fallback_models = ["gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.6-flash"]
        curr_model = self.model
        attempt_models = [curr_model] + [m for m in fallback_models if m != curr_model]

        last_error = None
        for m in attempt_models:
            try:
                if m == curr_model:
                    res = super()._generate(*args, **kwargs)
                else:
                    backup_llm = ChatGoogleGenerativeAI(
                        model=m,
                        google_api_key=self.google_api_key,
                        temperature=self.temperature
                    )
                    res = backup_llm._generate(*args, **kwargs)

                # Normalize content to string
                for gen in res.generations:
                    if isinstance(gen.message.content, list):
                        text_parts = [
                            p.get("text", "") if isinstance(p, dict) else str(p)
                            for p in gen.message.content
                        ]
                        gen.message.content = "".join(text_parts)
                return res
            except Exception as e:
                err_str = str(e)
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                    try:
                        print(f"\n⚠️ [Gemini Quota Auto-Fallback] {m} 할당량 초과 -> 다음 가용 모델로 자동 전환합니다.")
                    except (OSError, IOError):
                        pass
                    last_error = e
                    continue
                else:
                    raise e

        if last_error:
            raise last_error

def get_chat_model(
    tier: str = "standard",
    temperature: Optional[float] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> BaseChatModel:
    """
    Get a chat model instance based on the requested tier ('fast', 'standard', 'deep')
    or explicit provider ('ollama', 'gemini', 'meta_muse', 'groq', 'openai') and model name.
    """
    cfg = get_config().get("llm", {})
    tier_cfg = cfg.get("tiers", {}).get(tier, {})

    target_provider = (provider or tier_cfg.get("provider", cfg.get("default_provider", "gemini"))).lower()
    temp = temperature if temperature is not None else tier_cfg.get("temperature", 0.2)

    if target_provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        model_name = model or (tier_cfg.get("model") if tier_cfg.get("provider") == "gemini" else "gemini-3.5-flash")
        return NormalizedGeminiChat(
            model=model_name,
            google_api_key=api_key,
            temperature=temp
        )

    elif target_provider == "ollama":
        ollama_cfg = cfg.get("ollama", {})
        base_url = os.getenv("OLLAMA_BASE_URL", ollama_cfg.get("base_url", "http://localhost:11434"))
        model_name = model or (tier_cfg.get("model") if tier_cfg.get("provider") == "ollama" else ollama_cfg.get("default_model", "qwen3.8:27b"))
        num_predict = tier_cfg.get("num_predict", 500 if tier == "fast" else 3500)
        return OllamaChatModel(
            model_name=model_name,
            base_url=base_url,
            temperature=temp,
            timeout_sec=600,
            num_predict=num_predict,
            num_ctx=16384
        )

    elif target_provider in ["meta_muse", "meta"]:
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("META_API_KEY") or os.getenv("MUSE_API_KEY") or "dummy"
        base_url = os.getenv("META_API_BASE", "https://api.meta.ai/v1")
        model_name = model or "muse-spark-1.3"
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temp
        )

    elif target_provider in ["opencode", "opencode_api", "muse"]:
        opencode_cfg = cfg.get("opencode", {})
        base_url = os.getenv("OPENCODE_BASE_URL", opencode_cfg.get("base_url"))
        model_name = model or opencode_cfg.get("default_model", "opencode/muse-spark-1.3-contributor-free")
        agent = opencode_cfg.get("agent", "build")
        return OpenCodeChatModel(
            model_name=model_name,
            base_url=base_url,
            agent=agent,
            timeout_sec=240
        )

    elif target_provider == "groq":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("GROQ_API_KEY", "")
        return ChatOpenAI(
            model=model or "llama-3.3-70b-versatile",
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=temp
        )

    elif target_provider == "openai":
        from langchain_openai import ChatOpenAI
        model_name = model or tier_cfg.get("model", "gpt-4o-mini")
        return ChatOpenAI(
            model=model_name,
            temperature=temp
        )

    else:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return NormalizedGeminiChat(model="gemini-3.5-flash", google_api_key=api_key, temperature=temp)
