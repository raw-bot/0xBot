"""LLM client interface for multiple AI providers."""

import asyncio
import json
import os
from time import time
from typing import Any, Dict, Optional, cast

from anthropic import AsyncAnthropic
from anthropic.types import TextBlock
from openai import AsyncOpenAI

from ..core.config import config
from ..core.logger import get_logger

logger = get_logger(__name__)


# Cost per million tokens for each provider
MODEL_COSTS = {
    "claude": {"input": 3.0, "output": 15.0},
    "gpt": {"input": 10.0, "output": 30.0},
    "deepseek": {"input": 0.14, "output": 0.28},
    "qwen": {"input": 0.20, "output": 0.60},
}


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int = 10) -> None:
        self.calls_per_minute = calls_per_minute
        self.calls: list[float] = []

    async def acquire(self) -> None:
        """Wait if rate limit is reached."""
        now = time()
        self.calls = [t for t in self.calls if now - t < 60]
        if len(self.calls) >= self.calls_per_minute:
            wait_time = 60 - (now - self.calls[0])
            logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            self.calls = []
        self.calls.append(time())


class LLMClient:
    """Unified interface for multiple LLM providers (Claude, GPT, DeepSeek, Qwen)."""

    def __init__(self) -> None:
        """Initialize LLM clients with lazy initialization."""
        self._anthropic_client: Optional[AsyncAnthropic] = None
        self._openai_client: Optional[AsyncOpenAI] = None
        self._deepseek_client: Optional[AsyncOpenAI] = None
        self._qwen_client: Optional[AsyncOpenAI] = None
        self._rate_limiter = RateLimiter(config.LLM_CALLS_PER_MINUTE)

    @property
    def anthropic_client(self) -> AsyncAnthropic:
        """Lazy initialize Anthropic client."""
        if self._anthropic_client is None:
            self._anthropic_client = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY", ""))
        return self._anthropic_client

    @property
    def openai_client(self) -> AsyncOpenAI:
        """Lazy initialize OpenAI client."""
        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        return self._openai_client

    @property
    def deepseek_client(self) -> AsyncOpenAI:
        """Lazy initialize DeepSeek client."""
        if self._deepseek_client is None:
            self._deepseek_client = AsyncOpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                base_url="https://api.deepseek.com/v1"
            )
        return self._deepseek_client

    @property
    def qwen_client(self) -> AsyncOpenAI:
        """Lazy initialize Qwen client."""
        if self._qwen_client is None:
            self._qwen_client = AsyncOpenAI(
                api_key=os.getenv("QWEN_API_KEY", ""),
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            )
        return self._qwen_client

    async def analyze_market(
        self, model: str, prompt: str, max_tokens: int = 1024, temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Analyze market using specified LLM model."""
        model_lower = model.lower()
        await self._rate_limiter.acquire()

        if "claude" in model_lower:
            return await self._call_claude(prompt, max_tokens, temperature)
        elif "gpt" in model_lower:
            return await self._call_openai(prompt, max_tokens, temperature, "gpt")
        elif "deepseek" in model_lower:
            return await self._call_openai(prompt, max_tokens, temperature, "deepseek")
        elif "qwen" in model_lower:
            return await self._call_openai(prompt, max_tokens, temperature, "qwen")
        else:
            raise ValueError(
                f"Unsupported model: {model}. Supported: claude-4.5-sonnet, gpt-4, deepseek-v3, qwen-max"
            )

    async def _call_claude(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> Dict[str, Any]:
        """Call Claude API."""
        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            raw_response = cast(TextBlock, response.content[0]).text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            tokens_used = input_tokens + output_tokens

            parsed_decisions = self._parse_json_response(raw_response)
            total_cost = self._calculate_cost("claude", input_tokens, output_tokens)

            logger.info(f"Claude response: {tokens_used} tokens, ${total_cost:.6f}")

            return {
                "response": raw_response,
                "parsed_decisions": parsed_decisions,
                "tokens_used": tokens_used,
                "cost": total_cost,
            }
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            raise

    async def _call_openai(
        self, prompt: str, max_tokens: int, temperature: float, provider: str
    ) -> Dict[str, Any]:
        """Call OpenAI-compatible API (GPT, DeepSeek, Qwen)."""
        try:
            client_map = {
                "gpt": (self.openai_client, "gpt-4-turbo-preview"),
                "deepseek": (self.deepseek_client, "deepseek-chat"),
                "qwen": (self.qwen_client, "qwen-max"),
            }
            client, model_name = client_map[provider]

            messages = [{"role": "user", "content": prompt}]
            if provider == "qwen":
                messages.insert(0, {
                    "role": "system",
                    "content": "You are a trading assistant. Respond with valid JSON only."
                })

            response = await client.chat.completions.create(
                model=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,  # type: ignore[arg-type]
            )

            raw_response = response.choices[0].message.content or ""
            usage = response.usage
            tokens_used = usage.total_tokens if usage else 0

            parsed_decisions = self._parse_json_response(raw_response)

            if usage:
                total_cost = self._calculate_cost(provider, usage.prompt_tokens, usage.completion_tokens)
            else:
                total_cost = 0.0

            logger.info(f"{provider.upper()} response: {tokens_used} tokens, ${total_cost:.6f}")

            return {
                "response": raw_response,
                "parsed_decisions": parsed_decisions,
                "tokens_used": tokens_used,
                "cost": total_cost,
            }
        except Exception as e:
            logger.error(f"Error calling {provider.upper()} API: {e}")
            raise

    def _calculate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        costs = MODEL_COSTS.get(provider, MODEL_COSTS["gpt"])
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return input_cost + output_cost

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}")

            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx : end_idx + 1]
                return cast(Dict[str, Any], json.loads(json_str))

            return cast(Dict[str, Any], json.loads(response))
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from response: {e}")
            return {
                "action": "hold",
                "reasoning": "Failed to parse LLM response",
                "raw_response": response,
            }


_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
