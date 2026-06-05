from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.models import Project, ProjectPlace
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.external_api import fetch_artwork_by_id
from app.auth import get_current_user

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
    dependencies=[Depends(get_current_user)]  # Secure all project endpoints
)

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new travel project.
    Can optionally include a list of places (up to 10 places) to create in one single request.
    Each place is validated against the external Art Institute of Chicago API.
    """
    # 1. Create the project instance
    new_project = Project(
        name=project_data.name,
        description=project_data.description,
        start_date=project_data.start_date,
        is_completed=False
    )
    db.add(new_project)
    db.flush()  # Get the generated project ID

    if project_data.places:
        # Check for duplicate external_ids in the request body
        req_external_ids = [p.external_id for p in project_data.places]
        if len(req_external_ids) != len(set(req_external_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate external place IDs found in the request list."
            )

        places_to_add = []
        for place_in in project_data.places:
            # Validate existence via external API
            artwork = await fetch_artwork_by_id(place_in.external_id)
            if not artwork:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Artwork/Place with ID {place_in.external_id} does not exist in the external API."
                )
            
            # Create ProjectPlace instance
            place_db = ProjectPlace(
                project_id=new_project.id,
                external_id=place_in.external_id,
                title=artwork.get("title", f"Artwork {place_in.external_id}"),
                notes=place_in.notes,
                is_visited=False
            )
            places_to_add.append(place_db)
            db.add(place_db)
        
        # Flush to check unique constraint in database and retrieve items
        db.flush()
    
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max number of items to return"),
    name: Optional[str] = Query(None, description="Filter projects by name (case-insensitive substring)"),
    is_completed: Optional[bool] = Query(None, description="Filter projects by completion status"),
    db: Session = Depends(get_db)
):
    """
    List travel projects with pagination and filtering by name or completion status.
    """
    query = db.query(Project)
    
    if name:
        query = query.filter(Project.name.ilike(f"%{name}%"))
        
    if is_completed is not None:
        query = query.filter(Project.is_completed == is_completed)
        
    projects = query.offset(skip).limit(limit).all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """
    Get a single travel project by its ID.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found."
        )
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """
    Update basic information of a travel project (Name, Description, Start Date).
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found."
        )
    
    # Update fields if provided
    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
        
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    Delete a travel project.
    A project cannot be deleted if any of its places are already marked as visited.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found."
        )
    
    # Check if any of its places are marked as visited
    visited_places = db.query(ProjectPlace).filter(
        ProjectPlace.project_id == project_id,
        ProjectPlace.is_visited == True
    ).first()
    
    if visited_places:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete project because some of its places are already marked as visited."
        )
    
    db.delete(project)
    db.commit()
    return None
