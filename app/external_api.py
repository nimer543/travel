import logging
import httpx
from typing import Optional, Dict, Any
from app.config import ART_INSTITUTE_API_URL, CACHE_TTL_SECONDS
from app.cache import TTLInMemoryCache

logger = logging.getLogger(__name__)

# Initialize our TTL cache for artwork validation responses
artwork_cache = TTLInMemoryCache(ttl_seconds=CACHE_TTL_SECONDS)

async def fetch_artwork_by_id(artwork_id: int) -> Optional[Dict[str, Any]]:
    cache_key = f"artwork_{artwork_id}"
    
    # 1. Check cache first
    cached_data = artwork_cache.get(cache_key)
    if cached_data is not None:
        logger.info(f"Cache hit for artwork ID: {artwork_id}")
        return cached_data

    # 2. Fetch from external API
    url = f"{ART_INSTITUTE_API_URL}/artworks/{artwork_id}"
    params = {"fields": "id,title"}  
    logger.info(f"Cache miss. Fetching artwork {artwork_id} from {url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                json_data = response.json()
                artwork_data = json_data.get("data")
                if artwork_data:
                    # Cache the result
                    artwork_cache.set(cache_key, artwork_data)
                    return artwork_data
            elif response.status_code == 404:
                logger.warning(f"Artwork with ID {artwork_id} not found (404) in external API")
                return None
            else:
                logger.error(f"External API returned status {response.status_code} for artwork ID {artwork_id}")
                return None
                
    except httpx.RequestError as e:
        logger.error(f"Network error when calling Art Institute API: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating artwork {artwork_id}: {str(e)}")
        return None
