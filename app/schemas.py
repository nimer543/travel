from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import date
from typing import List, Optional

# Place Schemas

class PlaceBase(BaseModel):
    external_id: int = Field(..., description="External artwork ID from the Art Institute of Chicago API")
    notes: Optional[str] = Field(None, description="Notes attached to the place")

class PlaceCreate(PlaceBase):
    pass

class PlaceUpdate(BaseModel):
    notes: Optional[str] = Field(None, description="Update notes for this place")
    is_visited: Optional[bool] = Field(None, description="Mark whether the place is visited")

class PlaceResponse(PlaceBase):
    id: int
    project_id: int
    title: Optional[str] = Field(None, description="Title of the artwork retrieved from external API")
    is_visited: bool

    model_config = ConfigDict(from_attributes=True)


# Project Schemas

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the travel project")
    description: Optional[str] = Field(None, description="Optional description of the travel project")
    start_date: Optional[date] = Field(None, description="Optional start date of the project (YYYY-MM-DD)")

class ProjectCreate(ProjectBase):
    places: Optional[List[PlaceCreate]] = Field(None, description="Optional array of places to create with the project (1 to 10 places)")

    @field_validator("places")
    def validate_places_limit(cls, v):
        if v is not None:
            if len(v) < 1 or len(v) > 10:
                raise ValueError("A project creation request with places must include between 1 and 10 places.")
        return v

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Name of the travel project")
    description: Optional[str] = Field(None, description="Optional description of the travel project")
    start_date: Optional[date] = Field(None, description="Optional start date of the project (YYYY-MM-DD)")

class ProjectResponse(ProjectBase):
    id: int
    is_completed: bool
    places: List[PlaceResponse] = []

    model_config = ConfigDict(from_attributes=True)


# User Schemas

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username for registration")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")

class UserResponse(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)
