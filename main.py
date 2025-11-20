from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List
from dotenv import load_dotenv
import os

# ==========================================================
# 🔐 환경변수 로드 (.env)
# ==========================================================
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

app = FastAPI(title="Tumae API (RESTful Signup + Onboarding)")

# ==========================================================
# 🔐 JWT / 암호화 설정
# ==========================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    safe_pw = password[:72]
    return pwd_context.hash(safe_pw)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ==========================================================
# 🗃️ Fake DB (메모리 저장)
# ==========================================================
fake_users = {}
fake_tutor_details = {}
fake_student_details = {}

# ==========================================================
# 📌 Request Models
# ==========================================================

# --- 회원가입 ---
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str                     # student | tutor
    gender: str                  # male | female | none
    terms_agreed: bool
    privacy_policy_agreed: bool


# --- 로그인 ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# --- 튜터 온보딩 ---
class TutorAvailability(BaseModel):
    weekday: int     # 0=Mon ~ 6=Sun
    time_band_id: int

class TutorDetailsRequest(BaseModel):
    user_id: int
    education_level: str
    tutor_subjects: List[dict]       # {subject_id, skill_level_id}
    tutor_lesson_types: List[int]
    tutor_availabilities: List[TutorAvailability]
    tutor_goals: List[int]
    tutor_skill_levels: List[int]
    hourly_rate_min: int
    hourly_rate_max: int
    tutor_regions: List[int]


# --- 학생 온보딩 ---
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
    student_age: int
    

# ==========================================================
# 🚀 공통 회원가입 (User 생성)
# ==========================================================
@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(user: SignupRequest):

    # 이메일 중복 체크
    if user.email in fake_users:
        raise HTTPException(409, "EMAIL_ALREADY_EXISTS")

    if user.role not in ["student", "tutor"]:
        raise HTTPException(400, "INVALID_ROLE")

    if user.gender not in ["male", "female", "none"]:
        raise HTTPException(400, "INVALID_GENDER")

    user_id = len(fake_users) + 1

    # users 테이블에 한 줄 생성 (기본정보만)
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
        "data": {
            "user_id": user_id,
            "email": user.email,
            "role": user.role,
            "signup_status": "pending_profile"
        }
    }


# ==========================================================
# 🔐 로그인
# ==========================================================
@app.post("/auth/login", status_code=status.HTTP_200_OK)
def login(data: LoginRequest):

    user = fake_users.get(data.email)
    if not user:
        raise HTTPException(404, "USER_NOT_FOUND")

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "INVALID_CREDENTIALS")

    # 프로필 미완성 상태
    if user["signup_status"] == "pending_profile":
        raise HTTPException(403, "INACTIVE_ACCOUNT")

    access_token = create_access_token({"sub": data.email})
    refresh_token = create_refresh_token({"sub": data.email})

    redirect_url = "/students" if user["role"] == "tutor" else "/tutors"

    return {
        "message": "SUCCESS",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "user_id": user["user_id"],
                "email": user["email"],
                "name": user["name"],
                "role": user["role"]
            },
            "redirect_url": redirect_url
        }
    }


# ==========================================================
# 🧑‍🏫 튜터 온보딩 (PATCH)
# ==========================================================
@app.patch("/auth/tutors/details", status_code=status.HTTP_200_OK)
def tutor_details(req: TutorDetailsRequest):

    # user_id로 사용자 찾기
    target_user = None
    for u in fake_users.values():
        if u["user_id"] == req.user_id:
            target_user = u
            break

    if not target_user:
        raise HTTPException(404, "USER_NOT_FOUND")

    if target_user["role"] != "tutor":
        raise HTTPException(403, "FORBIDDEN_ROLE")

    # 온보딩 정보 저장
    fake_tutor_details[req.user_id] = req.dict()

    # users.signup_status 갱신
    target_user["signup_status"] = "active"

    return {
        "message": "SUCCESS",
        "data": {
            "user_id": req.user_id,
            "signup_status": "active"
        }
    }


# ==========================================================
# 👨‍🎓 학생 온보딩 (PATCH)
# ==========================================================
@app.patch("/auth/students/details", status_code=status.HTTP_200_OK)
def student_details(req: StudentDetailsRequest):

    target_user = None
    for u in fake_users.values():
        if u["user_id"] == req.user_id:
            target_user = u
            break

    if not target_user:
        raise HTTPException(404, "USER_NOT_FOUND")

    if target_user["role"] != "student":
        raise HTTPException(403, "FORBIDDEN_ROLE")

    fake_student_details[req.user_id] = req.dict()

    target_user["signup_status"] = "active"

    return {
        "message": "SUCCESS",
        "data": {
            "user_id": req.user_id,
            "signup_status": "active"
        }
    }


# ==========================================================
# 🍀 헬스체크
# ==========================================================
@app.get("/")
def root():
    return {"message": "Tumae API is running on Render 🚀"}

