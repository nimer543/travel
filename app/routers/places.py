from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Project, ProjectPlace
from app.schemas import PlaceCreate, PlaceUpdate, PlaceResponse
from app.external_api import fetch_artwork_by_id
from app.auth import get_current_user

router = APIRouter(
    prefix="/projects/{project_id}/places",
    tags=["Project Places"],
    dependencies=[Depends(get_current_user)]  # Secure all places endpoints
)

def update_project_completion_status(db: Session, project_id: int):
    """
    Helper to recalculate the completion status of a project.
    A project is completed if and only if:
      1. It has at least one place.
      2. All places linked to this project have is_visited = True.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return

    places = db.query(ProjectPlace).filter(ProjectPlace.project_id == project_id).all()
    
    if not places:
        # No places means the project is not completed (minimum 1 place needed)
        project.is_completed = False
    else:
        # True if all places are visited, False otherwise
        project.is_completed = all(p.is_visited for p in places)
        
    db.commit()


@router.post("", response_model=PlaceResponse, status_code=status.HTTP_201_CREATED)
async def add_place_to_project(
    project_id: int,
    place_data: PlaceCreate,
    db: Session = Depends(get_db)
):
    """
    Add a new place (artwork) to an existing project.
    Validates:
      - Project exists.
      - Place exists in the Art Institute of Chicago API.
      - Project does not exceed the limit of 10 places.
      - Place is not already added to this project.
    """
    # 1. Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found."
        )

    # 2. Enforce limits: maximum 10 places per project
    current_places_count = db.query(ProjectPlace).filter(ProjectPlace.project_id == project_id).count()
    if current_places_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add place. The project already has the maximum limit of 10 places."
        )

    # 3. Prevent adding the same place to the same project more than once
    existing_place = db.query(ProjectPlace).filter(
        ProjectPlace.project_id == project_id,
        ProjectPlace.external_id == place_data.external_id
    ).first()
    if existing_place:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Artwork with ID {place_data.external_id} is already added to this project."
        )

    # 4. Validate that the place exists in the Art Institute of Chicago API
    artwork = await fetch_artwork_by_id(place_data.external_id)
    if not artwork:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Artwork with ID {place_data.external_id} does not exist in the external API."
        )

    # 5. Create and store the new place
    new_place = ProjectPlace(
        project_id=project_id,
        external_id=place_data.external_id,
        title=artwork.get("title", f"Artwork {place_data.external_id}"),
        notes=place_data.notes,
        is_visited=False
    )
    db.add(new_place)
    db.commit()
    db.refresh(new_place)

    # 6. Recalculate project completion status (adding a non-visited place might mark project as incomplete)
    update_project_completion_status(db, project_id)
    db.refresh(new_place)

    return new_place


@router.get("", response_model=List[PlaceResponse])
def list_project_places(project_id: int, db: Session = Depends(get_db)):
    """
    List all places for a specific project.
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found."
        )

    places = db.query(ProjectPlace).filter(ProjectPlace.project_id == project_id).all()
    return places


@router.get("/{place_id}", response_model=PlaceResponse)
def get_project_place(project_id: int, place_id: int, db: Session = Depends(get_db)):
    """
    Get a single place details within a project.
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found."
        )

    place = db.query(ProjectPlace).filter(
        ProjectPlace.project_id == project_id,
        ProjectPlace.id == place_id
    ).first()
    
    if not place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Place with ID {place_id} not found within this project."
        )
    return place


@router.patch("/{place_id}", response_model=PlaceResponse)
def update_project_place(
    project_id: int,
    place_id: int,
    place_update: PlaceUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a place within a project (update notes and/or mark as visited).
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found."
        )

    place = db.query(ProjectPlace).filter(
        ProjectPlace.project_id == project_id,
        ProjectPlace.id == place_id
    ).first()

    if not place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Place with ID {place_id} not found within this project."
        )

    # Apply updates if provided in request body
    update_data = place_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(place, key, value)

    db.commit()
    db.refresh(place)

    # Recalculate project completion status if visited status was updated
    if "is_visited" in update_data:
        update_project_completion_status(db, project_id)
        db.refresh(place)

    return place
