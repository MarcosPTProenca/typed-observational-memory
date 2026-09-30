from pydantic import BaseModel, Field


class TokenBudget(BaseModel):
    max_tokens: int = Field(gt=0)


class UnsafeContextBudget(ValueError):
    """Raised when protected memory cannot fit in the requested budget."""

    def __init__(self, message: str, *, required_tokens: int = 0, budget: int = 0) -> None:
        super().__init__(message)
        self.required_tokens = required_tokens
        self.budget = budget
