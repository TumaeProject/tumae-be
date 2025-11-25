from fastapi import FastAPI, HTTPException, status, Query, Path, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os

# ==========================================================
# 🔐 환경변수 로드 (.env)
# ==========================================================
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# 데이터베이스 설정
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None

def get_db():
    if not SessionLocal:
        raise HTTPException(status_code=500, detail="데이터베이스 연결이 설정되지 않았습니다.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    title="Tumae API (코딩 과외 매칭 플랫폼)",
    description="회원가입/로그인 + 학생/튜터 매칭 API",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 실제 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# 🗃️ 데이터베이스 헬퍼 함수
# ==========================================================

def get_user_by_email(db: Session, email: str):
    """이메일로 사용자 조회"""
    result = db.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": email}
    )
    return result.fetchone()

def get_user_by_id(db: Session, user_id: int):
    """ID로 사용자 조회"""
    result = db.execute(
        text("SELECT * FROM users WHERE id = :user_id"),
        {"user_id": user_id}
    )
    return result.fetchone()

# ==========================================================
# 📌 Request/Response Models
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

class TutorSubject(BaseModel):
    subject_id: int
    skill_level_id: int


class TutorDetailsRequest(BaseModel):
    user_id: int
    education_level: str
    tutor_subjects: List[TutorSubject]       # {subject_id, skill_level_id}
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
    age_id: int
    student_age_id: int  # 단일 선택



# --- 프로필 업데이트 ---
class UpdateStudentProfileRequest(BaseModel):
    preferred_price_min: Optional[int] = None
    preferred_price_max: Optional[int] = None
    availability: Optional[str] = None
    subjects: Optional[List[int]] = None
    regions: Optional[List[int]] = None
    skill_levels: Optional[List[int]] = None
    goals: Optional[List[int]] = None
    lesson_types: Optional[List[int]] = None

class UpdateTutorProfileRequest(BaseModel):
    hourly_rate_min: Optional[int] = None
    hourly_rate_max: Optional[int] = None
    experience_years: Optional[int] = None
    education: Optional[str] = None
    career: Optional[str] = None
    introduction: Optional[str] = None
    availability: Optional[str] = None
    subjects: Optional[List[int]] = None
    regions: Optional[List[int]] = None
    lesson_types: Optional[List[int]] = None


# --- 튜터 온보딩 ---
class TutorAvailability(BaseModel):
    weekday: int     # 0=Mon ~ 6=Sun
    time_band_id: int

class TutorSubject(BaseModel):
    subject_id: int
    skill_level_id: int


class TutorDetailsRequest(BaseModel):
    user_id: int
    education_level: str
    tutor_subjects: List[TutorSubject]       # {subject_id, skill_level_id}
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
    student_age_id: int  # 단일 선택

# --- 학생 검색 응답 ---
class StudentListResponse(BaseModel):
    id: int
    name: str
    email: str
    preferred_price_min: Optional[int] = None
    preferred_price_max: Optional[int] = None
    subjects: List[str] = []
    regions: List[str] = []
    skill_level: Optional[str] = None
    goals: List[str] = []
    lesson_types: List[str] = []
    match_score: Optional[int] = None  # 매칭 점수 (0-100)

class StudentDetailResponse(BaseModel):
    id: int
    name: str
    email: str
    preferred_price_min: Optional[int] = None
    preferred_price_max: Optional[int] = None
    subjects: List[str] = []
    regions: List[str] = []
    skill_level: Optional[str] = None
    goals: List[str] = []
    lesson_types: List[str] = []
    created_at: str
    signup_status: str

# --- 튜터 검색 응답 ---
class TutorListResponse(BaseModel):
    id: int
    name: str
    email: str
    hourly_rate_min: Optional[int] = None
    hourly_rate_max: Optional[int] = None
    experience_years: Optional[int] = None
    rating_avg: Optional[float] = None
    rating_count: Optional[int] = None
    intro: Optional[str] = None
    subjects: List[str] = []
    regions: List[str] = []
    lesson_types: List[str] = []

class TutorDetailResponse(BaseModel):
    id: int
    name: str
    email: str
    hourly_rate_min: Optional[int] = None
    hourly_rate_max: Optional[int] = None
    experience_years: Optional[int] = None
    rating_avg: Optional[float] = None
    rating_count: Optional[int] = None
    intro: Optional[str] = None
    subjects: List[str] = []
    regions: List[str] = []
    lesson_types: List[str] = []
    created_at: str
    signup_status: str

# --- 게시글 등록 ---
class CreatePostRequest(BaseModel):
    author_id: int
    title: str
    body: str
    subject_id: int
    region_id: Optional[int] = None
    tags: Optional[List[str]] = None




