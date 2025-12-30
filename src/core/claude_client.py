"""
Anthropic Claude API client wrapper.
Replaces Abacus AI's client.evaluate_prompt() with direct Anthropic API calls.
"""

import time
from typing import Optional
import anthropic
from anthropic import APIError, RateLimitError

from .config import Config
from .console import console, print_warning, print_error


class ClaudeClient:
    """
    Wrapper for Anthropic Claude API calls.
    Provides compatibility layer for code migrated from Abacus AI.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Claude client."""
        self.api_key = api_key or Config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Set ANTHROPIC_API_KEY in your .env file."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)

        # Track API usage
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.api_calls = 0

    def evaluate_prompt(
        self,
        prompt: str,
        system_message: str = "",
        llm_name: str = "CLAUDE_V3_5_HAIKU",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> "ClaudeResponse":
        """
        Evaluate a prompt using Claude.

        This method provides compatibility with the Abacus AI interface:
        client.evaluate_prompt(prompt=..., system_message=..., llm_name=...)

        Args:
            prompt: The user prompt to send
            system_message: System instructions for Claude
            llm_name: Model identifier (CLAUDE_V3_5_HAIKU or CLAUDE_V3_5_SONNET)
            max_retries: Number of retries on rate limit errors
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            ClaudeResponse object with .content attribute
        """
        # Map Abacus model names to Anthropic model IDs
        model_mapping = {
            "CLAUDE_V3_5_HAIKU": Config.CLAUDE_HAIKU_MODEL,
            "CLAUDE_V3_5_SONNET": Config.CLAUDE_SONNET_MODEL,
        }

        model = model_mapping.get(llm_name, Config.CLAUDE_HAIKU_MODEL)
        max_tokens = (
            Config.MAX_TOKENS_SONNET if "sonnet" in model.lower()
            else Config.MAX_TOKENS_HAIKU
        )

        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_message,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                # Track usage
                self.api_calls += 1
                if hasattr(response, 'usage'):
                    self.total_input_tokens += response.usage.input_tokens
                    self.total_output_tokens += response.usage.output_tokens

                # Extract content from response
                content = ""
                if response.content:
                    for block in response.content:
                        if hasattr(block, 'text'):
                            content += block.text

                return ClaudeResponse(content=content, raw_response=response)

            except RateLimitError as e:
                last_error = e
                wait_time = retry_delay * (2 ** attempt)
                print_warning(f"Rate limited. Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)

            except APIError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print_warning(f"API error: {e}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    raise

        # If we get here, all retries failed
        raise last_error or Exception("All retries failed")

    def get_usage_stats(self) -> dict:
        """Return API usage statistics."""
        return {
            "total_api_calls": self.api_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
        }


class ClaudeResponse:
    """
    Response wrapper for Claude API responses.
    Provides compatibility with Abacus AI's response format.
    """

    def __init__(self, content: str, raw_response=None):
        self.content = content
        self.raw_response = raw_response

    def __str__(self):
        return self.content


# Create a global client instance for convenience
_global_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """Get or create the global Claude client."""
    global _global_client
    if _global_client is None:
        _global_client = ClaudeClient()
    return _global_client
