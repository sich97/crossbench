"""
Tokenizer Integration - Generate prompts that fill ~100% of configured context size.

Uses gguf library's built-in tokenizer for accurate token count estimation.
"""

from typing import Optional, Tuple
import os


class GGUFTokenizer:
    """
    Lightweight tokenizer wrapper using gguf library.

    Only loads tokenizer vocabulary, not model weights.
    Memory usage: ~10-50 MB
    """

    def __init__(self, model_path: str):
        """
        Initialize tokenizer from GGUF model file.

        Args:
            model_path: Path to the .gguf model file
        """
        import gguf

        self.reader = gguf.GGUFReader(model_path)
        self.tokenizer = self.reader.tokenizer

    def encode(self, text: str) -> list:
        """
        Encode text to token IDs.

        Args:
            text: Input text string

        Returns:
            List of token IDs
        """
        return self.tokenizer.encode(text)

    def decode(self, token_ids: list) -> str:
        """
        Decode token IDs to text.

        Args:
            token_ids: List of token IDs

        Returns:
            Decoded text string
        """
        return self.tokenizer.decode(token_ids)

    def count_tokens(self, text: str) -> int:
        """
        Get token count for text.

        Args:
            text: Input text string

        Returns:
            Number of tokens
        """
        return len(self.encode(text))


def get_tokenizer(model_path: str) -> Optional[GGUFTokenizer]:
    """
    Load tokenizer from GGUF model file using gguf library.

    Args:
        model_path: Path to the .gguf model file

    Returns:
        GGUFTokenizer object or None if not available
    """
    try:
        return GGUFTokenizer(model_path)
    except ImportError:
        print("Warning: gguf library not installed. Using fallback tokenizer.")
        return None
    except Exception as e:
        print(f"Warning: Could not load GGUF file: {e}")
        return None


def generate_repetitive_text(target_tokens: int, token_sample: str = "The") -> str:
    """
    Generate repetitive text that approximates target token count.

    This is a simple fallback method. For production, use actual tokenizer.

    Args:
        target_tokens: Target number of tokens
        token_sample: Sample text that represents one token (default: "The")

    Returns:
        Repetitive text string
    """
    # Estimate: "The " is approximately 1 token
    # Generate enough repetitions to reach target
    text = (token_sample + " ") * target_tokens

    return text


def generate_full_context_prompt(ctx_size: int, model_path: str) -> Tuple[str, int]:
    """
    Generate a prompt that fills ~90% of the configured context size.

    Uses gguf library tokenizer for accurate token count estimation.
    Targets 90% to prevent accidentally exceeding context limit.

    Args:
        ctx_size: Target context size in tokens (from --ctx-size)
        model_path: Path to the model file for tokenizer

    Returns:
        Tuple of (prompt_string, actual_token_count)
    """
    # Try to use actual tokenizer
    tokenizer = get_tokenizer(model_path)

    if tokenizer:
        # Generate prompt using model's tokenizer
        # Start with a base text and expand until we reach target
        base_text = "The quick brown fox jumps over the lazy dog. "

        # Calculate target (90% to be safe)
        target_tokens = int(ctx_size * 0.90)

        # Get base token count
        base_tokens = tokenizer.count_tokens(base_text)

        if base_tokens == 0:
            base_tokens = 1  # Prevent division by zero

        # Calculate how many repetitions we need
        repetitions = (target_tokens // base_tokens) + 1

        # Build prompt
        prompt = base_text * repetitions

        # Get actual token count
        actual_tokens = tokenizer.count_tokens(prompt)

        return prompt, actual_tokens

    # Fallback: use repetitive text generation
    # Target 90% of ctx_size (safe margin)
    target = int(ctx_size * 0.90)
    prompt = generate_repetitive_text(target, "The ")

    # Estimate token count (rough approximation)
    estimated_tokens = len(prompt.split())

    return prompt, estimated_tokens


def get_token_count(prompt: str, model_path: str) -> int:
    """
    Get actual token count for a prompt using model's tokenizer.

    Args:
        prompt: Prompt text
        model_path: Path to the model file

    Returns:
        Token count
    """
    tokenizer = get_tokenizer(model_path)
    if tokenizer:
        return tokenizer.count_tokens(prompt)

    # Fallback: word count approximation
    return len(prompt.split())