# ==========================================================
# 🚀 공통 회원가입 (User 생성)
# ==========================================================
@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(user: SignupRequest, db: Session = Depends(get_db)):
    """회원가입 - 기본 정보 등록"""
    
    try:
        # 이메일 중복 체크
        existing_user = get_user_by_email(db, user.email)
        if existing_user:
            raise HTTPException(409, "EMAIL_ALREADY_EXISTS")

        if user.role not in ["student", "tutor"]:
            raise HTTPException(400, "INVALID_ROLE")

        if user.gender not in ["male", "female", "none"]:
            raise HTTPException(400, "INVALID_GENDER")

        # 비밀번호 해시화
        password_hash = hash_password(user.password)

        # users 테이블에 삽입
        result = db.execute(text("""
            INSERT INTO users (name, email, password_hash, role, gender, terms_agreed, privacy_policy_agreed, signup_status, created_at)
            VALUES (:name, :email, :password_hash, :role, :gender, :terms_agreed, :privacy_policy_agreed, 'pending_profile', NOW())
            RETURNING id, email, role, signup_status
        """), {
            "name": user.name,
            "email": user.email,
            "password_hash": password_hash,
            "role": user.role,
            "gender": user.gender,
            "terms_agreed": user.terms_agreed,
            "privacy_policy_agreed": user.privacy_policy_agreed
        })
        
        db.commit()
        new_user = result.fetchone()

        return {
            "message": "SUCCESS",
            "data": {
                "user_id": new_user[0],
                "email": new_user[1],
                "role": new_user[2],
                "signup_status": new_user[3]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"회원가입 중 오류가 발생했습니다: {str(e)}")

@app.post("/auth/login", status_code=status.HTTP_200_OK)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """로그인 - JWT 토큰 발급"""
    
    try:
        # 사용자 조회
        user = get_user_by_email(db, data.email)
        if not user:
            raise HTTPException(404, "USER_NOT_FOUND")

        # 비밀번호 검증
        if not verify_password(data.password, user.password_hash):
            raise HTTPException(401, "INVALID_CREDENTIALS")

        # 프로필 미완성 상태 체크
        if user.signup_status == "pending_profile":
            raise HTTPException(403, "INACTIVE_ACCOUNT")

        # JWT 토큰 생성
        access_token = create_access_token({"sub": data.email})
        refresh_token = create_refresh_token({"sub": data.email})

        # 역할에 따른 리다이렉트 URL
        redirect_url = "/students" if user.role == "tutor" else "/tutors"

        return {
            "message": "SUCCESS",
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "user_id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role
                },
                "redirect_url": redirect_url
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 중 오류가 발생했습니다: {str(e)}")

# ==========================================================
# 🧑‍🏫 튜터 온보딩 (PATCH)
# ==========================================================
@app.patch("/auth/tutors/details", status_code=status.HTTP_200_OK)
def tutor_details(req: TutorDetailsRequest, db: Session = Depends(get_db)):
    """튜터 상세 정보 등록"""
    
    try:
        # 사용자 존재 및 권한 확인
        user = get_user_by_id(db, req.user_id)
        if not user:
            raise HTTPException(404, "USER_NOT_FOUND")

        if user.role != "tutor":
            raise HTTPException(403, "FORBIDDEN_ROLE")

        # tutor_profiles 테이블에 데이터 삽입/업데이트
        db.execute(text("""
            INSERT INTO tutor_profiles (user_id, education_level, hourly_rate_min, hourly_rate_max, created_at)
            VALUES (:user_id, :education_level, :hourly_rate_min, :hourly_rate_max, NOW())
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                education_level = :education_level,
                hourly_rate_min = :hourly_rate_min,
                hourly_rate_max = :hourly_rate_max
        """), {
            "user_id": req.user_id,
            "education_level": req.education_level,
            "hourly_rate_min": req.hourly_rate_min,
            "hourly_rate_max": req.hourly_rate_max
        })

        # 기존 과목, 수업방식, 목표, 실력수준, 가능시간, 지역 삭제
        db.execute(text("DELETE FROM tutor_subjects WHERE tutor_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM tutor_lesson_types WHERE tutor_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM tutor_goals WHERE tutor_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM tutor_skill_levels WHERE tutor_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM tutor_availabilities WHERE tutor_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM tutor_regions WHERE tutor_id = :user_id"), {"user_id": req.user_id})

        # 튜터 과목 저장
        for subject in req.tutor_subjects:
            db.execute(text("""
                INSERT INTO tutor_subjects (tutor_id, subject_id, skill_level_id)
                VALUES (:tutor_id, :subject_id, :skill_level_id)
            """), {
                "tutor_id": req.user_id,
                "subject_id": subject.subject_id,      
                "skill_level_id": subject.skill_level_id 
            })

        # 수업 방식 저장
        for lesson_type_id in req.tutor_lesson_types:
            db.execute(text("""
                INSERT INTO tutor_lesson_types (tutor_id, lesson_type_id)
                VALUES (:tutor_id, :lesson_type_id)
            """), {
                "tutor_id": req.user_id,
                "lesson_type_id": lesson_type_id
            })

        # 가능 시간 저장
        for availability in req.tutor_availabilities:
            db.execute(text("""
                INSERT INTO tutor_availabilities (tutor_id, weekday, time_band_id)
                VALUES (:tutor_id, :weekday, :time_band_id)
            """), {
                "tutor_id": req.user_id,
                "weekday": availability.weekday,
                "time_band_id": availability.time_band_id
            })

        # 튜터 목표 저장
        for goal_id in req.tutor_goals:
            db.execute(text("""
                INSERT INTO tutor_goals (tutor_id, goal_id)
                VALUES (:tutor_id, :goal_id)
            """), {
                "tutor_id": req.user_id,
                "goal_id": goal_id
            })

        # 튜터 실력 수준 저장
        for skill_level_id in req.tutor_skill_levels:
            db.execute(text("""
                INSERT INTO tutor_skill_levels (tutor_id, skill_level_id)
                VALUES (:tutor_id, :skill_level_id)
            """), {
                "tutor_id": req.user_id,
                "skill_level_id": skill_level_id
            })

        # 튜터 지역 저장 (추가)
        for region_id in req.tutor_regions:
            db.execute(text("""
                INSERT INTO tutor_regions (tutor_id, region_id)
                VALUES (:tutor_id, :region_id)
            """), {
                "tutor_id": req.user_id,
                "region_id": region_id
            })

        # users.signup_status를 'active'로 업데이트
        db.execute(text("""
            UPDATE users 
            SET signup_status = 'active'
            WHERE id = :user_id
        """), {"user_id": req.user_id})

        db.commit()

        return {
            "message": "SUCCESS",
            "data": {
                "user_id": req.user_id,
                "signup_status": "active"
            }
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"튜터 정보 저장 중 오류가 발생했습니다: {str(e)}")


# ==========================================================
# 👨‍🎓 학생 온보딩 (PATCH)
# ==========================================================
@app.patch("/auth/students/details", status_code=status.HTTP_200_OK)
def student_details(req: StudentDetailsRequest, db: Session = Depends(get_db)):
    """학생 상세 정보 등록"""
    
    try:
        # 사용자 존재 및 권한 확인
        user = get_user_by_id(db, req.user_id)
        if not user:
            raise HTTPException(404, "USER_NOT_FOUND")

        if user.role != "student":
            raise HTTPException(403, "FORBIDDEN_ROLE")

        # student_profiles 테이블에 데이터 삽입/업데이트
        db.execute(text("""
            INSERT INTO student_profiles (user_id, age_id, preferred_price_min, preferred_price_max, created_at)
            VALUES (:user_id, :age_id, :preferred_price_min, :preferred_price_max, NOW())
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                age_id = :age_id,
                preferred_price_min = :preferred_price_min,
                preferred_price_max = :preferred_price_max
        """), {
            "user_id": req.user_id,
            "age_id": req.student_age_id,
            "preferred_price_min": req.preferred_price_min,
            "preferred_price_max": req.preferred_price_max
        })

        # 기존 과목, 목표, 수업방식, 지역, 가능시간, 실력수준 삭제
        db.execute(text("DELETE FROM student_subjects WHERE user_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM student_goals WHERE user_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM student_lesson_types WHERE user_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM student_regions WHERE user_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM student_availabilities WHERE user_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM student_skill_levels WHERE user_id = :user_id"), {"user_id": req.user_id})

        # 학생 과목 저장
        for subject_id in req.student_subjects:
            db.execute(text("""
                INSERT INTO student_subjects (user_id, subject_id)
                VALUES (:user_id, :subject_id)
            """), {
                "user_id": req.user_id,
                "subject_id": subject_id
            })

        # 학생 목표 저장
        for goal_id in req.student_goals:
            db.execute(text("""
                INSERT INTO student_goals (user_id, goal_id)
                VALUES (:user_id, :goal_id)
            """), {
                "user_id": req.user_id,
                "goal_id": goal_id
            })

        # 수업 방식 저장
        for lesson_type_id in req.student_lesson_types:
            db.execute(text("""
                INSERT INTO student_lesson_types (user_id, lesson_type_id)
                VALUES (:user_id, :lesson_type_id)
            """), {
                "user_id": req.user_id,
                "lesson_type_id": lesson_type_id
            })

        # 지역 저장
        for region_id in req.student_regions:
            db.execute(text("""
                INSERT INTO student_regions (user_id, region_id)
                VALUES (:user_id, :region_id)
            """), {
                "user_id": req.user_id,
                "region_id": region_id
            })

        # 가능 시간 저장
        for availability in req.student_availabilities:
            db.execute(text("""
                INSERT INTO student_availabilities (user_id, weekday, time_band_id)
                VALUES (:user_id, :weekday, :time_band_id)
            """), {
                "user_id": req.user_id,
                "weekday": availability.weekday,
                "time_band_id": availability.time_band_id
            })

        # 학생 실력 수준 저장
        for skill_level_id in req.student_skill_levels:
            db.execute(text("""
                INSERT INTO student_skill_levels (user_id, skill_level_id)
                VALUES (:user_id, :skill_level_id)
            """), {
                "user_id": req.user_id,
                "skill_level_id": skill_level_id
            })

        # users.signup_status를 'active'로 업데이트
        db.execute(text("""
            UPDATE users 
            SET signup_status = 'active'
            WHERE id = :user_id
        """), {"user_id": req.user_id})

        db.commit()

        return {
            "message": "SUCCESS",
            "data": {
                "user_id": req.user_id,
                "signup_status": "active"
            }
        }


        # 비밀번호 검증
        if not verify_password(data.password, user.password_hash):
            raise HTTPException(401, "INVALID_CREDENTIALS")

        # 프로필 미완성 상태 체크
        if user.signup_status == "pending_profile":
            raise HTTPException(403, "INACTIVE_ACCOUNT")

        # JWT 토큰 생성
        access_token = create_access_token({"sub": data.email})
        refresh_token = create_refresh_token({"sub": data.email})

        # 역할에 따른 리다이렉트 URL
        redirect_url = "/students" if user.role == "tutor" else "/tutors"

        return {
            "message": "SUCCESS",
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "user_id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role
                },
                "redirect_url": redirect_url
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 중 오류가 발생했습니다: {str(e)}")

# ==========================================================
# 🧑‍🏫 튜터 온보딩 (PATCH)
# ==========================================================


# @app.get("/api/students/nearby")
# async def get_nearby_students(
#     user_id: int = Query(..., description="튜터의 user_id"),
#     radius_km: float = Query(10.0, description="검색 반경 (km)"),
#     db: Session = Depends(get_db)
# ):
#     """
#     튜터 위치 기준 반경 내 학생 검색
#     latitude/longitude 사용 (Haversine 공식)
#     """
#     from math import radians, sin, cos, sqrt, atan2
    
#     # 튜터의 대표 지역 좌표 조회
#     tutor_location = db.execute(text("""
#         SELECT r.latitude, r.longitude
#         FROM tutor_regions tr
#         JOIN regions r ON tr.region_id = r.id
#         WHERE tr.tutor_id = :user_id
#         AND r.latitude IS NOT NULL
#         AND r.longitude IS NOT NULL
#         LIMIT 1
#     """), {'user_id': user_id}).fetchone()
    
#     if not tutor_location:
#         raise HTTPException(status_code=404, detail="튜터의 위치 정보가 없습니다.")
    
#     tutor_lat, tutor_lng = float(tutor_location[0]), float(tutor_location[1])
    
#     # 모든 학생 지역 조회
#     student_regions = db.execute(text("""
#         SELECT DISTINCT
#             u.id, u.name, u.email,
#             r.latitude, r.longitude
#         FROM users u
#         JOIN student_regions sr ON sr.user_id = u.id
#         JOIN regions r ON r.id = sr.region_id
#         WHERE u.role = 'student'
#         AND u.signup_status = 'active'
#         AND r.latitude IS NOT NULL
#         AND r.longitude IS NOT NULL
#     """)).fetchall()
    
#     # Haversine 공식으로 거리 계산 및 필터링
#     nearby_students = []
#     R = 6371  # 지구 반지름 (km)
    
#     for student_id, name, email, s_lat, s_lng in student_regions:
#         s_lat, s_lng = float(s_lat), float(s_lng)
        
#         # 거리 계산
#         dlat = radians(s_lat - tutor_lat)
#         dlng = radians(s_lng - tutor_lng)
        
#         a = sin(dlat/2)**2 + cos(radians(tutor_lat)) * cos(radians(s_lat)) * sin(dlng/2)**2
#         c = 2 * atan2(sqrt(a), sqrt(1-a))
#         distance_km = R * c
        
#         # 반경 내에 있으면 추가
#         if distance_km <= radius_km:
#             nearby_students.append({
#                 'id': student_id,
#                 'name': name,
#                 'email': email,
#                 'distance_km': round(distance_km, 2)
#             })
    
#     # 거리순 정렬
#     nearby_students.sort(key=lambda x: x['distance_km'])
    
#     return nearby_students

# # ==========================================================
# # 🍀 헬스체크
# # ==========================================================
# # ==========================================================
# # 🏠 루트
# # ==========================================================

@app.get("/api/students/{student_id}", response_model=StudentDetailResponse)
async def get_student_detail(
    student_id: int = Path(..., description="학생 ID"),
    db: Session = Depends(get_db)
):
    """학생 상세 정보 - 학생의 학습 목표, 선호 스타일을 보여줌"""
    
    student_result = db.execute(text("""
        SELECT 
            u.id, u.name, u.email, u.created_at, u.signup_status,
            sp.preferred_price_min, sp.preferred_price_max
        FROM users u
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        WHERE u.id = :student_id AND u.role = 'student'
    """), {'student_id': student_id})
    
    student = student_result.fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    
    # 상세 정보 조회
    subjects_result = db.execute(text("""
        SELECT s.name FROM student_subjects ss
        JOIN subjects s ON ss.subject_id = s.id
        WHERE ss.user_id = :student_id
    """), {'student_id': student_id})
    subjects = [row[0] for row in subjects_result.fetchall()]
    
    regions_result = db.execute(text("""
        SELECT CASE 
            WHEN r.level = '시도' THEN r.name
            WHEN r.level = '시군구' THEN p.name || ' ' || r.name
            ELSE r.name
        END as full_name
        FROM student_regions sr
        JOIN regions r ON sr.region_id = r.id
        LEFT JOIN regions p ON r.parent_id = p.id
        WHERE sr.user_id = :student_id
        ORDER BY r.level, r.name
    """), {'student_id': student_id})
    regions = [row[0] for row in regions_result.fetchall()]
    
    skill_result = db.execute(text("""
        SELECT sl.name FROM student_skill_levels ssl
        JOIN skill_levels sl ON ssl.skill_level_id = sl.id
        WHERE ssl.user_id = :student_id
        LIMIT 1
    """), {'student_id': student_id})
    skill_level = skill_result.scalar()
    
    goals_result = db.execute(text("""
        SELECT g.name FROM student_goals sg
        JOIN goals g ON sg.goal_id = g.id
        WHERE sg.user_id = :student_id
    """), {'student_id': student_id})
    goals = [row[0] for row in goals_result.fetchall()]
    
    lesson_types_result = db.execute(text("""
        SELECT lt.name FROM student_lesson_types slt
        JOIN lesson_types lt ON slt.lesson_type_id = lt.id
        WHERE slt.user_id = :student_id
    """), {'student_id': student_id})
    lesson_types = [row[0] for row in lesson_types_result.fetchall()]
    
    return StudentDetailResponse(
        id=student[0],
        name=student[1],
        email=student[2],
        created_at=str(student[3]),
        signup_status=student[4],
        preferred_price_min=student[5],
        preferred_price_max=student[6],
        subjects=subjects,
        regions=regions,
        skill_level=skill_level,
        goals=goals,
        lesson_types=lesson_types
    )

# ==========================================================
# 🧑‍🏫 튜터 찾기 APIs
# ==========================================================

@app.get("/api/tutors", response_model=List[TutorListResponse])
async def get_tutors(
    db: Session = Depends(get_db),
    subject: Optional[str] = Query(None, description="과목 필터 (예: 웹개발)"),
    region: Optional[str] = Query(None, description="지역 필터 (예: 서울특별시)"),
    price_min: Optional[int] = Query(None, description="최소 시급"),
    price_max: Optional[int] = Query(None, description="최대 시급"),
    min_experience: Optional[int] = Query(None, description="최소 경력 (년)"),
    min_rating: Optional[float] = Query(None, description="최소 평점"),
    lesson_type: Optional[str] = Query(None, description="수업 방식 (예: 1:1과외)"),
    limit: int = Query(20, description="결과 개수 제한"),
    offset: int = Query(0, description="결과 시작 위치")
):
    """선생님 목록 검색 - 학생의 선호 스타일과 비슷한 선생님들을 보여줌"""
    
    query = """
        SELECT DISTINCT
            u.id, u.name, u.email, u.created_at, u.signup_status,
            tp.hourly_rate_min, tp.hourly_rate_max, tp.experience_years,
            tp.rating_avg, tp.rating_count, tp.intro
        FROM users u
        LEFT JOIN tutor_profiles tp ON u.id = tp.user_id
        WHERE u.role = 'tutor' AND u.signup_status = 'active'
    """
    
    params = {}
    
    if subject:
        query += " AND EXISTS (SELECT 1 FROM tutor_subjects ts JOIN subjects s ON ts.subject_id = s.id WHERE ts.tutor_id = u.id AND s.name = :subject)"
        params['subject'] = subject
    
    if region:
        query += " AND EXISTS (SELECT 1 FROM tutor_regions tr JOIN regions r ON tr.region_id = r.id WHERE tr.tutor_id = u.id AND (r.name = :region OR r.name LIKE :region_like))"
        params['region'] = region
        params['region_like'] = f"%{region}%"
    
    if price_min:
        query += " AND (tp.hourly_rate_max IS NULL OR tp.hourly_rate_max >= :price_min)"
        params['price_min'] = price_min
    
    if price_max:
        query += " AND (tp.hourly_rate_min IS NULL OR tp.hourly_rate_min <= :price_max)"
        params['price_max'] = price_max
    
    if min_experience:
        query += " AND (tp.experience_years IS NULL OR tp.experience_years >= :min_experience)"
        params['min_experience'] = min_experience
    
    if min_rating:
        query += " AND (tp.rating_avg IS NULL OR tp.rating_avg >= :min_rating)"
        params['min_rating'] = min_rating
    
    if lesson_type:
        query += " AND EXISTS (SELECT 1 FROM tutor_lesson_types tlt JOIN lesson_types lt ON tlt.lesson_type_id = lt.id WHERE tlt.tutor_id = u.id AND lt.name = :lesson_type)"
        params['lesson_type'] = lesson_type
    
    query += " ORDER BY tp.rating_avg DESC, tp.experience_years DESC, u.id LIMIT :limit OFFSET :offset"
    params['limit'] = limit
    params['offset'] = offset
    
    result = db.execute(text(query), params)
    tutors = result.fetchall()
    
    tutor_list = []
    for tutor in tutors:
        user_id = tutor[0]
        
        # 과목 조회
        subjects_result = db.execute(text("""
            SELECT s.name FROM tutor_subjects ts
            JOIN subjects s ON ts.subject_id = s.id
            WHERE ts.tutor_id = :user_id
        """), {'user_id': user_id})
        subjects = [row[0] for row in subjects_result.fetchall()]
        
        # 지역 조회
        regions_result = db.execute(text("""
            SELECT CASE 
                WHEN r.level = '시도' THEN r.name
                WHEN r.level = '시군구' THEN p.name || ' ' || r.name
                ELSE r.name
            END as full_name
            FROM tutor_regions tr
            JOIN regions r ON tr.region_id = r.id
            LEFT JOIN regions p ON r.parent_id = p.id
            WHERE tr.tutor_id = :user_id
            ORDER BY r.level, r.name
        """), {'user_id': user_id})
        regions = [row[0] for row in regions_result.fetchall()]
        
        # 수업 방식 조회
        lesson_types_result = db.execute(text("""
            SELECT lt.name FROM tutor_lesson_types tlt
            JOIN lesson_types lt ON tlt.lesson_type_id = lt.id
            WHERE tlt.tutor_id = :user_id
        """), {'user_id': user_id})
        lesson_types = [row[0] for row in lesson_types_result.fetchall()]
        
        tutor_list.append(TutorListResponse(
            id=tutor[0],
            name=tutor[1],
            email=tutor[2],
            hourly_rate_min=tutor[5],
            hourly_rate_max=tutor[6],
            experience_years=tutor[7],
            rating_avg=tutor[8],
            rating_count=tutor[9],
            intro=tutor[10],
            subjects=subjects,
            regions=regions,
            lesson_types=lesson_types
        ))
    
    return tutor_list

@app.get("/api/tutors/{tutor_id}", response_model=TutorDetailResponse)
async def get_tutor_detail(
    tutor_id: int = Path(..., description="튜터 ID"),
    db: Session = Depends(get_db)
):
    """선생님 상세 정보 - 선생님 이력과 경력, 과외 선호 스타일을 보여줌"""
    
    tutor_result = db.execute(text("""
        SELECT 
            u.id, u.name, u.email, u.created_at, u.signup_status,
            tp.hourly_rate_min, tp.hourly_rate_max, tp.experience_years,
            tp.rating_avg, tp.rating_count, tp.intro
        FROM users u
        LEFT JOIN tutor_profiles tp ON u.id = tp.user_id
        WHERE u.id = :tutor_id AND u.role = 'tutor'
    """), {'tutor_id': tutor_id})
    
    tutor = tutor_result.fetchone()
    if not tutor:
        raise HTTPException(status_code=404, detail="튜터를 찾을 수 없습니다.")
    
    # 상세 정보 조회 (과목, 지역, 수업방식)
    subjects_result = db.execute(text("""
        SELECT s.name FROM tutor_subjects ts
        JOIN subjects s ON ts.subject_id = s.id
        WHERE ts.tutor_id = :tutor_id
    """), {'tutor_id': tutor_id})
    subjects = [row[0] for row in subjects_result.fetchall()]
    
    regions_result = db.execute(text("""
        SELECT CASE 
            WHEN r.level = '시도' THEN r.name
            WHEN r.level = '시군구' THEN p.name || ' ' || r.name
            ELSE r.name
        END as full_name
        FROM tutor_regions tr
        JOIN regions r ON tr.region_id = r.id
        LEFT JOIN regions p ON r.parent_id = p.id
        WHERE tr.tutor_id = :tutor_id
        ORDER BY r.level, r.name
    """), {'tutor_id': tutor_id})
    regions = [row[0] for row in regions_result.fetchall()]
    
    lesson_types_result = db.execute(text("""
        SELECT lt.name FROM tutor_lesson_types tlt
        JOIN lesson_types lt ON tlt.lesson_type_id = lt.id
        WHERE tlt.tutor_id = :tutor_id
    """), {'tutor_id': tutor_id})
    lesson_types = [row[0] for row in lesson_types_result.fetchall()]
    
    return TutorDetailResponse(
        id=tutor[0],
        name=tutor[1],
        email=tutor[2],
        created_at=str(tutor[3]),
        signup_status=tutor[4],
        hourly_rate_min=tutor[5],
        hourly_rate_max=tutor[6],
        experience_years=tutor[7],
        rating_avg=tutor[8],
        rating_count=tutor[9],
        intro=tutor[10],
        subjects=subjects,
        regions=regions,
        lesson_types=lesson_types
    )
# PostGIS를 활용한 거리 기반 매칭 추가 부분

@app.get("/api/students", response_model=List[StudentListResponse])
async def get_students(
    user_id: int = Query(..., description="튜터의 user_id"),
    db: Session = Depends(get_db),
    min_score: int = Query(50, description="최소 매칭 점수 (0-100)"),
    max_distance_km: Optional[float] = Query(None, description="최대 거리 (km) - 설정 시 이 거리 내 학생만"),
    limit: int = Query(20, description="결과 개수 제한"),
    offset: int = Query(0, description="결과 시작 위치")
):
    """
    학생 목록 검색 - PostGIS 거리 기반 매칭
    
    매칭 점수 기준:
    - 과목 일치: 40점
    - 거리 기반 지역 점수: 30점
      * 0-5km: 30점
      * 5-10km: 25점
      * 10-20km: 20점
      * 20-30km: 15점
      * 30-50km: 10점
    - 가격 범위 일치: 20점
    - 수업 방식 일치: 10점
    """
    
    # 튜터 확인
    tutor_check = db.execute(text("""
        SELECT id FROM users WHERE id = :user_id AND role = 'tutor'
    """), {'user_id': user_id})
    
    if not tutor_check.fetchone():
        raise HTTPException(status_code=404, detail="해당 튜터를 찾을 수 없습니다.")
    
    # 튜터의 지역 좌표 조회
    tutor_regions_coords = db.execute(text("""
        SELECT r.id, r.name, 
               ST_Y(r.geom) as latitude, 
               ST_X(r.geom) as longitude,
               r.geom
        FROM tutor_regions tr
        JOIN regions r ON tr.region_id = r.id
        WHERE tr.tutor_id = :user_id
        AND r.geom IS NOT NULL
    """), {'user_id': user_id}).fetchall()
    
    # 모든 학생 조회
    students_query = """
        SELECT 
            u.id, u.name, u.email, u.created_at, u.signup_status,
            sp.preferred_price_min, sp.preferred_price_max
        FROM users u
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        WHERE u.role = 'student' AND u.signup_status = 'active'
    """
    
    result = db.execute(text(students_query))
    all_students = result.fetchall()
    
    scored_students = []
    
    for student in all_students:
        student_user_id = student[0]
        score = 0
        min_distance = float('inf')
        
        # 1. 과목 매칭 (40점)
        tutor_subjects = db.execute(text("""
            SELECT subject_id FROM tutor_subjects WHERE tutor_id = :user_id
        """), {'user_id': user_id}).fetchall()
        tutor_subject_ids = set([row[0] for row in tutor_subjects])
        
        if tutor_subject_ids:
            student_subjects = db.execute(text("""
                SELECT subject_id FROM student_subjects WHERE user_id = :user_id
            """), {'user_id': student_user_id}).fetchall()
            student_subject_ids = set([row[0] for row in student_subjects])
            
            if tutor_subject_ids & student_subject_ids:
                score += 40
        
        # 2. 거리 기반 지역 매칭 (30점) - PostGIS 사용
        if tutor_regions_coords:
            student_regions_coords = db.execute(text("""
                SELECT r.id, r.name,
                       ST_Y(r.geom) as latitude,
                       ST_X(r.geom) as longitude,
                       r.geom
                FROM student_regions sr
                JOIN regions r ON sr.region_id = r.id
                WHERE sr.user_id = :user_id
                AND r.geom IS NOT NULL
            """), {'user_id': student_user_id}).fetchall()
            
            if student_regions_coords:
                min_distance = float('inf')
                
                # 튜터와 학생의 모든 지역 조합에서 최소 거리 찾기
                for tutor_region in tutor_regions_coords:
                    tutor_geom = tutor_region[4]
                    
                    for student_region in student_regions_coords:
                        student_geom = student_region[4]
                        
                        # PostGIS로 거리 계산 (미터 단위)
                        distance_result = db.execute(text("""
                            SELECT (ST_Distance(
                                ST_Transform(:tutor_geom::geometry, 5179),
                                ST_Transform(:student_geom::geometry, 5179)
                            ) / 1000.0)::NUMERIC(10,2) as distance_km
                        """), {
                            'tutor_geom': str(tutor_geom),
                            'student_geom': str(student_geom)
                        }).fetchone()
                        
                        distance_km = distance_result[0] if distance_result else float('inf')
                        min_distance = min(min_distance, distance_km)
                
                # 거리에 따른 점수 부여
                if min_distance <= 10:
                    score += 30      # 0-10km: 30점
                elif min_distance <= 20:
                    score += 25      # 10-20km: 25점
                elif min_distance <= 30:
                    score += 20      # 20-30km: 20점
                elif min_distance <= 50:
                    score += 15      # 30-50km: 15점
                elif min_distance <= 100:
                    score += 10      # 50-100km: 10점
                elif min_distance <= 200:
                    score += 5       # 100-200km: 5점
                # 200km 이상은 0점
        
        # 3. 가격 매칭 (20점)
        tutor_profile = db.execute(text("""
            SELECT hourly_rate_min, hourly_rate_max FROM tutor_profiles WHERE user_id = :user_id
        """), {'user_id': user_id}).fetchone()
        
        if tutor_profile and tutor_profile[0] and tutor_profile[1]:
            student_price_min = student[5]
            student_price_max = student[6]
            
            # 가격 범위 겹침 체크
            if student_price_max is None or student_price_max >= tutor_profile[0]:
                if student_price_min is None or student_price_min <= tutor_profile[1]:
                    score += 20
        
        # 4. 수업 방식 매칭 (10점)
        tutor_lesson_types = db.execute(text("""
            SELECT lesson_type_id FROM tutor_lesson_types WHERE tutor_id = :user_id
        """), {'user_id': user_id}).fetchall()
        tutor_lesson_type_ids = set([row[0] for row in tutor_lesson_types])
        
        if tutor_lesson_type_ids:
            student_lesson_types = db.execute(text("""
                SELECT lesson_type_id FROM student_lesson_types WHERE user_id = :user_id
            """), {'user_id': student_user_id}).fetchall()
            student_lesson_type_ids = set([row[0] for row in student_lesson_types])
            
            if tutor_lesson_type_ids & student_lesson_type_ids:
                score += 10
        
        # 최소 점수 필터링
        if score < min_score:
            continue
        
        # 최대 거리 필터링 (옵션)
        if max_distance_km is not None:
            if min_distance == float('inf') or min_distance > max_distance_km:
                continue
        
        scored_students.append((student, score, min_distance if min_distance != float('inf') else None))
    
    # 점수순 정렬 (같은 점수면 거리 가까운 순)
    scored_students.sort(key=lambda x: (-x[1], x[2] if x[2] else float('inf')))
    
    # 페이지네이션
    paginated_students = scored_students[offset:offset + limit]
    
    # 상세 정보 조회 및 응답 생성
    student_list = []
    for student, match_score, distance in paginated_students:
        student_user_id = student[0]
        
        # 과목 조회
        subjects_result = db.execute(text("""
            SELECT s.name FROM student_subjects ss
            JOIN subjects s ON ss.subject_id = s.id
            WHERE ss.user_id = :user_id
        """), {'user_id': student_user_id})
        subjects = [row[0] for row in subjects_result.fetchall()]
        
        # 지역 조회
        regions_result = db.execute(text("""
            SELECT CASE 
                WHEN r.level = '시도' THEN r.name
                WHEN r.level = '시군구' THEN p.name || ' ' || r.name
                ELSE r.name
            END as full_name
            FROM student_regions sr
            JOIN regions r ON sr.region_id = r.id
            LEFT JOIN regions p ON r.parent_id = p.id
            WHERE sr.user_id = :user_id
            ORDER BY r.level, r.name
        """), {'user_id': student_user_id})
        regions = [row[0] for row in regions_result.fetchall()]
        
        # 실력 수준 조회
        skill_result = db.execute(text("""
            SELECT sl.name FROM student_skill_levels ssl
            JOIN skill_levels sl ON ssl.skill_level_id = sl.id
            WHERE ssl.user_id = :user_id
            LIMIT 1
        """), {'user_id': student_user_id})
        skill_level = skill_result.scalar()
        
        # 학습 목적 조회
        goals_result = db.execute(text("""
            SELECT g.name FROM student_goals sg
            JOIN goals g ON sg.goal_id = g.id
            WHERE sg.user_id = :user_id
        """), {'user_id': student_user_id})
        goals = [row[0] for row in goals_result.fetchall()]
        
        # 수업 방식 조회
        lesson_types_result = db.execute(text("""
            SELECT lt.name FROM student_lesson_types slt
            JOIN lesson_types lt ON slt.lesson_type_id = lt.id
            WHERE slt.user_id = :user_id
        """), {'user_id': student_user_id})
        lesson_types = [row[0] for row in lesson_types_result.fetchall()]
        
        student_list.append(StudentListResponse(
            id=student[0],
            name=student[1],
            email=student[2],
            preferred_price_min=student[5],
            preferred_price_max=student[6],
            subjects=subjects,
            regions=regions,
            skill_level=skill_level,
            goals=goals,
            lesson_types=lesson_types,
            match_score=match_score,
            distance_km=round(distance, 2) if distance is not None else None
        ))
    
    return student_list


# ============================================
# 거리 계산을 위한 헬퍼 함수 (선택적)
# ============================================

def calculate_distance_postgis(db: Session, point1: tuple, point2: tuple) -> float:
    """
    PostGIS를 사용한 두 지점 간 거리 계산
    
    Args:
        db: 데이터베이스 세션
        point1: (latitude, longitude) 튜플
        point2: (latitude, longitude) 튜플
    
    Returns:
        거리 (km)
    """
    result = db.execute(text("""
        SELECT (ST_Distance(
            ST_Transform(
                ST_SetSRID(ST_MakePoint(:lng1, :lat1), 4326),
                5179
            ),
            ST_Transform(
                ST_SetSRID(ST_MakePoint(:lng2, :lat2), 4326),
                5179
            )
        ) / 1000.0)::NUMERIC(10,2) as distance_km
    """), {
        'lat1': point1[0],
        'lng1': point1[1],
        'lat2': point2[0],
        'lng2': point2[1]
    }).fetchone()
    
    return float(result[0]) if result else None


# ============================================
# 반경 내 학생 검색 (보너스 기능)
# ============================================


# @app.get("/")
# def root():
#     return {
#         "message": "SUCCESS", 
#         "service": "Tumae API - 코딩 과외 매칭 플랫폼",
#         "version": "3.0.0",
#         "docs": "/docs",
#         "endpoints": {
#             "auth": {
#                 "signup": "/auth/signup",
#                 "login": "/auth/login",
#                 "tutor_onboarding": "/auth/tutors/details",
#                 "student_onboarding": "/auth/students/details"
#             },
#             "search": {
#                 "students": "/api/students",
#                 "tutors": "/api/tutors"
#             }
#         }
#     }

# if __name__ == "__main__":
#     import uvicorn
    
#     # 환경에 따른 설정
#     host = os.getenv('HOST', '0.0.0.0')
#     port = int(os.getenv('PORT', 8000))
    
#     print("🚀 Tumae API 서버 시작!")
#     print("📖 API 문서: http://localhost:8000/docs")
#     print("🔐 회원가입: POST /auth/signup")
#     print("🔐 로그인: POST /auth/login")
#     print("🔍 학생 검색: GET /api/students")
#     print("🔍 튜터 검색: GET /api/tutors")
    
#     # 프로덕션에서는 reload=False
#     reload = os.getenv('ENVIRONMENT', 'development') == 'development'
    
#     uvicorn.run(app, host=host, port=port, reload=reload)# main.py에 추가할 프로필 업데이트 엔드포인트

# # ==========================================================
# # 📝 프로필 업데이트 API
# # ==========================================================

# # --- Request Models ---
class UpdateStudentProfileRequest(BaseModel):
    preferred_price_min: Optional[int] = None
    preferred_price_max: Optional[int] = None
    availability: Optional[str] = None
    subjects: Optional[List[int]] = None  # subject_id 배열
    regions: Optional[List[int]] = None   # region_id 배열
    skill_levels: Optional[List[int]] = None
    goals: Optional[List[int]] = None
    lesson_types: Optional[List[int]] = None

class UpdateTutorProfileRequest(BaseModel):
    hourly_rate_min: Optional[int] = None
    hourly_rate_max: Optional[int] = None
    experience_years: Optional[int] = None
    education: Optional[str] = None
    career: Optional[str] = None
    introduction: Optional[str] = None
    availability: Optional[str] = None
    subjects: Optional[List[int]] = None      # subject_id 배열
    regions: Optional[List[int]] = None       # region_id 배열
    lesson_types: Optional[List[int]] = None  # lesson_type_id 배열

# ==========================================================
# 👨‍🎓 학생 프로필 업데이트
# ==========================================================

# @app.put("/api/profile/student")
# def update_student_profile(
#     profile: UpdateStudentProfileRequest,
#     db: Session = Depends(get_db),
#     current_user_id: int = Query(..., description="현재 로그인한 사용자 ID")
# ):
#     """학생 프로필 업데이트"""
    
#     try:
#         # 사용자 확인
#         user = db.execute(text("""
#             SELECT id, role FROM users WHERE id = :user_id
#         """), {'user_id': current_user_id}).fetchone()
        
#         if not user:
#             raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
#         if user[1] != 'student':
#             raise HTTPException(status_code=403, detail="학생만 접근 가능합니다.")
        
#         # 1. student_profiles 테이블 업데이트
#         if any([profile.preferred_price_min, profile.preferred_price_max, profile.availability]):
#             # 프로필이 있는지 확인
#             existing = db.execute(text("""
#                 SELECT user_id FROM student_profiles WHERE user_id = :user_id
#             """), {'user_id': current_user_id}).fetchone()
            
#             if existing:
#                 # 업데이트
#                 update_fields = []
#                 params = {'user_id': current_user_id}
                
#                 if profile.preferred_price_min is not None:
#                     update_fields.append("preferred_price_min = :price_min")
#                     params['price_min'] = profile.preferred_price_min
                
#                 if profile.preferred_price_max is not None:
#                     update_fields.append("preferred_price_max = :price_max")
#                     params['price_max'] = profile.preferred_price_max
                
#                 if profile.availability is not None:
#                     update_fields.append("availability = :availability")
#                     params['availability'] = profile.availability
                
#                 if update_fields:
#                     db.execute(text(f"""
#                         UPDATE student_profiles 
#                         SET {', '.join(update_fields)}
#                         WHERE user_id = :user_id
#                     """), params)
#             else:
#                 # 신규 생성
#                 db.execute(text("""
#                     INSERT INTO student_profiles (user_id, preferred_price_min, preferred_price_max, availability, created_at)
#                     VALUES (:user_id, :price_min, :price_max, :availability, NOW())
#                 """), {
#                     'user_id': current_user_id,
#                     'price_min': profile.preferred_price_min,
#                     'price_max': profile.preferred_price_max,
#                     'availability': profile.availability
#                 })
        
#         # 2. 과목 업데이트
#         if profile.subjects is not None:
#             # 기존 과목 삭제
#             db.execute(text("""
#                 DELETE FROM student_subjects WHERE user_id = :user_id
#             """), {'user_id': current_user_id})
            
#             # 새 과목 추가
#             for subject_id in profile.subjects:
#                 db.execute(text("""
#                     INSERT INTO student_subjects (user_id, subject_id)
#                     VALUES (:user_id, :subject_id)
#                 """), {'user_id': current_user_id, 'subject_id': subject_id})
        
#         # 3. 지역 업데이트
#         if profile.regions is not None:
#             # 기존 지역 삭제
#             db.execute(text("""
#                 DELETE FROM student_regions WHERE user_id = :user_id
#             """), {'user_id': current_user_id})
            
#             # 새 지역 추가
#             for region_id in profile.regions:
#                 db.execute(text("""
#                     INSERT INTO student_regions (user_id, region_id)
#                     VALUES (:user_id, :region_id)
#                 """), {'user_id': current_user_id, 'region_id': region_id})
        
#         # 4. 실력 수준 업데이트
#         if profile.skill_levels is not None:
#             db.execute(text("""
#                 DELETE FROM student_skill_levels WHERE user_id = :user_id
#             """), {'user_id': current_user_id})
            
#             for skill_id in profile.skill_levels:
#                 db.execute(text("""
#                     INSERT INTO student_skill_levels (user_id, skill_level_id)
#                     VALUES (:user_id, :skill_id)
#                 """), {'user_id': current_user_id, 'skill_id': skill_id})
        
#         # 5. 학습 목적 업데이트
#         if profile.goals is not None:
#             db.execute(text("""
#                 DELETE FROM student_goals WHERE user_id = :user_id
#             """), {'user_id': current_user_id})
            
#             for goal_id in profile.goals:
#                 db.execute(text("""
#                     INSERT INTO student_goals (user_id, goal_id)
#                     VALUES (:user_id, :goal_id)
#                 """), {'user_id': current_user_id, 'goal_id': goal_id})
        
#         # 6. 수업 방식 업데이트
#         if profile.lesson_types is not None:
#             db.execute(text("""
#                 DELETE FROM student_lesson_types WHERE user_id = :user_id
#             """), {'user_id': current_user_id})
            
#             for lesson_type_id in profile.lesson_types:
#                 db.execute(text("""
#                     INSERT INTO student_lesson_types (user_id, lesson_type_id)
#                     VALUES (:user_id, :lesson_type_id)
#                 """), {'user_id': current_user_id, 'lesson_type_id': lesson_type_id})
        
#         # 7. signup_status를 'active'로 변경
#         db.execute(text("""
#             UPDATE users SET signup_status = 'active' WHERE id = :user_id
#         """), {'user_id': current_user_id})
        
#         db.commit()
        
#         return {"message": "학생 프로필이 성공적으로 업데이트되었습니다."}
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"프로필 업데이트 중 오류: {str(e)}")

