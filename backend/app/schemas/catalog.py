from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FieldType = Literal[
    "text", "textarea", "number", "currency", "date", "date_range", "boolean",
    "select", "multi_select", "user_picker", "department_picker", "attachment", "url",
]


class FormOption(BaseModel):
    value: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=180)


class FormField(BaseModel):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    type: FieldType
    label: str = Field(min_length=1, max_length=180)
    required: bool = False
    helper_text: str | None = Field(default=None, max_length=500)
    placeholder: str | None = Field(default=None, max_length=250)
    options: list[FormOption] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def validate_options(self) -> "FormField":
        values = [option.value for option in self.options]
        if len(values) != len(set(values)):
            raise ValueError("Option values must be unique")
        if self.type in {"select", "multi_select"} and not values:
            raise ValueError("Select fields require at least one option")
        return self


class FormSection(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=500)
    fields: list[FormField] = Field(min_length=1, max_length=100)


class DynamicFormSchema(BaseModel):
    sections: list[FormSection] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_unique_field_keys(self) -> "DynamicFormSchema":
        keys = [field.key for section in self.sections for field in section.fields]
        if len(keys) != len(set(keys)):
            raise ValueError("Form field keys must be unique across the schema")
        if len(keys) > 100:
            raise ValueError("A form supports at most 100 fields")
        return self


class RequestTypeCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    category: str = Field(min_length=2, max_length=80)
    owner_service_team_id: int | None = None
    is_active: bool = True


class RequestTypeUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=2, max_length=80)
    owner_service_team_id: int | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "RequestTypeUpdate":
        for name in ("category", "is_active"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class RequestTypeVersionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    form_schema: DynamicFormSchema
    validation_schema: dict[str, Any] | None = None
    sla_config: dict[str, Any] | None = None
    attachment_config: dict[str, Any] | None = None


class RequestTypeVersionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    form_schema: DynamicFormSchema | None = None
    validation_schema: dict[str, Any] | None = None
    sla_config: dict[str, Any] | None = None
    attachment_config: dict[str, Any] | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "RequestTypeVersionUpdate":
        for name in ("title", "form_schema"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class RequestTypeVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_type_id: int
    version: int
    title: str
    description: str | None
    form_schema: dict[str, Any]
    validation_schema: dict[str, Any] | None
    sla_config: dict[str, Any] | None
    attachment_config: dict[str, Any] | None
    status: str
    published_at: datetime | None
    created_by: int | None
    created_at: datetime


class RequestTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    category: str
    owner_service_team_id: int | None
    is_active: bool
    created_at: datetime


class CatalogRequestTypeOut(RequestTypeOut):
    published_version: RequestTypeVersionOut
