from enum import StrEnum


class ProductionOrderType(StrEnum):
    STANDARD = "standard"
    PROTOTYPE = "prototype"
    REPAIR = "repair"
    REWORK = "rework"
    KIT = "kit"
    OTHER = "other"


class ProductionOrderStatus(StrEnum):
    DRAFT = "draft"
    PLANNED = "planned"
    RELEASED = "released"
    MATERIALS_RESERVED = "materials_reserved"
    IN_PROGRESS = "in_progress"
    PARTIALLY_COMPLETED = "partially_completed"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class ProductionOrderPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ProductionMaterialSourceType(StrEnum):
    INVENTORY_ITEM = "inventory_item"
    MANUAL = "manual"
    SUBASSEMBLY = "subassembly"


class ProductionStageStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ProductionMaterialTransactionType(StrEnum):
    RESERVATION = "reservation"
    RESERVATION_RELEASE = "reservation_release"
    ISSUE = "issue"
    RETURN = "return"
    CONSUMPTION = "consumption"
    SCRAP = "scrap"
    CORRECTION = "correction"


class ProductionMaterialTransactionStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


class ProductionCompletionStatus(StrEnum):
    POSTED = "posted"
    CANCELLED = "cancelled"