# # ==========================================================
# # 👨‍🏫 튜터 프로필 업데이트
# # ==========================================================

# @app.put("/api/profile/tutor")
# def update_tutor_profile(
#     profile: UpdateTutorProfileRequest,
#     db: Session = Depends(get_db),
#     current_user_id: int = Query(..., description="현재 로그인한 사용자 ID")
# ):
#     """튜터 프로필 업데이트"""
    
#     try:
#         # 사용자 확인
#         user = db.execute(text("""
#             SELECT id, role FROM users WHERE id = :user_id
#         """), {'user_id': current_user_id}).fetchone()
        
#         if not user:
#             raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
#         if user[1] != 'tutor':
#             raise HTTPException(status_code=403, detail="튜터만 접근 가능합니다.")
        
#         # 1. tutor_profiles 테이블 업데이트
#         if any([profile.hourly_rate_min, profile.hourly_rate_max, profile.experience_years, 
#                 profile.education, profile.career, profile.introduction, profile.availability]):
            
#             # 프로필이 있는지 확인
#             existing = db.execute(text("""
#                 SELECT user_id FROM tutor_profiles WHERE user_id = :user_id
#             """), {'user_id': current_user_id}).fetchone()
            
#             if existing:
#                 # 업데이트
#                 update_fields = []
#                 params = {'user_id': current_user_id}
                
