from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.organizations.domain.entities import EmployeeStatus


class EntityResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None
    deleted_at: datetime | None
    deleted_by: UUID | None
    version: int

    model_config = ConfigDict(from_attributes=True)


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    short_name: str = Field(min_length=1, max_length=120)
    legal_name: str = Field(min_length=1, max_length=255)
    edrpou: str = Field(min_length=8, max_length=12)
    tax_number: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=64)
    website: str | None = Field(default=None, max_length=255)
    address: str | None = None
    is_active: bool = True


class OrganizationUpdate(BaseModel):
    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    short_name: str | None = Field(default=None, min_length=1, max_length=120)
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    edrpou: str | None = Field(default=None, min_length=8, max_length=12)
    tax_number: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=64)
    website: str | None = Field(default=None, max_length=255)
    address: str | None = None
    is_active: bool | None = None


class OrganizationResponse(EntityResponse):
    name: str
    short_name: str
    legal_name: str
    edrpou: str
    tax_number: str | None
    email: str | None
    phone: str | None
    website: str | None
    address: str | None
    is_active: bool


class DepartmentCreate(BaseModel):
    organization_id: UUID
    parent_department_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    description: str | None = None
    manager_employee_id: UUID | None = None
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    version: int = Field(ge=1)
    organization_id: UUID | None = None
    parent_department_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    description: str | None = None
    manager_employee_id: UUID | None = None
    is_active: bool | None = None


class DepartmentResponse(EntityResponse):
    organization_id: UUID
    parent_department_id: UUID | None
    name: str
    code: str | None
    description: str | None
    manager_employee_id: UUID | None
    is_active: bool


class PositionCreate(BaseModel):
    organization_id: UUID
    department_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    description: str | None = None
    is_active: bool = True


class PositionUpdate(BaseModel):
    version: int = Field(ge=1)
    organization_id: UUID | None = None
    department_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)
    description: str | None = None
    is_active: bool | None = None


class PositionResponse(EntityResponse):
    organization_id: UUID
    department_id: UUID | None
    name: str
    code: str | None
    description: str | None
    is_active: bool


class EmployeeCreate(BaseModel):
    organization_id: UUID
    department_id: UUID | None = None
    position_id: UUID | None = None
    personnel_number: str | None = Field(default=None, max_length=64)
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    middle_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=64)
    hire_date: date | None = None
    termination_date: date | None = None
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    supervisor_employee_id: UUID | None = None
    notes: str | None = None


class EmployeeUpdate(BaseModel):
    version: int = Field(ge=1)
    organization_id: UUID | None = None
    department_id: UUID | None = None
    position_id: UUID | None = None
    personnel_number: str | None = Field(default=None, max_length=64)
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    middle_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=64)
    hire_date: date | None = None
    termination_date: date | None = None
    status: EmployeeStatus | None = None
    supervisor_employee_id: UUID | None = None
    notes: str | None = None


class EmployeeResponse(EntityResponse):
    organization_id: UUID
    department_id: UUID | None
    position_id: UUID | None
    personnel_number: str | None
    first_name: str
    last_name: str
    middle_name: str | None
    email: str | None
    phone: str | None
    hire_date: date | None
    termination_date: date | None
    status: EmployeeStatus
    supervisor_employee_id: UUID | None
    notes: str | None
