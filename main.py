from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List, Optional
from dotenv import load_dotenv
import os

# ==========================================================
# ✅ 환경변수 로드 (.env에서 읽음)
# ==========================================================
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

app = FastAPI(title="Tumae API (Render Deployable)")

# ==========================================================
# ✅ 보안 / JWT / 암호화 설정
# ==========================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=expires_days)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def hash_password(password: str) -> str:
    # bcrypt는 72바이트까지만 허용
    safe_pw = password[:72]
    return pwd_context.hash(safe_pw)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ==========================================================
# ✅ 임시 데이터 저장소 (메모리 기반)
# ==========================================================
fake_users = {}
fake_tutor_details = {}
fake_student_details = {}

# ==========================================================
# ✅ 모델 정의
# ==========================================================
# --- 공통 회원가입 ---
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str        
    role: str
    gender: str
    terms_agreed: bool
    privacy_policy_agreed: bool


# --- 로그인 ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- 튜터 선호도 입력 ---
class TutorAvailability(BaseModel):
    weekday: int
    time_band_id: int

class TutorDetailsRequest(BaseModel):
    user_id: int
    education_level: str
    tutor_subjects: List[dict]
    tutor_lesson_types: List[int]
    tutor_availabilities: List[TutorAvailability]
    tutor_goals: List[int]
    tutor_skill_levels: List[int]
    hourly_rate_min: int
    hourly_rate_max: int

# --- 학생 선호도 입력 ---
class StudentAvailability(BaseModel):
    weekday: int
    time_band_id: int

class StudentDetailsRequest(BaseModel):
    user_id: int
    student_subjects: List[int]
    student_goals: List[int]
    student_lesson_types: List[int]
    student_regions: List[int]
    student_availabilities: List[StudentAvailability]
    preferred_price_min: int
    preferred_price_max: int
    student_skill_levels: List[int]

# ==========================================================
# ✅ 회원가입 API
# ==========================================================
@app.post("/auth/signup")
def signup(user: SignupRequest):
    if user.email in fake_users:
        raise HTTPException(status_code=409, detail="EMAIL_ALREADY_EXISTS")
    if user.role not in ["student", "tutor"]:
        raise HTTPException(status_code=400, detail="INVALID_ROLE")
    if user.gender not in ["male", "female", "none"]:
        raise HTTPException(status_code=400, detail="INVALID_INPUT")

    user_id = len(fake_users) + 1
    fake_users[user.email] = {
        "user_id": user_id,
        "name": user.name,
        "email": user.email,
        "password_hash": hash_password(user.password),
        "role": user.role,
        "gender": user.gender,
        "terms_agreed": user.terms_agreed,
        "privacy_policy_agreed": user.privacy_policy_agreed,
        "signup_status": "pending_profile",
        "created_at": datetime.utcnow().isoformat()
    }

    return {
        "message": "SUCCESS",
        "status_code": 201,
        "data": {
            "user_id": user_id,
            "email": user.email,
            "role": user.role,
            "signup_status": "pending_profile"
        }
    }

# ==========================================================
# ✅ 로그인 API
# ==========================================================
@app.post("/auth/login")
def login(data: LoginRequest):
    user = fake_users.get(data.email)
    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIALS")
    if user["signup_status"] == "pending_profile":
        raise HTTPException(status_code=403, detail="INACTIVE_ACCOUNT")

    access_token = create_access_token({"sub": data.email})
    refresh_token = create_refresh_token({"sub": data.email})
    redirect_url = "/students" if user["role"] == "tutor" else "/tutors"

    return {
        "message": "SUCCESS",
        "status_code": 200,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "user_id": user["user_id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "signup_status": user["signup_status"]
            },
            "redirect_url": redirect_url
        }
    }

# ==========================================================
# ✅ 튜터 선호도 설정 API
# ==========================================================
@app.patch("/auth/tutors/details")
def tutor_details(req: TutorDetailsRequest):
    # 사용자 유효성 검증
    target_user = None
    for u in fake_users.values():
        if u["user_id"] == req.user_id:
            target_user = u
            break
    if not target_user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    if target_user["role"] != "tutor":
        raise HTTPException(status_code=403, detail="FORBIDDEN_ROLE")

    # 데이터 저장
    fake_tutor_details[req.user_id] = req.dict()
    target_user["signup_status"] = "active"

    return {
        "message": "SUCCESS",
        "status_code": 200,
        "data": {"user_id": req.user_id, "signup_status": "active"}
    }

# ==========================================================
# ✅ 학생 선호도 설정 API
# ==========================================================
@app.patch("/auth/students/details")
def student_details(req: StudentDetailsRequest):
    # 사용자 유효성 검증
    target_user = None
    for u in fake_users.values():
        if u["user_id"] == req.user_id:
            target_user = u
            break
    if not target_user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    if target_user["role"] != "student":
        raise HTTPException(status_code=403, detail="FORBIDDEN_ROLE")

    # 데이터 저장
    fake_student_details[req.user_id] = req.dict()
    target_user["signup_status"] = "active"

    return {
        "message": "SUCCESS",
        "status_code": 200,
        "data": {"user_id": req.user_id, "signup_status": "active"}
    }

# ==========================================================
# ✅ 헬스체크 (Render용)
# ==========================================================
@app.get("/")
def root():
    return {"message": "Tumae API is running on Render 🚀"}