#                 if profile.hourly_rate_min is not None:
#                     update_fields.append("hourly_rate_min = :rate_min")
#                     params['rate_min'] = profile.hourly_rate_min
                
#                 if profile.hourly_rate_max is not None:
#                     update_fields.append("hourly_rate_max = :rate_max")
#                     params['rate_max'] = profile.hourly_rate_max
                
#                 if profile.experience_years is not None:
#                     update_fields.append("experience_years = :exp_years")
#                     params['exp_years'] = profile.experience_years
                
#                 if profile.education is not None:
#                     update_fields.append("education = :education")
#                     params['education'] = profile.education
                
#                 if profile.career is not None:
#                     update_fields.append("career = :career")
#                     params['career'] = profile.career
                
#                 if profile.introduction is not None:
#                     update_fields.append("introduction = :intro")
#                     params['intro'] = profile.introduction
                
#                 if profile.availability is not None:
#                     update_fields.append("availability = :availability")
#                     params['availability'] = profile.availability
                
#                 if update_fields:
#                     db.execute(text(f"""
#                         UPDATE tutor_profiles 
#                         SET {', '.join(update_fields)}
#                         WHERE user_id = :user_id
#                     """), params)
#             else:
#                 # 신규 생성
#                 db.execute(text("""
#                     INSERT INTO tutor_profiles 
#                     (user_id, hourly_rate_min, hourly_rate_max, experience_years, education, career, introduction, availability, created_at)
#                     VALUES (:user_id, :rate_min, :rate_max, :exp_years, :education, :career, :intro, :availability, NOW())
#                 """), {
#                     'user_id': current_user_id,
#                     'rate_min': profile.hourly_rate_min,
#                     'rate_max': profile.hourly_rate_max,
#                     'exp_years': profile.experience_years,
#                     'education': profile.education,
#                     'career': profile.career,
#                     'intro': profile.introduction,
#                     'availability': profile.availability
#                 })
        
