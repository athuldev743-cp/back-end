# routes/location.py
from fastapi import APIRouter, Query
import requests  # correct import

router = APIRouter()

@router.get("/search-location")
def search_location(q: str = Query(...)):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"format": "json", "q": q, "limit": 5}
    headers = {"User-Agent": "RealEstateApp/1.0"}  # Nominatim requires User-Agent
    response = requests.get(url, params=params, headers=headers)
    return response.json()
