# routes/location.py
from fastapi import APIRouter, Query, HTTPException
import requests

router = APIRouter()

@router.get("/search-location")
def search_location(q: str = Query(...)):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"format": "json", "q": q, "limit": 5}
    headers = {"User-Agent": "RealEstateApp/1.0"}  # Nominatim requires User-Agent

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # Raise error for 4xx/5xx responses
        data = response.json()
        return data
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch location: {str(e)}")
