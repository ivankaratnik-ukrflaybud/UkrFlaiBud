from enum import StrEnum


class WarehouseType(StrEnum):
    MAIN = "main"
    PRODUCTION = "production"
    RAW_MATERIAL = "raw_material"
    COMPONENTS = "components"
    FINISHED_GOODS = "finished_goods"
    QUARANTINE = "quarantine"
    SCRAP = "scrap"
    OTHER = "other"


class StorageLocationType(StrEnum):
    ZONE = "zone"
    RACK = "rack"
    SHELF = "shelf"
    BIN = "bin"
    FLOOR = "floor"
    QUARANTINE = "quarantine"
    SCRAP = "scrap"
    OTHER = "other"


class ItemType(StrEnum):
    RAW_MATERIAL = "raw_material"
    COMPONENT = "component"
    SEMI_FINISHED = "semi_finished"
    FINISHED_GOOD = "finished_good"
    CONSUMABLE = "consumable"
    TOOL = "tool"
    SPARE_PART = "spare_part"
    PACKAGING = "packaging"
    SERVICE = "service"
    OTHER = "other"


class SerialStatus(StrEnum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    ISSUED = "issued"
    IN_PRODUCTION = "in_production"
    INSTALLED = "installed"
    QUARANTINE = "quarantine"
    SCRAPPED = "scrapped"


class InventoryDocumentType(StrEnum):
    RECEIPT = "receipt"
    ISSUE = "issue"
    TRANSFER = "transfer"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"
    RETURN_IN = "return_in"
    RETURN_OUT = "return_out"


class InventoryDocumentStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


class InventoryMovementKind(StrEnum):
    RECEIPT = "receipt"
    ISSUE = "issue"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"
    RETURN_IN = "return_in"
    RETURN_OUT = "return_out"
    REVERSAL = "reversal"
