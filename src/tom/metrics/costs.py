from .models import CostRates


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    rates: CostRates,
) -> float:
    """Estimate provider cost from token counts and per-million-token rates."""
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    return (
        input_tokens * rates.input_per_million + output_tokens * rates.output_per_million
    ) / 1_000_000
