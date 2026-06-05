
## Features

- Travel Projects: Create, read, update, and delete travel projects. A project cannot be deleted if any of its places are already marked as visited.
- Project Places: Add places from the Art Institute of Chicago API (validated using their endpoints). Max 10 places per project. Prevents duplicate places.
- Project Completion: A project is automatically marked as completed when all of its places are visited.
- User Authentication: Simple basic authentication. Supports dynamic user registration.
- In-memory Caching: Caches external API responses for 5 minutes.
- Pagination and Filtering: List projects with limit, offset, and filters.

## Project Structure

- app/main.py: App entrypoint and registration endpoint.
- app/config.py: Environment variables and configuration.
- app/database.py: Database connection and SessionLocal.
- app/models.py: SQLAlchemy models for User, Project, and ProjectPlace.
- app/schemas.py: Pydantic request and response schemas.
- app/auth.py: Password hashing and authentication dependency.
- app/cache.py: Simple TTL caching utility.
- app/external_api.py: Client for the Art Institute of Chicago API.
- app/routers/projects.py: Routes for managing travel projects.
- app/routers/places.py: Routes for managing places in projects.
- tests/test_api.py: Pytest test cases.
- Dockerfile: Docker config.
- docker-compose.yml: Docker Compose config.
- requirements.txt: Dependencies list.
- travel_planner.postman_collection.json: Exported Postman collection.

## Setup and Running

### Running Locally

1. Create a virtual environment and activate it:
   python3 -m venv venv
   source venv/bin/activate

2. Install dependencies:
   pip install -r requirements.txt

3. Start the server:
   uvicorn app.main:app --reload

4. Access the API documentation at http://127.0.0.1:8000/docs

### Running with Docker

1. Start the containers:
   docker-compose up --build -d

2. The server will be available at http://localhost:8000/docs

3. Stop the containers:
   docker-compose down

## Authentication

All endpoints (except the registration endpoint) are protected by Basic Authentication. 

You can register a new user:
- Endpoint: POST /api/v1/register
- Request body:
  {
      "username": "myuser",
      "password": "mypassword"
  }

Once registered, use these credentials for Basic Auth.

Alternatively, you can use the default preconfigured credentials:
- Username: admin
- Password: travel123

## Running Tests

To run the automated tests, execute:
pytest
