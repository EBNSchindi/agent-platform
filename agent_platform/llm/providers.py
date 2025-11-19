"""
Unified LLM Provider with Ollama-First + OpenAI Fallback

Strategy:
1. Try Ollama (local, fast, free) for every LLM call
2. On any error → Automatic fallback to OpenAI (cloud, reliable)
3. Log which provider was used for transparency

Based on OpenAI-compatible API interface.
"""

from typing import Optional, Literal, Dict, Any, List
from openai import OpenAI
import time
from datetime import datetime


class UnifiedLLMProvider:
    """
    Provides unified interface for LLM calls with automatic fallback.

    All LLM calls go through this provider:
    - Primary: Ollama (local gptoss20b via http://localhost:11434)
    - Fallback: OpenAI (cloud gpt-4o)

    Usage:
        provider = get_llm_provider()
        response, provider_used = await provider.complete(messages)
    """

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434/v1",
        ollama_model: str = "gptoss20b",
        ollama_timeout: int = 60,
        openai_api_key: str = "",
        openai_model: str = "gpt-4o",
        fallback_enabled: bool = True
    ):
        """
        Initialize LLM provider with Ollama and OpenAI clients.

        Args:
            ollama_base_url: Ollama API endpoint (OpenAI-compatible)
            ollama_model: Model name for Ollama
            ollama_timeout: Timeout for Ollama requests (seconds)
            openai_api_key: OpenAI API key
            openai_model: Model name for OpenAI
            fallback_enabled: Whether to fallback to OpenAI on Ollama errors
        """

        # Ollama client (OpenAI-compatible API via Ollama)
        self.ollama = OpenAI(
            base_url=ollama_base_url,
            api_key="ollama",  # Dummy key (Ollama doesn't require auth)
            timeout=ollama_timeout
        )
        self.ollama_model = ollama_model

        # OpenAI client (fallback)
        self.openai = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.openai_model = openai_model

        # Configuration
        self.fallback_enabled = fallback_enabled

        # Statistics tracking
        self.stats = {
            'ollama_success': 0,
            'ollama_failures': 0,
            'openai_fallbacks': 0,
            'openai_direct': 0,  # When explicitly requested
            'total_calls': 0
        }

        # Performance tracking
        self.performance = {
            'ollama_avg_time': 0.0,
            'openai_avg_time': 0.0,
            'ollama_call_count': 0,
            'openai_call_count': 0
        }

    async def complete(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[type] = None,
        force_provider: Optional[Literal["ollama", "openai"]] = None,
        **kwargs
    ) -> tuple[Any, str]:
        """
        Complete chat with automatic Ollama-first fallback.

        Args:
            messages: Chat messages in OpenAI format
            response_format: Pydantic model for structured output (optional)
            force_provider: Force specific provider (for testing)
            **kwargs: Additional arguments passed to completion API

        Returns:
            (response, provider_used) where provider_used is "ollama" or "openai_fallback"

        Raises:
            RuntimeError: If both providers fail
        """

        self.stats['total_calls'] += 1

        # Allow forcing specific provider (useful for testing)
        if force_provider == "openai":
            return await self._openai_complete(messages, response_format, **kwargs)

        # Try Ollama first
        try:
            start_time = time.time()
            response = await self._ollama_complete(messages, response_format, **kwargs)
            elapsed = time.time() - start_time

            # Update stats
            self.stats['ollama_success'] += 1
            self._update_performance('ollama', elapsed)

            return response, "ollama"

        except Exception as ollama_error:
            self.stats['ollama_failures'] += 1

            print(f"\n⚠️  Ollama failed: {str(ollama_error)[:150]}")

            # Check if fallback is enabled
            if not self.fallback_enabled:
                raise RuntimeError(
                    f"Ollama failed and fallback is disabled: {ollama_error}"
                )

            if not self.openai:
                raise RuntimeError(
                    f"Ollama failed and OpenAI client not configured: {ollama_error}"
                )

            print(f"🔄 Falling back to OpenAI {self.openai_model}...\n")

            # Fallback to OpenAI
            try:
                start_time = time.time()
                response = await self._openai_complete(messages, response_format, **kwargs)
                elapsed = time.time() - start_time

                # Update stats
                self.stats['openai_fallbacks'] += 1
                self._update_performance('openai', elapsed)

                return response, "openai_fallback"

            except Exception as openai_error:
                # Both failed - raise comprehensive error
                raise RuntimeError(
                    f"Both LLM providers failed!\n"
                    f"  Ollama error: {ollama_error}\n"
                    f"  OpenAI error: {openai_error}"
                )

    async def _ollama_complete(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[type] = None,
        **kwargs
    ) -> Any:
        """Call Ollama API"""

        # Build request
        request_params = {
            'model': self.ollama_model,
            'messages': messages,
            **kwargs
        }

        # Make API call with structured output if specified
        if response_format:
            # Use .parse() for structured outputs (Pydantic models)
            response = self.ollama.beta.chat.completions.parse(
                model=self.ollama_model,
                messages=messages,
                response_format=response_format,
                **kwargs
            )
        else:
            # Use .create() for regular completions
            response = self.ollama.chat.completions.create(**request_params)

        # Return response object (caller will wrap in tuple)
        return response

    async def _openai_complete(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[type] = None,
        **kwargs
    ) -> Any:
        """Call OpenAI API"""

        if not self.openai:
            raise RuntimeError("OpenAI client not configured")

        # Update direct call stat if not a fallback
        if self.stats['total_calls'] == self.stats['openai_direct'] + self.stats['openai_fallbacks'] + 1:
            self.stats['openai_direct'] += 1

        # Make API call with structured output if specified
        if response_format:
            # Use .parse() for structured outputs (Pydantic models)
            response = self.openai.beta.chat.completions.parse(
                model=self.openai_model,
                messages=messages,
                response_format=response_format,
                **kwargs
            )
        else:
            # Use .create() for regular completions
            response = self.openai.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                **kwargs
            )

        # Return response object only (caller will wrap in tuple)
        return response

    def _update_performance(self, provider: str, elapsed_time: float):
        """Update performance metrics"""

        if provider == 'ollama':
            count = self.performance['ollama_call_count']
            avg = self.performance['ollama_avg_time']

            # Exponential moving average
            self.performance['ollama_avg_time'] = (avg * count + elapsed_time) / (count + 1)
            self.performance['ollama_call_count'] = count + 1

        elif provider == 'openai':
            count = self.performance['openai_call_count']
            avg = self.performance['openai_avg_time']

            self.performance['openai_avg_time'] = (avg * count + elapsed_time) / (count + 1)
            self.performance['openai_call_count'] = count + 1

    def get_stats(self) -> Dict[str, Any]:
        """
        Get provider usage statistics.

        Returns:
            Dictionary with usage stats and success rates
        """
        total = self.stats['total_calls']

        if total == 0:
            return {
                **self.stats,
                'ollama_success_rate': 0.0,
                'fallback_rate': 0.0,
                **self.performance
            }

        return {
            **self.stats,
            'ollama_success_rate': self.stats['ollama_success'] / total,
            'fallback_rate': self.stats['openai_fallbacks'] / total,
            **self.performance
        }

    def print_stats(self):
        """Print human-readable statistics"""
        stats = self.get_stats()

        print("\n" + "=" * 60)
        print("LLM PROVIDER STATISTICS")
        print("=" * 60)
        print(f"Total Calls: {stats['total_calls']}")
        print(f"\nOllama (Local):")
        print(f"  ✅ Successes: {stats['ollama_success']}")
        print(f"  ❌ Failures: {stats['ollama_failures']}")
        print(f"  📊 Success Rate: {stats['ollama_success_rate']:.1%}")
        if stats['ollama_call_count'] > 0:
            print(f"  ⏱️  Avg Time: {stats['ollama_avg_time']:.2f}s")

        print(f"\nOpenAI (Cloud):")
        print(f"  🔄 Fallbacks: {stats['openai_fallbacks']}")
        print(f"  📞 Direct Calls: {stats['openai_direct']}")
        print(f"  📊 Fallback Rate: {stats['fallback_rate']:.1%}")
        if stats['openai_call_count'] > 0:
            print(f"  ⏱️  Avg Time: {stats['openai_avg_time']:.2f}s")

        print("=" * 60 + "\n")

    def reset_stats(self):
        """Reset statistics (useful for testing)"""
        self.stats = {
            'ollama_success': 0,
            'ollama_failures': 0,
            'openai_fallbacks': 0,
            'openai_direct': 0,
            'total_calls': 0
        }
        self.performance = {
            'ollama_avg_time': 0.0,
            'openai_avg_time': 0.0,
            'ollama_call_count': 0,
            'openai_call_count': 0
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_provider: Optional[UnifiedLLMProvider] = None


def get_llm_provider(reset: bool = False) -> UnifiedLLMProvider:
    """
    Get singleton instance of UnifiedLLMProvider.

    Automatically loads configuration from agent_platform.core.config.

    Args:
        reset: Force recreation of provider (useful for config changes)

    Returns:
        UnifiedLLMProvider instance
    """
    global _provider

    if _provider is None or reset:
        # Import here to avoid circular imports
        from agent_platform.core.config import Config

        _provider = UnifiedLLMProvider(
            ollama_base_url=Config.OLLAMA_BASE_URL,
            ollama_model=Config.OLLAMA_MODEL,
            ollama_timeout=Config.OLLAMA_TIMEOUT,
            openai_api_key=Config.OPENAI_API_KEY,
            openai_model=Config.OPENAI_MODEL,
            fallback_enabled=Config.LLM_FALLBACK_ENABLED
        )

    return _provider