#         # 2. 과목 업데이트
#         if profile.subjects is not None:
#             # 기존 과목 삭제
#             db.execute(text("""
#                 DELETE FROM tutor_subjects WHERE tutor_id = :user_id
#             """), {'user_id': current_user_id})
            
#             # 새 과목 추가
#             for subject_id in profile.subjects:
#                 db.execute(text("""
#                     INSERT INTO tutor_subjects (tutor_id, subject_id)
#                     VALUES (:user_id, :subject_id)
#                 """), {'user_id': current_user_id, 'subject_id': subject_id})
        
#         # 3. 지역 업데이트 ⭐ 이게 중요!
#         if profile.regions is not None:
#             # 기존 지역 삭제
#             db.execute(text("""
#                 DELETE FROM tutor_regions WHERE tutor_id = :user_id
#             """), {'user_id': current_user_id})
            
#             # 새 지역 추가
#             for region_id in profile.regions:
#                 db.execute(text("""
#                     INSERT INTO tutor_regions (tutor_id, region_id)
#                     VALUES (:user_id, :region_id)
#                 """), {'user_id': current_user_id, 'region_id': region_id})
        
#         # 4. 수업 방식 업데이트
#         if profile.lesson_types is not None:
#             db.execute(text("""
#                 DELETE FROM tutor_lesson_types WHERE tutor_id = :user_id
#             """), {'user_id': current_user_id})
            
