import os


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./travel_planner.db")


BASIC_AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME", "admin")
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "travel123")

# Third-party Art Institute of Chicago API url
ART_INSTITUTE_API_URL = os.getenv("ART_INSTITUTE_API_URL", "https://api.artic.edu/api/v1")

# Cache configuration (TTL in seconds)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
