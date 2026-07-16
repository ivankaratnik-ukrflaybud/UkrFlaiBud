from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID

from app.models.base import BaseEntity, ValidationError


class EmployeeStatus(StrEnum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"


@dataclass(slots=True)
class Organization(BaseEntity):
    name: str = ""
    short_name: str = ""
    legal_name: str = ""
    edrpou: str = ""
    tax_number: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    is_active: bool = True


@dataclass(slots=True)
class Department(BaseEntity):
    organization_id: UUID | None = None
    parent_department_id: UUID | None = None
    name: str = ""
    code: str | None = None
    description: str | None = None
    manager_employee_id: UUID | None = None
    is_active: bool = True

    def ensure_not_parented_to_self(self) -> None:
        if self.parent_department_id == self.id:
            raise ValidationError("Department cannot be its own parent.")


@dataclass(slots=True)
class Position(BaseEntity):
    organization_id: UUID | None = None
    department_id: UUID | None = None
    name: str = ""
    code: str | None = None
    description: str | None = None
    is_active: bool = True


@dataclass(slots=True)
class Employee(BaseEntity):
    organization_id: UUID | None = None
    department_id: UUID | None = None
    position_id: UUID | None = None
    personnel_number: str | None = None
    first_name: str = ""
    last_name: str = ""
    middle_name: str | None = None
    email: str | None = None
    phone: str | None = None
    hire_date: date | None = None
    termination_date: date | None = None
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    supervisor_employee_id: UUID | None = None
    notes: str | None = None

    def ensure_not_supervisor_of_self(self) -> None:
        if self.supervisor_employee_id == self.id:
            raise ValidationError("Employee cannot supervise themselves.")
