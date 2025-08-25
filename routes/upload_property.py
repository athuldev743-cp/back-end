from fastapi import APIRouter, HTTPException, UploadFile, Form, Depends
import requests
import os
from dotenv import load_dotenv
from routes.auth import get_current_user

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL")
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

router = APIRouter()

@router.post("/upload-property")
async def upload_property(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    location: str = Form(...),
    category: str = Form(...),
    image: UploadFile = None,
    current_user: dict = Depends(get_current_user),
):
    try:
        # Step 1: Log in to get JWT
        login_response = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
        )
        if login_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Login failed")
        
        token = login_response.json().get("access_token")
        if not token:
            raise HTTPException(status_code=500, detail="Token not received")

        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Prepare property data
        data = {
            "title": title,
            "description": description,
            "price": price,
            "location": location,
            "category": category
        }

        files = {}
        if image:
            files = {"image": image.file}

        # Step 3: Send request to backend add-property
        response = requests.post(
            f"{BACKEND_URL}/api/add-property",
            headers=headers,
            data=data,
            files=files
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
