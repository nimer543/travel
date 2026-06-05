from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)

    #if project is deleted, places should be deleted too
    places = relationship("ProjectPlace", back_populates="project", cascade="all, delete-orphan")


class ProjectPlace(Base):
    __tablename__ = "project_places"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(Integer, nullable=False)  # Art Institute artwork ID
    title = Column(String, nullable=True)           # Name of the place retrieved from API
    notes = Column(Text, nullable=True)             # User notes
    is_visited = Column(Boolean, default=False, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="places")

    __table_args__ = (
        UniqueConstraint("project_id", "external_id", name="uq_project_place"),
    )
