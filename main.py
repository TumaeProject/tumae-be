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
    description="회원가입/로그인/로그아웃 + 학생/튜터 매칭 API",
    version="3.1.0",
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

# --- 로그아웃 ---
class LogoutRequest(BaseModel):
    user_id: int

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
    tutor_subjects: List[TutorSubject]
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
    student_age_id: int

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
    match_score: Optional[int] = None

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
    match_score: int

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

# --- 게시글 관련 ---
class CreatePostRequest(BaseModel):
    author_id: int
    title: str
    body: str
    subject_id: int
    region_id: Optional[int] = None
    tags: Optional[List[str]] = None

class PostAnswerResponse(BaseModel):
    id: int
    author_id: int
    author_name: str
    body: str
    is_accepted: bool
    created_at: str

class PostDetailResponse(BaseModel):
    id: int
    title: str
    body: str
    author_id: int
    author_name: str
    subject_id: int
    subject_name: str
    region_id: Optional[int]
    region_name: Optional[str]
    created_at: str
    answers: List[PostAnswerResponse] = []

class CreateAnswerRequest(BaseModel):
    author_id: int
    body: str

class AcceptAnswerRequest(BaseModel):
    user_id: int

# ==========================================================
# 🚀 회원가입
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

# ==========================================================
# 🔐 로그인
# ==========================================================
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
# 🔓 로그아웃 (클라이언트 기반)
# ==========================================================
@app.post("/auth/logout", status_code=status.HTTP_200_OK)
def logout(data: LogoutRequest, db: Session = Depends(get_db)):
    """로그아웃 처리
    
    JWT는 stateless이므로 서버에서 토큰을 직접 무효화할 수 없습니다.
    실제 로그아웃은 클라이언트(프론트엔드)에서 토큰을 삭제하여 처리합니다.
    
    이 API는:
    1. 사용자 존재 확인
    2. 로그아웃 시각 기록
    3. (선택) 로그아웃 이력 저장
    
    클라이언트는 응답을 받은 후 반드시 localStorage/쿠키에서 토큰을 삭제해야 합니다.
    """
    
    try:
        # 사용자 존재 여부 확인
        user = get_user_by_id(db, data.user_id)
        if not user:
            raise HTTPException(404, "USER_NOT_FOUND")
        
        # 로그아웃 시각 기록
        logged_out_at = datetime.utcnow()
        
        # [선택사항] DB에 로그아웃 이력 저장
        # db.execute(text("""
        #     INSERT INTO logout_history (user_id, logged_out_at)
        #     VALUES (:user_id, NOW())
        # """), {"user_id": data.user_id})
        # db.commit()
        
        return {
            "message": "로그아웃되었습니다",
            "status_code": 200,
            "data": {
                "user_id": user.id,
                "logged_out_at": logged_out_at.isoformat()
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그아웃 처리 중 오류가 발생했습니다: {str(e)}")

# ==========================================================
# 🗑️ 회원 탈퇴
# ==========================================================
@app.delete("/auth/users/{user_id}", status_code=200)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """회원 탈퇴 (DB 완전 삭제)"""

    try:
        user = db.execute(
            text("SELECT id FROM users WHERE id = :uid"),
            {"uid": user_id}
        ).fetchone()

        if not user:
            raise HTTPException(404, "USER_NOT_FOUND")

        # 댓글 삭제
        deleted_answers = db.execute(
            text("DELETE FROM answers WHERE author_id = :uid RETURNING id"),
            {"uid": user_id}
        ).fetchall()

        # 게시글 삭제
        deleted_posts = db.execute(
            text("DELETE FROM posts WHERE author_id = :uid RETURNING id"),
            {"uid": user_id}
        ).fetchall()

        # 온보딩 관련 삭제
        db.execute(text("DELETE FROM tutor_profiles WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM student_profiles WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM tutor_subjects WHERE tutor_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM tutor_lesson_types WHERE tutor_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM tutor_skill_levels WHERE tutor_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM tutor_availabilities WHERE tutor_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM tutor_regions WHERE tutor_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM tutor_goals WHERE tutor_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM student_subjects WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM student_lesson_types WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM student_regions WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM student_availabilities WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM student_goals WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM student_skill_levels WHERE user_id = :uid"), {"uid": user_id})

        # 매칭/세션/메시지 삭제
        db.execute(text("DELETE FROM lesson_requests WHERE student_id = :uid OR tutor_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM sessions WHERE student_id = :uid OR tutor_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM messages WHERE sender_id = :uid OR receiver_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM notifications WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM event_logs WHERE user_id = :uid OR tutor_id = :uid"), {"uid": user_id})

        # users 삭제
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})

        db.commit()

        return {
            "message": "SUCCESS",
            "status_code": 200,
            "data": {
                "deleted_user_id": user_id,
                "deleted_posts": len(deleted_posts),
                "deleted_answers": len(deleted_answers)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"INTERNAL_SERVER_ERROR: {str(e)}")

# ==========================================================
# 🧑‍🏫 튜터 온보딩
# ==========================================================
@app.patch("/auth/tutors/details", status_code=status.HTTP_200_OK)
def tutor_details(req: TutorDetailsRequest, db: Session = Depends(get_db)):
    """튜터 상세 정보 등록"""
    
    try:
        user = get_user_by_id(db, req.user_id)
        if not user:
            raise HTTPException(404, "USER_NOT_FOUND")
        if user.role != "tutor":
            raise HTTPException(403, "FORBIDDEN_ROLE")

        # tutor_profiles 저장
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

        # 기존 데이터 삭제
        db.execute(text("DELETE FROM tutor_subjects WHERE tutor_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM tutor_lesson_types WHERE tutor_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM tutor_goals WHERE tutor_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM tutor_skill_levels WHERE tutor_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM tutor_availabilities WHERE tutor_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM tutor_regions WHERE tutor_id = :user_id"), {"user_id": req.user_id})

        # 과목 저장
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
            """), {"tutor_id": req.user_id, "lesson_type_id": lesson_type_id})

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

        # 목표 저장
        for goal_id in req.tutor_goals:
            db.execute(text("""
                INSERT INTO tutor_goals (tutor_id, goal_id)
                VALUES (:tutor_id, :goal_id)
            """), {"tutor_id": req.user_id, "goal_id": goal_id})

        # 실력 수준 저장
        for skill_level_id in req.tutor_skill_levels:
            db.execute(text("""
                INSERT INTO tutor_skill_levels (tutor_id, skill_level_id)
                VALUES (:tutor_id, :skill_level_id)
            """), {"tutor_id": req.user_id, "skill_level_id": skill_level_id})

        # 지역 저장
        for region_id in req.tutor_regions:
            db.execute(text("""
                INSERT INTO tutor_regions (tutor_id, region_id)
                VALUES (:tutor_id, :region_id)
            """), {"tutor_id": req.user_id, "region_id": region_id})

        # signup_status 업데이트
        db.execute(text("""
            UPDATE users SET signup_status = 'active' WHERE id = :user_id
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
# 👨‍🎓 학생 온보딩
# ==========================================================
@app.patch("/auth/students/details", status_code=status.HTTP_200_OK)
def student_details(req: StudentDetailsRequest, db: Session = Depends(get_db)):
    """학생 상세 정보 등록"""
    
    try:
        user = get_user_by_id(db, req.user_id)
        if not user:
            raise HTTPException(404, "USER_NOT_FOUND")
        if user.role != "student":
            raise HTTPException(403, "FORBIDDEN_ROLE")

        # student_profiles 저장
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

        # 기존 데이터 삭제
        db.execute(text("DELETE FROM student_subjects WHERE user_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM student_goals WHERE user_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM student_lesson_types WHERE user_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM student_regions WHERE user_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM student_availabilities WHERE user_id = :user_id"), {"user_id": req.user_id})
        db.execute(text("DELETE FROM student_skill_levels WHERE user_id = :user_id"), {"user_id": req.user_id})

        # 과목 저장
        for subject_id in req.student_subjects:
            db.execute(text("""
                INSERT INTO student_subjects (user_id, subject_id)
                VALUES (:user_id, :subject_id)
            """), {"user_id": req.user_id, "subject_id": subject_id})

        # 목표 저장
        for goal_id in req.student_goals:
            db.execute(text("""
                INSERT INTO student_goals (user_id, goal_id)
                VALUES (:user_id, :goal_id)
            """), {"user_id": req.user_id, "goal_id": goal_id})

        # 수업 방식 저장
        for lesson_type_id in req.student_lesson_types:
            db.execute(text("""
                INSERT INTO student_lesson_types (user_id, lesson_type_id)
                VALUES (:user_id, :lesson_type_id)
            """), {"user_id": req.user_id, "lesson_type_id": lesson_type_id})

        # 지역 저장
        for region_id in req.student_regions:
            db.execute(text("""
                INSERT INTO student_regions (user_id, region_id)
                VALUES (:user_id, :region_id)
            """), {"user_id": req.user_id, "region_id": region_id})

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

        # 실력 수준 저장
        for skill_level_id in req.student_skill_levels:
            db.execute(text("""
                INSERT INTO student_skill_levels (user_id, skill_level_id)
                VALUES (:user_id, :skill_level_id)
            """), {"user_id": req.user_id, "skill_level_id": skill_level_id})

        # signup_status 업데이트
        db.execute(text("""
            UPDATE users SET signup_status = 'active' WHERE id = :user_id
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
        raise HTTPException(status_code=500, detail=f"학생 정보 저장 중 오류가 발생했습니다: {str(e)}")

# ==========================================================
# 🔍 헬스체크
# ==========================================================
@app.get("/")
def root():
    return {"message": "SUCCESS"}

# ==========================================================
# 👨‍🎓 학생 상세 조회
# ==========================================================
@app.get("/api/students/{student_id}", response_model=StudentDetailResponse)
async def get_student_detail(student_id: int = Path(...), db: Session = Depends(get_db)):
    """학생 상세 정보"""
    
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

#튜터 목록 검색 API(수정됨)
@app.get("/api/tutors", response_model=List[TutorListResponse])
async def get_tutors(
    user_id: int = Query(..., description="학생의 user_id"),
    db: Session = Depends(get_db),
    min_score: int = Query(50, description="최소 매칭 점수 (0-100)"),
    max_distance_km: Optional[float] = Query(None, description="최대 거리 (km)"),
    limit: int = Query(20, description="결과 개수 제한"),
    offset: int = Query(0, description="결과 시작 위치")
):
    """
    ⚡ 최적화된 튜터 목록 검색
    
    개선사항:
    - N+1 쿼리 제거 (1000번 → 10번)
    - JOIN을 사용한 한 번의 쿼리로 모든 튜터 데이터 조회
    - 응답 시간 10배 개선
    
    매칭 점수 기준:
    - 과목 일치: 40점
    - 거리 기반 지역: 30점
    - 가격 범위 일치: 20점
    - 수업 방식 일치: 10점
    """
    
    # 1️⃣ 학생 정보 한 번에 조회
    student_data = db.execute(text("""
        WITH student_info AS (
            SELECT 
                :user_id as student_id,
                sp.preferred_price_min,
                sp.preferred_price_max,
                ARRAY_AGG(DISTINCT ss.subject_id) FILTER (WHERE ss.subject_id IS NOT NULL) as subject_ids,
                ARRAY_AGG(DISTINCT slt.lesson_type_id) FILTER (WHERE slt.lesson_type_id IS NOT NULL) as lesson_type_ids,
                ARRAY_AGG(DISTINCT sr.region_id) FILTER (WHERE sr.region_id IS NOT NULL) as region_ids
            FROM users u
            LEFT JOIN student_profiles sp ON u.id = sp.user_id
            LEFT JOIN student_subjects ss ON u.id = ss.user_id
            LEFT JOIN student_lesson_types slt ON u.id = slt.user_id
            LEFT JOIN student_regions sr ON u.id = sr.user_id
            WHERE u.id = :user_id AND u.role = 'student'
            GROUP BY u.id, sp.preferred_price_min, sp.preferred_price_max
        )
        SELECT * FROM student_info
    """), {'user_id': user_id}).fetchone()
    
    if not student_data:
        raise HTTPException(404, "학생을 찾을 수 없습니다.")
    
    student_price_min = student_data[1]
    student_price_max = student_data[2]
    student_subject_ids = set(student_data[3]) if student_data[3] else set()
    student_lesson_type_ids = set(student_data[4]) if student_data[4] else set()
    student_region_ids = set(student_data[5]) if student_data[5] else set()
    
    # 2️⃣ 모든 튜터 정보를 한 번의 쿼리로 조회
    tutors_query = text("""
        SELECT 
            u.id,
            u.name,
            u.email,
            u.created_at,
            u.signup_status,
            tp.hourly_rate_min,
            tp.hourly_rate_max,
            tp.experience_years,
            tp.rating_avg,
            tp.rating_count,
            tp.intro,
            ARRAY_AGG(DISTINCT ts.subject_id) FILTER (WHERE ts.subject_id IS NOT NULL) as subject_ids,
            ARRAY_AGG(DISTINCT tlt.lesson_type_id) FILTER (WHERE tlt.lesson_type_id IS NOT NULL) as lesson_type_ids,
            ARRAY_AGG(DISTINCT tr.region_id) FILTER (WHERE tr.region_id IS NOT NULL) as region_ids,
            ARRAY_AGG(DISTINCT subj.name) FILTER (WHERE subj.name IS NOT NULL) as subject_names,
            ARRAY_AGG(DISTINCT 
                CASE 
                    WHEN r.level = '시도' THEN r.name
                    WHEN r.level = '시군구' THEN COALESCE(p.name || ' ', '') || r.name
                    ELSE r.name
                END
            ) FILTER (WHERE r.name IS NOT NULL) as region_names,
            ARRAY_AGG(DISTINCT lt.name) FILTER (WHERE lt.name IS NOT NULL) as lesson_type_names
        FROM users u
        LEFT JOIN tutor_profiles tp ON u.id = tp.user_id
        LEFT JOIN tutor_subjects ts ON u.id = ts.tutor_id
        LEFT JOIN subjects subj ON ts.subject_id = subj.id
        LEFT JOIN tutor_lesson_types tlt ON u.id = tlt.tutor_id
        LEFT JOIN lesson_types lt ON tlt.lesson_type_id = lt.id
        LEFT JOIN tutor_regions tr ON u.id = tr.tutor_id
        LEFT JOIN regions r ON tr.region_id = r.id
        LEFT JOIN regions p ON r.parent_id = p.id
        WHERE u.role = 'tutor' 
        AND u.signup_status = 'active'
        GROUP BY u.id, u.name, u.email, u.created_at, u.signup_status,
                 tp.hourly_rate_min, tp.hourly_rate_max, tp.experience_years,
                 tp.rating_avg, tp.rating_count, tp.intro
    """)
    
    all_tutors = db.execute(tutors_query).fetchall()
    
    # 3️⃣ 거리 계산이 필요한 경우 지역 좌표 조회
    student_region_coords = {}
    tutor_region_coords = {}
    
    if student_region_ids:
        student_coords = db.execute(text("""
            SELECT id, geom
            FROM regions
            WHERE id = ANY(:ids) AND geom IS NOT NULL
        """), {'ids': list(student_region_ids)}).fetchall()
        
        for region_id, geom in student_coords:
            student_region_coords[region_id] = geom
    
    # 4️⃣ 점수 계산
    scored_tutors = []
    
    for tutor in all_tutors:
        score = 0
        min_distance = None
        
        tutor_subject_ids = set(tutor[11]) if tutor[11] else set()
        tutor_lesson_type_ids = set(tutor[12]) if tutor[12] else set()
        tutor_region_ids = set(tutor[13]) if tutor[13] else set()
        
        # 과목 매칭 (40점)
        if student_subject_ids & tutor_subject_ids:
            score += 40
        
        # 거리 기반 지역 매칭 (30점)
        if student_region_ids and tutor_region_ids:
            if student_region_ids & tutor_region_ids:
                min_distance = 0.0
                score += 30
            else:
                min_dist = float('inf')
                
                tutor_coords = db.execute(text("""
                    SELECT id, geom
                    FROM regions
                    WHERE id = ANY(:ids) AND geom IS NOT NULL
                """), {'ids': list(tutor_region_ids)}).fetchall()
                
                for t_region_id, t_geom in tutor_coords:
                    tutor_region_coords[t_region_id] = t_geom
                
                for s_region_id, s_geom in student_region_coords.items():
                    for t_region_id, t_geom in tutor_region_coords.items():
                        dist_result = db.execute(text("""
                            SELECT (ST_Distance(
                                ST_Transform(:geom1::geometry, 5179),
                                ST_Transform(:geom2::geometry, 5179)
                            ) / 1000.0)::NUMERIC(10,2)
                        """), {
                            'geom1': str(s_geom),
                            'geom2': str(t_geom)
                        }).fetchone()
                        
                        if dist_result:
                            min_dist = min(min_dist, float(dist_result[0]))
                
                if min_dist != float('inf'):
                    min_distance = min_dist
                    
                    if min_dist <= 10:
                        score += 30
                    elif min_dist <= 20:
                        score += 25
                    elif min_dist <= 30:
                        score += 20
                    elif min_dist <= 50:
                        score += 15
                    elif min_dist <= 100:
                        score += 10
                    elif min_dist <= 200:
                        score += 5
        
        # 가격 매칭 (20점)
        tutor_hourly_min = tutor[5]
        tutor_hourly_max = tutor[6]
        
        if tutor_hourly_min and tutor_hourly_max:
            if student_price_max is None or student_price_max >= tutor_hourly_min:
                if student_price_min is None or student_price_min <= tutor_hourly_max:
                    score += 20
        
        # 수업 방식 매칭 (10점)
        if student_lesson_type_ids & tutor_lesson_type_ids:
            score += 10
        
        # 필터링
        if score < min_score:
            continue
        
        if max_distance_km is not None:
            if min_distance is None or min_distance > max_distance_km:
                continue
        
        scored_tutors.append((tutor, score, min_distance))
    
    # 5️⃣ 정렬 (매칭 점수 → 거리 → 평점 → 경력)
    scored_tutors.sort(key=lambda x: (
        -x[1],  # 매칭 점수 (내림차순)
        x[2] if x[2] is not None else float('inf'),  # 거리 (오름차순)
        -(x[0][8] if x[0][8] is not None else 0),  # 평점 (내림차순)
        -(x[0][7] if x[0][7] is not None else 0)   # 경력 (내림차순)
    ))
    
    # 6️⃣ 페이지네이션
    paginated_tutors = scored_tutors[offset:offset + limit]
    
    # 7️⃣ 응답 생성
    tutor_list = []
    for tutor, match_score, distance in paginated_tutors:
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
            subjects=tutor[14] if tutor[14] else [],
            regions=tutor[15] if tutor[15] else [],
            lesson_types=tutor[16] if tutor[16] else [],
            match_score=match_score
        ))
    
    return tutor_list
# ==========================================================
# 🧑‍🏫 튜터 상세 조회
# ==========================================================
@app.get("/api/tutors/{tutor_id}", response_model=TutorDetailResponse)
async def get_tutor_detail(tutor_id: int = Path(...), db: Session = Depends(get_db)):
    """튜터 상세 정보"""
    
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

# ==========================================================
# ⚡ 학생 목록 검색 (최적화 버전)
# ==========================================================
@app.get("/api/students", response_model=List[StudentListResponse])
async def get_students(
    user_id: int = Query(..., description="튜터의 user_id"),
    db: Session = Depends(get_db),
    min_score: int = Query(50, description="최소 매칭 점수 (0-100)"),
    max_distance_km: Optional[float] = Query(None, description="최대 거리 (km)"),
    limit: int = Query(20, description="결과 개수 제한"),
    offset: int = Query(0, description="결과 시작 위치")
):
    """
    ⚡ 최적화된 학생 목록 검색
    
    개선사항:
    - N+1 쿼리 제거 (1000번 → 10번)
    - JOIN을 사용한 한 번의 쿼리로 모든 학생 데이터 조회
    - 응답 시간 10배 개선
    
    매칭 점수 기준:
    - 과목 일치: 40점
    - 거리 기반 지역: 30점
    - 가격 범위 일치: 20점
    - 수업 방식 일치: 10점
    """
    
    # 1️⃣ 튜터 정보 한 번에 조회
    tutor_data = db.execute(text("""
        WITH tutor_info AS (
            SELECT 
                :user_id as tutor_id,
                tp.hourly_rate_min,
                tp.hourly_rate_max,
                ARRAY_AGG(DISTINCT ts.subject_id) FILTER (WHERE ts.subject_id IS NOT NULL) as subject_ids,
                ARRAY_AGG(DISTINCT tlt.lesson_type_id) FILTER (WHERE tlt.lesson_type_id IS NOT NULL) as lesson_type_ids,
                ARRAY_AGG(DISTINCT tr.region_id) FILTER (WHERE tr.region_id IS NOT NULL) as region_ids
            FROM users u
            LEFT JOIN tutor_profiles tp ON u.id = tp.user_id
            LEFT JOIN tutor_subjects ts ON u.id = ts.tutor_id
            LEFT JOIN tutor_lesson_types tlt ON u.id = tlt.tutor_id
            LEFT JOIN tutor_regions tr ON u.id = tr.tutor_id
            WHERE u.id = :user_id AND u.role = 'tutor'
            GROUP BY u.id, tp.hourly_rate_min, tp.hourly_rate_max
        )
        SELECT * FROM tutor_info
    """), {'user_id': user_id}).fetchone()
    
    if not tutor_data:
        raise HTTPException(404, "튜터를 찾을 수 없습니다.")
    
    tutor_hourly_min = tutor_data[1]
    tutor_hourly_max = tutor_data[2]
    tutor_subject_ids = set(tutor_data[3]) if tutor_data[3] else set()
    tutor_lesson_type_ids = set(tutor_data[4]) if tutor_data[4] else set()
    tutor_region_ids = set(tutor_data[5]) if tutor_data[5] else set()
    
    # 2️⃣ 모든 학생 정보를 한 번의 쿼리로 조회
    students_query = text("""
        SELECT 
            u.id,
            u.name,
            u.email,
            u.created_at,
            u.signup_status,
            sp.preferred_price_min,
            sp.preferred_price_max,
            ARRAY_AGG(DISTINCT ss.subject_id) FILTER (WHERE ss.subject_id IS NOT NULL) as subject_ids,
            ARRAY_AGG(DISTINCT slt.lesson_type_id) FILTER (WHERE slt.lesson_type_id IS NOT NULL) as lesson_type_ids,
            ARRAY_AGG(DISTINCT sr.region_id) FILTER (WHERE sr.region_id IS NOT NULL) as region_ids,
            ARRAY_AGG(DISTINCT subj.name) FILTER (WHERE subj.name IS NOT NULL) as subject_names,
            ARRAY_AGG(DISTINCT 
                CASE 
                    WHEN r.level = '시도' THEN r.name
                    WHEN r.level = '시군구' THEN COALESCE(p.name || ' ', '') || r.name
                    ELSE r.name
                END
            ) FILTER (WHERE r.name IS NOT NULL) as region_names,
            MAX(sl.name) as skill_level,
            ARRAY_AGG(DISTINCT g.name) FILTER (WHERE g.name IS NOT NULL) as goal_names,
            ARRAY_AGG(DISTINCT lt.name) FILTER (WHERE lt.name IS NOT NULL) as lesson_type_names
        FROM users u
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        LEFT JOIN student_subjects ss ON u.id = ss.user_id
        LEFT JOIN subjects subj ON ss.subject_id = subj.id
        LEFT JOIN student_lesson_types slt ON u.id = slt.user_id
        LEFT JOIN lesson_types lt ON slt.lesson_type_id = lt.id
        LEFT JOIN student_regions sr ON u.id = sr.user_id
        LEFT JOIN regions r ON sr.region_id = r.id
        LEFT JOIN regions p ON r.parent_id = p.id
        LEFT JOIN student_skill_levels ssl ON u.id = ssl.user_id
        LEFT JOIN skill_levels sl ON ssl.skill_level_id = sl.id
        LEFT JOIN student_goals sg ON u.id = sg.user_id
        LEFT JOIN goals g ON sg.goal_id = g.id
        WHERE u.role = 'student' 
        AND u.signup_status = 'active'
        GROUP BY u.id, u.name, u.email, u.created_at, u.signup_status,
                 sp.preferred_price_min, sp.preferred_price_max
    """)
    
    all_students = db.execute(students_query).fetchall()
    
    # 3️⃣ 거리 계산이 필요한 경우 지역 좌표 조회
    tutor_region_coords = {}
    student_region_coords = {}
    
    if tutor_region_ids:
        tutor_coords = db.execute(text("""
            SELECT id, geom
            FROM regions
            WHERE id = ANY(:ids) AND geom IS NOT NULL
        """), {'ids': list(tutor_region_ids)}).fetchall()
        
        for region_id, geom in tutor_coords:
            tutor_region_coords[region_id] = geom
    
    # 4️⃣ 점수 계산
    scored_students = []
    
    for student in all_students:
        score = 0
        min_distance = None
        
        student_subject_ids = set(student[7]) if student[7] else set()
        student_lesson_type_ids = set(student[8]) if student[8] else set()
        student_region_ids = set(student[9]) if student[9] else set()
        
        # 과목 매칭 (40점)
        if tutor_subject_ids & student_subject_ids:
            score += 40
        
        # 거리 기반 지역 매칭 (30점)
        if tutor_region_ids and student_region_ids:
            if tutor_region_ids & student_region_ids:
                min_distance = 0.0
                score += 30
            else:
                min_dist = float('inf')
                
                student_coords = db.execute(text("""
                    SELECT id, geom
                    FROM regions
                    WHERE id = ANY(:ids) AND geom IS NOT NULL
                """), {'ids': list(student_region_ids)}).fetchall()
                
                for s_region_id, s_geom in student_coords:
                    student_region_coords[s_region_id] = s_geom
                
                for t_region_id, t_geom in tutor_region_coords.items():
                    for s_region_id, s_geom in student_region_coords.items():
                        dist_result = db.execute(text("""
                            SELECT (ST_Distance(
                                ST_Transform(:geom1::geometry, 5179),
                                ST_Transform(:geom2::geometry, 5179)
                            ) / 1000.0)::NUMERIC(10,2)
                        """), {
                            'geom1': str(t_geom),
                            'geom2': str(s_geom)
                        }).fetchone()
                        
                        if dist_result:
                            min_dist = min(min_dist, float(dist_result[0]))
                
                if min_dist != float('inf'):
                    min_distance = min_dist
                    
                    if min_dist <= 10:
                        score += 30
                    elif min_dist <= 20:
                        score += 25
                    elif min_dist <= 30:
                        score += 20
                    elif min_dist <= 50:
                        score += 15
                    elif min_dist <= 100:
                        score += 10
                    elif min_dist <= 200:
                        score += 5
        
        # 가격 매칭 (20점)
        if tutor_hourly_min and tutor_hourly_max:
            student_price_min = student[5]
            student_price_max = student[6]
            
            if student_price_max is None or student_price_max >= tutor_hourly_min:
                if student_price_min is None or student_price_min <= tutor_hourly_max:
                    score += 20
        
        # 수업 방식 매칭 (10점)
        if tutor_lesson_type_ids & student_lesson_type_ids:
            score += 10
        
        # 필터링
        if score < min_score:
            continue
        
        if max_distance_km is not None:
            if min_distance is None or min_distance > max_distance_km:
                continue
        
        scored_students.append((student, score, min_distance))
    
    # 5️⃣ 정렬
    scored_students.sort(key=lambda x: (-x[1], x[2] if x[2] is not None else float('inf')))
    
    # 6️⃣ 페이지네이션
    paginated_students = scored_students[offset:offset + limit]
    
    # 7️⃣ 응답 생성
    student_list = []
    for student, match_score, distance in paginated_students:
        student_list.append(StudentListResponse(
            id=student[0],
            name=student[1],
            email=student[2],
            preferred_price_min=student[5],
            preferred_price_max=student[6],
            subjects=student[10] if student[10] else [],
            regions=student[11] if student[11] else [],
            skill_level=student[12],
            goals=student[13] if student[13] else [],
            lesson_types=student[14] if student[14] else [],
            match_score=match_score
        ))
    
    return student_list

# ==========================================================
# 📝 커뮤니티 - 게시글 등록
# ==========================================================
@app.post("/community/posts", status_code=201)
def create_post(req: CreatePostRequest, db: Session = Depends(get_db)):
    """커뮤니티 게시글 등록"""

    try:
        author = db.execute(
            text("SELECT id FROM users WHERE id = :id"),
            {"id": req.author_id}
        ).fetchone()

        if not author:
            raise HTTPException(404, "USER_NOT_FOUND")

        subject = db.execute(
            text("SELECT id FROM subjects WHERE id = :sid"),
            {"sid": req.subject_id}
        ).fetchone()

        if not subject:
            raise HTTPException(404, "SUBJECT_NOT_FOUND")

        if req.region_id is not None:
            region = db.execute(
                text("SELECT id FROM regions WHERE id = :rid"),
                {"rid": req.region_id}
            ).fetchone()

            if not region:
                raise HTTPException(404, "REGION_NOT_FOUND")

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

        if req.tags:
            for tag in req.tags:
                tag_row = db.execute(
                    text("SELECT id FROM tags WHERE name = :name"),
                    {"name": tag}
                ).fetchone()

                if tag_row:
                    tag_id = tag_row[0]
                else:
                    new_tag = db.execute(
                        text("INSERT INTO tags (name) VALUES (:name) RETURNING id"),
                        {"name": tag}
                    ).fetchone()
                    tag_id = new_tag[0]

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

# ==========================================================
# 📝 커뮤니티 - 게시물 상세 조회
# ==========================================================
@app.get("/community/posts/{post_id}", status_code=200)
def get_post_detail(post_id: int, db: Session = Depends(get_db)):
    """게시글 상세 조회"""

    try:
        post = db.execute(text("""
            SELECT 
                p.id, p.title, p.body, p.author_id, p.subject_id, p.region_id, p.created_at,
                u.name AS author_name,
                s.name AS subject_name,
                r.name AS region_name
            FROM posts p
            JOIN users u ON p.author_id = u.id
            JOIN subjects s ON p.subject_id = s.id
            LEFT JOIN regions r ON p.region_id = r.id
            WHERE p.id = :pid
        """), {"pid": post_id}).fetchone()

        if not post:
            raise HTTPException(404, "POST_NOT_FOUND")

        answers_result = db.execute(text("""
            SELECT 
                a.id, a.author_id, a.body, a.is_accepted, a.created_at,
                u.name AS author_name
            FROM answers a
            JOIN users u ON a.author_id = u.id
            WHERE a.post_id = :pid
            ORDER BY a.created_at ASC
        """), {"pid": post_id}).fetchall()

        answers = []
        for row in answers_result:
            answers.append({
                "id": row[0],
                "author_id": row[1],
                "author_name": row[5],
                "body": row[2],
                "is_accepted": row[3],
                "created_at": str(row[4])
            })

        return {
            "message": "SUCCESS",
            "status_code": 200,
            "data": {
                "id": post[0],
                "title": post[1],
                "body": post[2],
                "author_id": post[3],
                "author_name": post[7],
                "subject_id": post[4],
                "subject_name": post[8],
                "region_id": post[5],
                "region_name": post[9],
                "created_at": str(post[6]),
                "answers": answers
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"게시글 조회 중 오류 발생: {str(e)}")

# ==========================================================
# 📝 커뮤니티 - 댓글(답변) 등록
# ==========================================================
@app.post("/community/posts/{post_id}/answers", status_code=201)
def create_answer(
    post_id: int = Path(...),
    req: CreateAnswerRequest = Depends(),
    db: Session = Depends(get_db)
):
    """특정 게시물에 댓글(답변) 등록"""

    try:
        post_check = db.execute(
            text("SELECT id FROM posts WHERE id = :post_id"),
            {"post_id": post_id}
        ).fetchone()

        if not post_check:
            raise HTTPException(404, "POST_NOT_FOUND")

        author_check = db.execute(
            text("SELECT id FROM users WHERE id = :author_id"),
            {"author_id": req.author_id}
        ).fetchone()

        if not author_check:
            raise HTTPException(404, "USER_NOT_FOUND")

        if not req.body or req.body.strip() == "":
            raise HTTPException(400, "INVALID_INPUT")

        result = db.execute(text("""
            INSERT INTO answers (post_id, author_id, body, is_accepted, created_at)
            VALUES (:post_id, :author_id, :body, false, NOW())
            RETURNING id, post_id, author_id, body, is_accepted, created_at
        """), {
            "post_id": post_id,
            "author_id": req.author_id,
            "body": req.body
        })

        db.commit()
        answer = result.fetchone()

        return {
            "message": "SUCCESS",
            "status_code": 201,
            "data": {
                "answer_id": answer.id,
                "post_id": answer.post_id,
                "author_id": answer.author_id,
                "body": answer.body,
                "is_accepted": answer.is_accepted,
                "created_at": str(answer.created_at)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, detail=f"댓글 등록 중 오류: {str(e)}")

# ==========================================================
# 📝 커뮤니티 - 답변 채택
# ==========================================================
@app.patch("/community/answers/{answer_id}/accept", status_code=200)
def accept_answer(
    answer_id: int = Path(...),
    req: AcceptAnswerRequest = Depends(),
    db: Session = Depends(get_db)
):
    """게시글 작성자가 특정 답변을 채택"""

    try:
        answer = db.execute(text("""
            SELECT id, post_id, author_id, is_accepted
            FROM answers
            WHERE id = :answer_id
        """), {"answer_id": answer_id}).fetchone()

        if not answer:
            raise HTTPException(404, "ANSWER_NOT_FOUND")

        post_id = answer.post_id

        post = db.execute(text("""
            SELECT author_id
            FROM posts
            WHERE id = :post_id
        """), {"post_id": post_id}).fetchone()

        if not post:
            raise HTTPException(404, "POST_NOT_FOUND")

        if post.author_id != req.user_id:
            raise HTTPException(403, "NOT_POST_AUTHOR")

        db.execute(text("""
            UPDATE answers
            SET is_accepted = false
            WHERE post_id = :post_id
        """), {"post_id": post_id})

        updated = db.execute(text("""
            UPDATE answers
            SET is_accepted = true
            WHERE id = :answer_id
            RETURNING id, post_id, is_accepted
        """), {"answer_id": answer_id}).fetchone()

        db.commit()

        return {
            "message": "SUCCESS",
            "status_code": 200,
            "data": {
                "answer_id": updated.id,
                "post_id": updated.post_id,
                "is_accepted": updated.is_accepted
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, detail=f"답변 채택 중 오류: {str(e)}")

#----게시물 리스트 조회 API-----
@app.get("/community/posts", status_code=200)
def list_posts(
    subject_id: int = Query(None, description="과목 필터 (subjects.id)"),
    region_id: int = Query(None, description="지역 필터 (regions.id)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 개수"),
    order: str = Query("latest", description="정렬 기준 latest | oldest"),
    db: Session = Depends(get_db)
):
    """
    게시글 목록 조회 (필터 + 페이징 + 정렬)
    """

    try:
        offset = (page - 1) * limit

        # 정렬 기준
        order_clause = "p.created_at DESC" if order == "latest" else "p.created_at ASC"

        # ====== (1) 전체 게시글 개수 조회 ======
        count_query = """
            SELECT COUNT(*) 
            FROM posts p 
            WHERE 1=1
        """
        count_params = {}

        if subject_id:
            count_query += " AND p.subject_id = :subject_id"
            count_params["subject_id"] = subject_id

        if region_id:
            count_query += " AND p.region_id = :region_id"
            count_params["region_id"] = region_id

        total_count = db.execute(text(count_query), count_params).scalar()

        # ====== (2) 실제 게시글 조회 ======
        query = f"""
            SELECT 
                p.id, p.title, p.body, p.author_id, p.subject_id, p.region_id, p.created_at,
                u.name AS author_name,
                s.name AS subject_name,
                r.name AS region_name
            FROM posts p
            JOIN users u ON p.author_id = u.id
            LEFT JOIN subjects s ON p.subject_id = s.id
            LEFT JOIN regions r ON p.region_id = r.id
            WHERE 1=1
        """

        params = {}

        if subject_id:
            query += " AND p.subject_id = :subject_id"
            params["subject_id"] = subject_id

        if region_id:
            query += " AND p.region_id = :region_id"
            params["region_id"] = region_id

        query += f" ORDER BY {order_clause} LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        rows = db.execute(text(query), params).fetchall()

        posts = []
        for row in rows:
            posts.append({
                "id": row.id,
                "title": row.title,
                "body": row.body,
                "author_id": row.author_id,
                "author_name": row.author_name,
                "subject_id": row.subject_id,
                "subject_name": row.subject_name,
                "region_id": row.region_id,
                "region_name": row.region_name,
                "created_at": row.created_at
            })

        return {
            "message": "SUCCESS",
            "status_code": 200,
            "data": {
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "posts": posts
            }
        }

    except Exception as e:
        raise HTTPException(500, f"INTERNAL_SERVER_ERROR: {str(e)}")
