# app/api/endpoints/users.py 새로 작성
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()

@router.get("/students")
def get_students_simple(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    return {
        "message": "SUCCESS",
        "statusCode": 200,
        "data": {
            "students": [
                {"user_id": 1, "name": "김학생", "subjects": ["웹개발"]}
            ],
            "pagination": {"current_page": page, "total_count": 1}
        }
    }

@router.get("/tutors")  
def get_tutors_simple(
    page: int = Query(1, ge=1)
):
    return {
        "message": "SUCCESS", 
        "statusCode": 200,
        "data": {
            "tutors": [
                {"user_id": 1, "name": "김튜터", "rating_avg": 4.5}
            ],
            "pagination": {"current_page": page, "total_count": 1}
        }
    }