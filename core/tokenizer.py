"""
Tokenizer Integration - Generate prompts that fill ~100% of configured context size.

Uses model-specific tokenizer logic to ensure accurate context utilization.
"""

from typing import Optional, Tuple
import os


def get_tokenizer_from_gguf(model_path: str):
    """
    Load tokenizer from GGUF model file using gguf library.

    Args:
        model_path: Path to the .gguf model file

    Returns:
        Tokenizer object or None if not available
    """
    try:
        import gguf

        reader = gguf.GGUFReader(model_path)
        return reader
    except ImportError:
        print("Warning: gguf library not installed. Using fallback tokenizer.")
        return None
    except Exception as e:
        print(f"Warning: Could not load GGUF file: {e}")
        return None


def get_tokenizer_from_llama_cpp(model_path: str):
    """
    Load tokenizer from GGUF model file using llama-cpp-python.

    Args:
        model_path: Path to the .gguf model file

    Returns:
        Llama tokenizer object or None if not available
    """
    try:
        from llama_cpp import Llama

        llm = Llama(model_path, n_ctx=1, verbose=False)
        return llm
    except ImportError:
        print(
            "Warning: llama-cpp-python library not installed. Using fallback tokenizer."
        )
        return None
    except Exception as e:
        print(f"Warning: Could not load model with llama-cpp-python: {e}")
        return None


def get_context_size_from_model(model_path: str) -> Optional[int]:
    """
    Extract context size from model metadata.

    Args:
        model_path: Path to the .gguf model file

    Returns:
        Context size in tokens or None if not found
    """
    # Try gguf library first
    reader = get_tokenizer_from_gguf(model_path)
    if reader:
        try:
            for kv in reader.fields.items():
                if "context_length" in str(kv[0]).lower():
                    return kv[1].value
        except Exception:
            pass

    # Try llama-cpp-python
    llm = get_tokenizer_from_llama_cpp(model_path)
    if llm:
        return llm.n_ctx()

    # Fallback: return None
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


def generate_full_context_prompt(
    ctx_size: int, model_path: str, use_actual_tokenizer: bool = True
) -> Tuple[str, int]:
    """
    Generate a prompt that fills ~100% of the configured context size.

    Args:
        ctx_size: Target context size in tokens (from --ctx-size)
        model_path: Path to the model file for tokenizer
        use_actual_tokenizer: Whether to use actual tokenizer (requires library)

    Returns:
        Tuple of (prompt_string, actual_token_count)
    """
    if use_actual_tokenizer:
        # Try to use actual tokenizer
        llm = get_tokenizer_from_llama_cpp(model_path)
        if llm:
            # Generate prompt using model's tokenizer
            # Start with a base text and expand until we reach target
            base_text = "The quick brown fox jumps over the lazy dog. "
            prompt = base_text
            token_count = len(llm.tokenize(prompt.encode()))

            # Expand until we're close to target (within 5%)
            max_iterations = 100
            for _ in range(max_iterations):
                if token_count >= ctx_size * 0.95:
                    break
                prompt = base_text * (
                    (token_count // len(llm.tokenize(base_text.encode()))) + 1
                )
                token_count = len(llm.tokenize(prompt.encode()))

            return prompt, token_count

    # Fallback: use repetitive text generation
    # Target 95-100% of ctx_size
    target = int(ctx_size * 0.98)
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
    llm = get_tokenizer_from_llama_cpp(model_path)
    if llm:
        return len(llm.tokenize(prompt.encode()))

    # Fallback: word count approximation
    return len(prompt.split())
