"""LLM client interface for multiple AI providers."""

import json
import os
from typing import Any, Dict, Optional

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from ..core.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """
    Unified interface for multiple LLM providers.
    
    Supports: Claude (Anthropic), GPT (OpenAI), DeepSeek, Qwen
    """
    
    def __init__(self):
        """Initialize LLM clients (lazy initialization)."""
        self._anthropic_client = None
        self._openai_client = None
        self._deepseek_client = None
        self._qwen_client = None
    
    @property
    def anthropic_client(self):
        """Lazy initialize Anthropic client."""
        if self._anthropic_client is None:
            self._anthropic_client = AsyncAnthropic(
                api_key=os.getenv("CLAUDE_API_KEY", "")
            )
        return self._anthropic_client
    
    @property
    def openai_client(self):
        """Lazy initialize OpenAI client."""
        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY", "")
            )
        return self._openai_client
    
    @property
    def deepseek_client(self):
        """Lazy initialize DeepSeek client."""
        if self._deepseek_client is None:
            self._deepseek_client = AsyncOpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                base_url="https://api.deepseek.com/v1"
            )
        return self._deepseek_client
    
    @property
    def qwen_client(self):
        """Lazy initialize Qwen client."""
        if self._qwen_client is None:
            self._qwen_client = AsyncOpenAI(
                api_key=os.getenv("QWEN_API_KEY", ""),
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
            )
        return self._qwen_client
    
    async def analyze_market(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analyze market using specified LLM model.
        
        Args:
            model: Model name ('claude-4.5-sonnet', 'gpt-4', 'deepseek-v3', 'qwen-max')
            prompt: Market analysis prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            
        Returns:
            Dict with 'response' (str), 'parsed_decisions' (dict), 'tokens_used' (int), 'cost' (float)
        """
        model_lower = model.lower()
        
        if "claude" in model_lower:
            return await self._call_claude(prompt, max_tokens, temperature)
        elif "gpt" in model_lower:
            return await self._call_openai(prompt, max_tokens, temperature)
        elif "deepseek" in model_lower:
            return await self._call_deepseek(prompt, max_tokens, temperature)
        elif "qwen" in model_lower:
            return await self._call_qwen(prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Unsupported model: {model}. Supported: claude-4.5-sonnet, gpt-4, deepseek-v3, qwen-max")
    
    async def _call_claude(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Call Claude API."""
        try:
            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",  # Latest Claude model
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            raw_response = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            # Parse JSON from response
            parsed_decisions = self._parse_json_response(raw_response)
            
            # Estimate cost (Claude Sonnet: ~$3 per 1M input tokens, $15 per 1M output tokens)
            input_cost = (response.usage.input_tokens / 1_000_000) * 3.0
            output_cost = (response.usage.output_tokens / 1_000_000) * 15.0
            total_cost = input_cost + output_cost
            
            logger.info(f"Claude response: {tokens_used} tokens, ${total_cost:.6f}")
            
            return {
                "response": raw_response,
                "parsed_decisions": parsed_decisions,
                "tokens_used": tokens_used,
                "cost": total_cost
            }
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            raise
    
    async def _call_openai(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Call OpenAI GPT API."""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            raw_response = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Parse JSON from response
            parsed_decisions = self._parse_json_response(raw_response)
            
            # Estimate cost (GPT-4 Turbo: ~$10 per 1M input tokens, $30 per 1M output tokens)
            if response.usage:
                input_cost = (response.usage.prompt_tokens / 1_000_000) * 10.0
                output_cost = (response.usage.completion_tokens / 1_000_000) * 30.0
                total_cost = input_cost + output_cost
            else:
                total_cost = 0.0
            
            logger.info(f"GPT-4 response: {tokens_used} tokens, ${total_cost:.6f}")
            
            return {
                "response": raw_response,
                "parsed_decisions": parsed_decisions,
                "tokens_used": tokens_used,
                "cost": total_cost
            }
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise
    
    async def _call_deepseek(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Call DeepSeek API."""
        try:
            response = await self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            raw_response = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Parse JSON from response
            parsed_decisions = self._parse_json_response(raw_response)
            
            # Estimate cost (DeepSeek: ~$0.14 per 1M input tokens, $0.28 per 1M output tokens)
            if response.usage:
                input_cost = (response.usage.prompt_tokens / 1_000_000) * 0.14
                output_cost = (response.usage.completion_tokens / 1_000_000) * 0.28
                total_cost = input_cost + output_cost
            else:
                total_cost = 0.0
            
            logger.info(f"DeepSeek response: {tokens_used} tokens, ${total_cost:.6f}")
            
            return {
                "response": raw_response,
                "parsed_decisions": parsed_decisions,
                "tokens_used": tokens_used,
                "cost": total_cost
            }
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            raise
    
    async def _call_qwen(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Call Qwen API (Alibaba Cloud)."""
        try:
            response = await self.qwen_client.chat.completions.create(
                model="qwen-max",  # Qwen Max model
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            raw_response = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Parse JSON from response
            parsed_decisions = self._parse_json_response(raw_response)
            
            # Estimate cost (Qwen Max: ~$0.20 per 1M input tokens, ~$0.60 per 1M output tokens)
            if response.usage:
                input_cost = (response.usage.prompt_tokens / 1_000_000) * 0.20
                output_cost = (response.usage.completion_tokens / 1_000_000) * 0.60
                total_cost = input_cost + output_cost
            else:
                total_cost = 0.0
            
            logger.info(f"Qwen response: {tokens_used} tokens, ${total_cost:.6f}")
            
            return {
                "response": raw_response,
                "parsed_decisions": parsed_decisions,
                "tokens_used": tokens_used,
                "cost": total_cost
            }
        except Exception as e:
            logger.error(f"Error calling Qwen API: {e}")
            raise
    
    # Gemini implementation removed - can be added later with google-generativeai library
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed JSON dict or empty dict if parsing fails
        """
        try:
            # Try to find JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx + 1]
                parsed = json.loads(json_str)
                return parsed
            
            # If no JSON found, try parsing entire response
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from response: {e}")
            return {
                "action": "hold",
                "reasoning": "Failed to parse LLM response",
                "raw_response": response
            }


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get or create LLM client instance.
    
    Returns:
        LLMClient instance
    """
    global _llm_client
    
    if _llm_client is None:
        _llm_client = LLMClient()
    
    return _llm_client