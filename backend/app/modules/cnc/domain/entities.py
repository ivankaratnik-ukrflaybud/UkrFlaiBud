from enum import StrEnum


class CncMachineType(StrEnum):
    ROUTER = "router"
    MILLING = "milling"
    LASER = "laser"
    PLASMA = "plasma"
    WATERJET = "waterjet"
    LATHE = "lathe"
    OTHER = "other"


class CncMachineStatus(StrEnum):
    AVAILABLE = "available"
    SETUP = "setup"
    RUNNING = "running"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    FAULT = "fault"
    UNAVAILABLE = "unavailable"
    DECOMMISSIONED = "decommissioned"


class CncToolType(StrEnum):
    END_MILL = "end_mill"
    DRILL = "drill"
    ENGRAVING = "engraving"
    BALL_NOSE = "ball_nose"
    V_BIT = "v_bit"
    SAW = "saw"
    INSERT = "insert"
    HOLDER = "holder"
    OTHER = "other"


class CncFileType(StrEnum):
    NC = "nc"
    GCODE = "gcode"
    TAP = "tap"
    DXF = "dxf"
    DWG = "dwg"
    STEP = "step"
    STP = "stp"
    PDF = "pdf"
    OTHER = "other"


class CncProgramStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    OBSOLETE = "obsolete"


class CncSheetPlanStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    IN_USE = "in_use"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CncWorkOrderStatus(StrEnum):
    DRAFT = "draft"
    PLANNED = "planned"
    QUEUED = "queued"
    SETUP = "setup"
    RUNNING = "running"
    PAUSED = "paused"
    PARTIALLY_COMPLETED = "partially_completed"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class CncPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class CncExecutionEventType(StrEnum):
    QUEUED = "queued"
    SETUP_STARTED = "setup_started"
    SETUP_COMPLETED = "setup_completed"
    MACHINING_STARTED = "machining_started"
    PAUSED = "paused"
    RESUMED = "resumed"
    BLOCKED = "blocked"
    UNBLOCKED = "unblocked"
    QUANTITY_REPORTED = "quantity_reported"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CncMaterialTransactionType(StrEnum):
    ISSUE = "issue"
    RETURN = "return"
    SCRAP = "scrap"
    CORRECTION = "correction"


class CncOffcutStatus(StrEnum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    CONSUMED = "consumed"
    SCRAPPED = "scrapped"
