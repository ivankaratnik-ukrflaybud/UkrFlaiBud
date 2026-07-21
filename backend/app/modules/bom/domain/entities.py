from enum import StrEnum


class SpecificationType(StrEnum):
    PRODUCT = "product"
    ASSEMBLY = "assembly"
    SEMI_FINISHED = "semi_finished"
    KIT = "kit"
    PACKAGING = "packaging"
    SPARE_PARTS_KIT = "spare_parts_kit"
    OTHER = "other"


class SpecificationStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class BomVersionStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class BomLineSourceType(StrEnum):
    INVENTORY_ITEM = "inventory_item"
    MANUAL = "manual"
    SUBASSEMBLY = "subassembly"