#             for lesson_type_id in profile.lesson_types:
#                 db.execute(text("""
#                     INSERT INTO tutor_lesson_types (tutor_id, lesson_type_id)
#                     VALUES (:user_id, :lesson_type_id)
#                 """), {'user_id': current_user_id, 'lesson_type_id': lesson_type_id})
        
#         # 5. signup_status를 'active'로 변경
#         db.execute(text("""
#             UPDATE users SET signup_status = 'active' WHERE id = :user_id
#         """), {'user_id': current_user_id})
        
#         db.commit()
        
#         return {"message": "튜터 프로필이 성공적으로 업데이트되었습니다."}
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"프로필 업데이트 중 오류: {str(e)}")

# ==========================================================
# 📝 커뮤니티 - 게시글 등록 (POST)
# ==========================================================
@app.post("/community/posts", status_code=201)
def create_post(req: CreatePostRequest, db: Session = Depends(get_db)):
    """커뮤니티 게시글 등록"""

    try:
        # -------------------------
        # 1) 작성자 존재 확인
        # -------------------------
        author = db.execute(
            text("SELECT id FROM users WHERE id = :id"),
            {"id": req.author_id}
        ).fetchone()

        if not author:
            raise HTTPException(404, "USER_NOT_FOUND")

        # -------------------------
        # 2) 과목 존재 확인
        # -------------------------
        subject = db.execute(
            text("SELECT id FROM subjects WHERE id = :sid"),
            {"sid": req.subject_id}
        ).fetchone()

        if not subject:
            raise HTTPException(404, "SUBJECT_NOT_FOUND")

        # -------------------------
        # 3) 지역 존재 확인 (선택값)
        # -------------------------
        if req.region_id is not None:
            region = db.execute(
                text("SELECT id FROM regions WHERE id = :rid"),
                {"rid": req.region_id}
            ).fetchone()

            if not region:
                raise HTTPException(404, "REGION_NOT_FOUND")

        # -------------------------
        # 4) posts 테이블 insert
        # -------------------------
        post_result = db.execute(
            text("""
                INSERT INTO posts (author_id, title, body, subject_id, region_id, created_at)
                VALUES (:author_id, :title, :body, :subject_id, :region_id, NOW())
                RETURNING id, created_at
            """),
            {
                "author_id": req.author_id,
                "title": req.title,
                "body": req.body,
                "subject_id": req.subject_id,
                "region_id": req.region_id
            }
        )
        post = post_result.fetchone()
        post_id = post[0]

        # -------------------------
        # 5) 태그 처리
        # -------------------------
        if req.tags:
            for tag in req.tags:
                # 태그 존재 여부 확인
                tag_row = db.execute(
                    text("SELECT id FROM tags WHERE name = :name"),
                    {"name": tag}
                ).fetchone()

                if tag_row:
                    tag_id = tag_row[0]
                else:
                    # 신규 태그 생성
                    new_tag = db.execute(
                        text("INSERT INTO tags (name) VALUES (:name) RETURNING id"),
                        {"name": tag}
                    ).fetchone()
                    tag_id = new_tag[0]

                # posts_tags 매핑 테이블 저장
                db.execute(
                    text("""
                        INSERT INTO post_tags (post_id, tag_id)
                        VALUES (:post_id, :tag_id)
                    """),
                    {"post_id": post_id, "tag_id": tag_id}
                )

        db.commit()

        return {
            "message": "SUCCESS",
            "status_code": 201,
            "data": {
                "post_id": post_id,
                "created_at": str(post[1])
            }
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"게시글 등록 중 오류가 발생했습니다: {str(e)}")
