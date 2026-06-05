from fastapi import FastAPI, status, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db
from app.models import User
from app.schemas import UserCreate, UserResponse
from app.auth import hash_password
from app.routers import projects, places

# Initialize SQLite db
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Travel Planner API",
    description="A CRUD backend API for managing travel projects and collecting desired places (artworks) to visit using the Art Institute of Chicago API.",
    version="1.0.0",
)

# Register project and place routers under API version prefix
app.include_router(projects.router, prefix="/api/v1")
app.include_router(places.router, prefix="/api/v1")

@app.post("/api/v1/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken."
        )
    new_user = User(
        username=user_in.username,
        hashed_password=hash_password(user_in.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/", include_in_schema=False)
def root():
    # Redirect the root endpoint to API documintation
    return RedirectResponse(url="/docs")

