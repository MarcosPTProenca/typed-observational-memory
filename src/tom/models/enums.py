from enum import StrEnum


class KnowledgeType(StrEnum):
    CONSTRAINT = "constraint"
    PROCEDURE = "procedure"
    BELIEF = "belief"
    PREFERENCE = "preference"
    EPISODIC = "episodic"


class RetentionPolicy(StrEnum):
    EXACT = "exact"
    HIGH_FIDELITY = "high_fidelity"
    COMPRESSIBLE = "compressible"
    DISCARDABLE = "discardable"


class Importance(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MemoryStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
