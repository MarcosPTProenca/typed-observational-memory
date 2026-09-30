import tiktoken

_ENCODING = tiktoken.get_encoding("o200k_base")


def count_tokens(text: str) -> int:
    """Count tokens using the encoding used by current OpenAI models."""
    return len(_ENCODING.encode(text))
