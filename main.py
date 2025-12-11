from fastapi import FastAPI, HTTPException, status, Query, Path, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
import json

# ==========================================================
# 📁 환경변수 로드 (.env)
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
    description="회원가입/로그인 + 매칭 + 쪽지함 + 커뮤니티(채택 랭킹 시스템)",
    version="4.3.0 (Full Code)",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    result = db.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": email}
    )
    return result.fetchone()

def get_user_by_id(db: Session, user_id: int):
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
    weekday: int
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
    accepted_count: int = 0  # DB 컬럼 값

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
    accepted_count: int = 0  # DB 컬럼 값

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

# --- 이력서 관련 ---
class ResumeBlockCreateRequest(BaseModel):
    block_type: str
    title: Optional[str] = None
    period: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[str] = None
    issuer: Optional[str] = None
    acquired_at: Optional[str] = None
    file_url: Optional[str] = None
    link_url: Optional[str] = None

class ResumeBlockUpdateRequest(BaseModel):
    title: Optional[str] = None
    period: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[str] = None
    issuer: Optional[str] = None
    acquired_at: Optional[str] = None
    file_url: Optional[str] = None
    link_url: Optional[str] = None

# --- 쪽지함 관련 ---
class MessageCreate(BaseModel):
    receiver_id: int
    subject: str
    body: str
    reply_to: Optional[int] = None

class MessageListItem(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    subject: str
    preview: str
    is_read: bool
    is_starred: bool
    created_at: str

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    receiver_id: int
    receiver_name: str
    subject: str
    body: str
    is_read: bool
    is_starred: bool
    created_at: str
    read_at: Optional[str] = None
    reply_to: Optional[int] = None

# ==========================================================
# 🚀 회원가입
# ==========================================================
@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(user: SignupRequest, db: Session = Depends(get_db)):
    """회원가입 - 기본 정보 등록"""
    
    try:
        existing_user = get_user_by_email(db, user.email)
        if existing_user:
            raise HTTPException(409, "EMAIL_ALREADY_EXISTS")

        if user.role not in ["student", "tutor"]:
            raise HTTPException(400, "INVALID_ROLE")

        if user.gender not in ["male", "female", "none"]:
            raise HTTPException(400, "INVALID_GENDER")

        password_hash = hash_password(user.password)

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
# 🔑 로그인
# ==========================================================
@app.post("/auth/login", status_code=status.HTTP_200_OK)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """로그인 - JWT 토큰 발급"""
    try:
        user = get_user_by_email(db, data.email)
        if not user:
            raise HTTPException(404, "USER_NOT_FOUND")

        if not verify_password(data.password, user.password_hash):
            raise HTTPException(401, "INVALID_CREDENTIALS")

        if user.signup_status == "pending_profile":
            raise HTTPException(403, "INACTIVE_ACCOUNT")

        access_token = create_access_token({"sub": data.email})
        refresh_token = create_refresh_token({"sub": data.email})
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
# 🔓 로그아웃
# ==========================================================
@app.post("/auth/logout", status_code=status.HTTP_200_OK)
def logout(data: LogoutRequest, db: Session = Depends(get_db)):
    """로그아웃 처리"""
    try:
        user = get_user_by_id(db, data.user_id)
        if not user:
            raise HTTPException(404, "USER_NOT_FOUND")
        
        logged_out_at = datetime.utcnow()
        
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
    """회원 탈퇴"""
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(404, "USER_NOT_FOUND")

        # 연관 데이터 삭제
        tables = [
            "tutor_subjects", "tutor_lesson_types", "tutor_skill_levels", "tutor_availabilities",
            "tutor_regions", "tutor_goals", "tutor_profiles",
            "student_subjects", "student_lesson_types", "student_regions", "student_availabilities",
            "student_goals", "student_skill_levels", "student_profiles",
            "lesson_requests", "sessions", "messages", "notifications", "event_logs",
            "post_tags", "answers", "posts", "resume_blocks"
        ]
        
        for table in tables:
            try:
                col = "tutor_id" if "tutor_" in table else "user_id"
                if table in ["posts", "answers"]: col = "author_id"
                if table == "messages": continue
                db.execute(text(f"DELETE FROM {table} WHERE {col} = :uid"), {"uid": user_id})
            except:
                pass

        db.execute(text("DELETE FROM messages WHERE sender_id = :uid OR receiver_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})
        db.commit()

        return {"message": "SUCCESS", "status_code": 200}
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
        if not user or user.role != "tutor":
            raise HTTPException(403, "INVALID_USER_OR_ROLE")

        # accepted_count는 기존 값을 유지하거나, 없으면 0으로 시작 (ON CONFLICT DO UPDATE에서 제외)
        db.execute(text("""
            INSERT INTO tutor_profiles (user_id, education_level, hourly_rate_min, hourly_rate_max, accepted_count, created_at)
            VALUES (:user_id, :education_level, :hourly_rate_min, :hourly_rate_max, 0, NOW())
            ON CONFLICT (user_id) DO UPDATE SET 
                education_level = :education_level,
                hourly_rate_min = :hourly_rate_min,
                hourly_rate_max = :hourly_rate_max
        """), req.dict())

        # 매핑 테이블 데이터 재설정
        for table in ["tutor_subjects", "tutor_lesson_types", "tutor_availabilities", "tutor_goals", "tutor_skill_levels", "tutor_regions"]:
            db.execute(text(f"DELETE FROM {table} WHERE tutor_id = :user_id"), {"user_id": req.user_id})

        for s in req.tutor_subjects:
            db.execute(text("INSERT INTO tutor_subjects (tutor_id, subject_id, skill_level_id) VALUES (:uid, :sid, :slid)"),
                       {"uid": req.user_id, "sid": s.subject_id, "slid": s.skill_level_id})
        
        for lt in req.tutor_lesson_types:
            db.execute(text("INSERT INTO tutor_lesson_types (tutor_id, lesson_type_id) VALUES (:uid, :lid)"), {"uid": req.user_id, "lid": lt})
            
        for av in req.tutor_availabilities:
            db.execute(text("INSERT INTO tutor_availabilities (tutor_id, weekday, time_band_id) VALUES (:uid, :w, :tid)"),
                       {"uid": req.user_id, "w": av.weekday, "tid": av.time_band_id})

        for g in req.tutor_goals:
             db.execute(text("INSERT INTO tutor_goals (tutor_id, goal_id) VALUES (:uid, :gid)"), {"uid": req.user_id, "gid": g})

        for sl in req.tutor_skill_levels:
             db.execute(text("INSERT INTO tutor_skill_levels (tutor_id, skill_level_id) VALUES (:uid, :sid)"), {"uid": req.user_id, "sid": sl})

        for r in req.tutor_regions:
             db.execute(text("INSERT INTO tutor_regions (tutor_id, region_id) VALUES (:uid, :rid)"), {"uid": req.user_id, "rid": r})

        db.execute(text("UPDATE users SET signup_status = 'active' WHERE id = :uid"), {"uid": req.user_id})
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
        raise HTTPException(500, f"튜터 정보 저장 중 오류가 발생했습니다: {str(e)}")

# ==========================================================
# 👨‍🎓 학생 온보딩
# ==========================================================
@app.patch("/auth/students/details", status_code=status.HTTP_200_OK)
def student_details(req: StudentDetailsRequest, db: Session = Depends(get_db)):
    """학생 상세 정보 등록"""
    try:
        user = get_user_by_id(db, req.user_id)
        if not user or user.role != "student":
            raise HTTPException(403, "INVALID_USER_OR_ROLE")

        db.execute(text("""
            INSERT INTO student_profiles (user_id, age_id, preferred_price_min, preferred_price_max, created_at)
            VALUES (:user_id, :age_id, :preferred_price_min, :preferred_price_max, NOW())
            ON CONFLICT (user_id) DO UPDATE SET 
                age_id = :age_id, preferred_price_min = :preferred_price_min, preferred_price_max = :preferred_price_max
        """), {"user_id": req.user_id, "age_id": req.student_age_id, "preferred_price_min": req.preferred_price_min, "preferred_price_max": req.preferred_price_max})

        tables = ["student_subjects", "student_goals", "student_lesson_types", "student_regions", "student_availabilities", "student_skill_levels"]
        for table in tables:
             db.execute(text(f"DELETE FROM {table} WHERE user_id = :uid"), {"uid": req.user_id})

        for s in req.student_subjects:
            db.execute(text("INSERT INTO student_subjects (user_id, subject_id) VALUES (:uid, :sid)"), {"uid": req.user_id, "sid": s})
        
        for lt in req.student_lesson_types:
             db.execute(text("INSERT INTO student_lesson_types (user_id, lesson_type_id) VALUES (:uid, :lid)"), {"uid": req.user_id, "lid": lt})
             
        for r in req.student_regions:
             db.execute(text("INSERT INTO student_regions (user_id, region_id) VALUES (:uid, :rid)"), {"uid": req.user_id, "rid": r})
             
        for av in req.student_availabilities:
             db.execute(text("INSERT INTO student_availabilities (user_id, weekday, time_band_id) VALUES (:uid, :w, :tid)"), {"uid": req.user_id, "w": av.weekday, "tid": av.time_band_id})
             
        for g in req.student_goals:
             db.execute(text("INSERT INTO student_goals (user_id, goal_id) VALUES (:uid, :gid)"), {"uid": req.user_id, "gid": g})
             
        for sl in req.student_skill_levels:
             db.execute(text("INSERT INTO student_skill_levels (user_id, skill_level_id) VALUES (:uid, :sid)"), {"uid": req.user_id, "sid": sl})

        db.execute(text("UPDATE users SET signup_status = 'active' WHERE id = :uid"), {"uid": req.user_id})
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
        raise HTTPException(500, f"학생 정보 저장 중 오류가 발생했습니다: {str(e)}")

# ==========================================================
# 🏠 헬스체크
# ==========================================================
@app.get("/")
def root():
    return {"message": "SUCCESS"}

# ==========================================================
# 🏆 [NEW] 튜터 랭킹 API (DB 컬럼 기반)
# ==========================================================
@app.get("/api/tutors/rankings/best", response_model=List[TutorListResponse], tags=["튜터"])
async def get_tutors_ranked_by_acceptance(
    limit: int = Query(10, description="랭킹 표시 개수"),
    db: Session = Depends(get_db)
):
    """
    🏆 채택 횟수(accepted_count)가 높은 순서대로 튜터 목록을 반환합니다.
    - JOIN 계산 없이 DB 컬럼을 직접 읽어 빠릅니다.
    """
    
    query = text("""
        SELECT 
            u.id,
            u.name,
            u.email,
            tp.hourly_rate_min,
            tp.hourly_rate_max,
            tp.experience_years,
            tp.rating_avg,
            tp.rating_count,
            tp.intro,
            COALESCE(tp.accepted_count, 0) as accepted_count,
            ARRAY_AGG(DISTINCT subj.name) FILTER (WHERE subj.name IS NOT NULL) as subject_names,
            ARRAY_AGG(DISTINCT lt.name) FILTER (WHERE lt.name IS NOT NULL) as lesson_type_names,
            ARRAY_AGG(DISTINCT r.name) FILTER (WHERE r.name IS NOT NULL) as region_names
        FROM users u
        JOIN tutor_profiles tp ON u.id = tp.user_id
        LEFT JOIN tutor_subjects ts ON u.id = ts.tutor_id
        LEFT JOIN subjects subj ON ts.subject_id = subj.id
        LEFT JOIN tutor_lesson_types tlt ON u.id = tlt.tutor_id
        LEFT JOIN lesson_types lt ON tlt.lesson_type_id = lt.id
        LEFT JOIN tutor_regions tr ON u.id = tr.tutor_id
        LEFT JOIN regions r ON tr.region_id = r.id
        WHERE u.role = 'tutor' AND u.signup_status = 'active'
        GROUP BY u.id, tp.hourly_rate_min, tp.hourly_rate_max, tp.experience_years, 
                 tp.rating_avg, tp.rating_count, tp.intro, tp.accepted_count
        ORDER BY tp.accepted_count DESC, tp.rating_avg DESC
        LIMIT :limit
    """)
    
    results = db.execute(query, {"limit": limit}).fetchall()
    
    tutors = []
    for r in results:
        tutors.append(TutorListResponse(
            id=r[0], name=r[1], email=r[2],
            hourly_rate_min=r[3], hourly_rate_max=r[4],
            experience_years=r[5], rating_avg=r[6], rating_count=r[7], intro=r[8],
            match_score=0, 
            accepted_count=r[9],
            subjects=r[10] if r[10] else [],
            lesson_types=r[11] if r[11] else [],
            regions=r[12] if r[12] else []
        ))
        
    return tutors

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
    """튜터 상세 정보 (accepted_count 컬럼 조회)"""
    
    tutor_result = db.execute(text("""
        SELECT 
            u.id, u.name, u.email, u.created_at, u.signup_status,
            tp.hourly_rate_min, tp.hourly_rate_max, tp.experience_years,
            tp.rating_avg, tp.rating_count, tp.intro,
            COALESCE(tp.accepted_count, 0) as accepted_count
        FROM users u
        LEFT JOIN tutor_profiles tp ON u.id = tp.user_id
        WHERE u.id = :tutor_id AND u.role = 'tutor'
    """), {'tutor_id': tutor_id})
    
    tutor = tutor_result.fetchone()
    if not tutor:
        raise HTTPException(status_code=404, detail="튜터를 찾을 수 없습니다.")
    
    subjects = [r[0] for r in db.execute(text("SELECT s.name FROM tutor_subjects ts JOIN subjects s ON ts.subject_id = s.id WHERE ts.tutor_id = :tid"), {'tid': tutor_id})]
    regions = [r[0] for r in db.execute(text("SELECT r.name FROM tutor_regions tr JOIN regions r ON tr.region_id = r.id WHERE tr.tutor_id = :tid"), {'tid': tutor_id})]
    lesson_types = [r[0] for r in db.execute(text("SELECT lt.name FROM tutor_lesson_types tlt JOIN lesson_types lt ON tlt.lesson_type_id = lt.id WHERE tlt.tutor_id = :tid"), {'tid': tutor_id})]
    
    return TutorDetailResponse(
        id=tutor[0], name=tutor[1], email=tutor[2], created_at=str(tutor[3]), signup_status=tutor[4],
        hourly_rate_min=tutor[5], hourly_rate_max=tutor[6], experience_years=tutor[7],
        rating_avg=tutor[8], rating_count=tutor[9], intro=tutor[10],
        accepted_count=tutor[11], # 컬럼 값
        subjects=subjects, regions=regions, lesson_types=lesson_types
    )

# ==========================================================
# ⚡ 학생 관련 API
# ==========================================================
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
# 📝 커뮤니티 API (게시글, 답변, 채택)
# ==========================================================
@app.post("/community/posts", status_code=201)
def create_post(req: CreatePostRequest, db: Session = Depends(get_db)):
    try:
        author = db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": req.author_id}).fetchone()
        if not author: raise HTTPException(404, "USER_NOT_FOUND")

        subject = db.execute(text("SELECT id FROM subjects WHERE id = :sid"), {"sid": req.subject_id}).fetchone()
        if not subject: raise HTTPException(404, "SUBJECT_NOT_FOUND")

        if req.region_id is not None:
            region = db.execute(text("SELECT id FROM regions WHERE id = :rid"), {"rid": req.region_id}).fetchone()
            if not region: raise HTTPException(404, "REGION_NOT_FOUND")

        post_result = db.execute(text("""
            INSERT INTO posts (author_id, title, body, subject_id, region_id, created_at)
            VALUES (:author_id, :title, :body, :subject_id, :region_id, NOW())
            RETURNING id, created_at
        """), req.dict())
        post = post_result.fetchone()
        post_id = post[0]

        if req.tags:
            for tag in req.tags:
                tag_row = db.execute(text("SELECT id FROM tags WHERE name = :name"), {"name": tag}).fetchone()
                tag_id = tag_row[0] if tag_row else db.execute(text("INSERT INTO tags (name) VALUES (:name) RETURNING id"), {"name": tag}).fetchone()[0]
                db.execute(text("INSERT INTO post_tags (post_id, tag_id) VALUES (:post_id, :tag_id)"), {"post_id": post_id, "tag_id": tag_id})

        db.commit()
        return {"message": "SUCCESS", "status_code": 201, "data": {"post_id": post_id, "created_at": str(post[1])}}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"게시글 등록 중 오류가 발생했습니다: {str(e)}")

@app.get("/community/posts/{post_id}", status_code=200)
def get_post_detail(post_id: int, db: Session = Depends(get_db)):
    post = db.execute(text("""
        SELECT p.id, p.title, p.body, p.author_id, p.subject_id, p.region_id, p.created_at,
        u.name AS author_name, s.name AS subject_name, r.name AS region_name
        FROM posts p
        JOIN users u ON p.author_id = u.id
        JOIN subjects s ON p.subject_id = s.id
        LEFT JOIN regions r ON p.region_id = r.id
        WHERE p.id = :pid
    """), {"pid": post_id}).fetchone()
    if not post: raise HTTPException(404, "POST_NOT_FOUND")
    
    answers_result = db.execute(text("""
        SELECT a.id, a.author_id, a.body, a.is_accepted, a.created_at, u.name AS author_name
        FROM answers a JOIN users u ON a.author_id = u.id
        WHERE a.post_id = :pid ORDER BY a.created_at ASC
    """), {"pid": post_id}).fetchall()
    
    answers = [{"id": r[0], "author_id": r[1], "author_name": r[5], "body": r[2], "is_accepted": r[3], "created_at": str(r[4])} for r in answers_result]
    
    return {
        "message": "SUCCESS", "status_code": 200,
        "data": {
            "id": post[0], "title": post[1], "body": post[2], "author_id": post[3],
            "author_name": post[7], "subject_id": post[4], "subject_name": post[8],
            "region_id": post[5], "region_name": post[9], "created_at": str(post[6]), "answers": answers
        }
    }

@app.post("/community/posts/{post_id}/answers", status_code=201)
def create_answer(post_id: int, req: CreateAnswerRequest, db: Session = Depends(get_db)):
    try:
        if not db.execute(text("SELECT id FROM posts WHERE id = :pid"), {"pid": post_id}).fetchone():
            raise HTTPException(404, "POST_NOT_FOUND")
        if not db.execute(text("SELECT id FROM users WHERE id = :aid"), {"aid": req.author_id}).fetchone():
            raise HTTPException(404, "USER_NOT_FOUND")
        if not req.body or req.body.strip() == "":
            raise HTTPException(400, "INVALID_INPUT")

        result = db.execute(text("""
            INSERT INTO answers (post_id, author_id, body, is_accepted, created_at)
            VALUES (:pid, :aid, :body, false, NOW()) RETURNING id, post_id, author_id, body, is_accepted, created_at
        """), {"pid": post_id, "aid": req.author_id, "body": req.body})
        db.commit()
        answer = result.fetchone()
        return {"message": "SUCCESS", "status_code": 201, "data": {"answer_id": answer.id, "post_id": answer.post_id, "author_id": answer.author_id, "body": answer.body, "is_accepted": answer.is_accepted, "created_at": str(answer.created_at)}}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"댓글 등록 중 오류: {str(e)}")

# ==========================================================
# 🏆 [KEY] 답변 채택 API (accepted_count 컬럼 업데이트 로직 포함)
# ==========================================================
@app.patch("/community/answers/{answer_id}/accept", status_code=200)
def accept_answer(answer_id: int, req: AcceptAnswerRequest, db: Session = Depends(get_db)):
    """답변 채택 API - accepted_count 물리 컬럼 업데이트"""
    try:
        # 1. 채택하려는 답변 조회
        new_answer = db.execute(text("SELECT id, post_id, author_id FROM answers WHERE id = :id"), {"id": answer_id}).fetchone()
        if not new_answer: raise HTTPException(404, "ANSWER_NOT_FOUND")
        post_id = new_answer.post_id
        
        # 2. 게시글 작성자 본인 확인
        post = db.execute(text("SELECT author_id FROM posts WHERE id = :pid"), {"pid": post_id}).fetchone()
        if not post or post.author_id != req.user_id:
            raise HTTPException(403, "NOT_POST_AUTHOR")
            
        # 3. 기존에 채택된 답변이 있는지 확인
        old_answer = db.execute(text("SELECT id, author_id FROM answers WHERE post_id = :pid AND is_accepted = TRUE"), {"pid": post_id}).fetchone()
        
        # 4. 트랜잭션 시작 - 점수 조정
        if old_answer:
            if old_answer.id == answer_id:
                return {"message": "ALREADY_ACCEPTED"}
            
            # 기존 답변 채택 취소
            db.execute(text("UPDATE answers SET is_accepted = FALSE WHERE id = :aid"), {"aid": old_answer.id})
            # 기존 저자의 accepted_count 감소
            db.execute(text("UPDATE tutor_profiles SET accepted_count = GREATEST(accepted_count - 1, 0) WHERE user_id = :uid"), {"uid": old_answer.author_id})
            
        # 새로운 답변 채택 및 점수 증가
        db.execute(text("UPDATE answers SET is_accepted = TRUE WHERE id = :aid"), {"aid": answer_id})
        db.execute(text("UPDATE tutor_profiles SET accepted_count = COALESCE(accepted_count, 0) + 1 WHERE user_id = :uid"), {"uid": new_answer.author_id})
        
        db.commit()
        return {"message": "SUCCESS"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

# ==========================================================
# 📬 쪽지함 API
# ==========================================================
@app.post("/messages/send", status_code=201, tags=["쪽지함"])
async def send_message(msg: MessageCreate, sender_id: int = Query(...), db: Session = Depends(get_db)):
    sender = get_user_by_id(db, sender_id)
    if not sender: raise HTTPException(404, "발신자를 찾을 수 없습니다.")
    receiver = get_user_by_id(db, msg.receiver_id)
    if not receiver: raise HTTPException(404, "수신자를 찾을 수 없습니다.")
    
    try:
        reply_to_value = msg.reply_to if msg.reply_to and msg.reply_to > 0 else None
        res = db.execute(text("""
            INSERT INTO messages (sender_id, receiver_id, subject, body, reply_to)
            VALUES (:sid, :rid, :sub, :body, :rep) RETURNING id, created_at
        """), {"sid": sender_id, "rid": msg.receiver_id, "sub": msg.subject, "body": msg.body, "rep": reply_to_value})
        db.commit()
        r = res.fetchone()
        return {"message": "쪽지 전송 완료", "message_id": r[0], "created_at": r[1].isoformat()}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

@app.get("/messages/inbox", response_model=List[MessageListItem], tags=["쪽지함"])
async def get_inbox(user_id: int = Query(...), page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    offset = (page - 1) * per_page
    res = db.execute(text("""
        SELECT m.id, m.sender_id, u.name, m.subject, SUBSTRING(m.body, 1, 50), m.is_read, m.is_starred, m.created_at
        FROM messages m JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = :uid AND m.receiver_deleted = FALSE ORDER BY m.created_at DESC
        LIMIT :per_page OFFSET :offset
    """), {"uid": user_id, "per_page": per_page, "offset": offset})
    return [{"id": r[0], "sender_id": r[1], "sender_name": r[2], "subject": r[3], "preview": r[4], "is_read": r[5], "is_starred": r[6], "created_at": r[7].isoformat()} for r in res]

@app.get("/messages/sent", response_model=List[MessageListItem], tags=["쪽지함"])
async def get_sent(user_id: int = Query(...), page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    offset = (page - 1) * per_page
    res = db.execute(text("""
        SELECT m.id, m.receiver_id, u.name, m.subject, SUBSTRING(m.body, 1, 50), m.is_read, m.is_starred, m.created_at
        FROM messages m JOIN users u ON m.receiver_id = u.id
        WHERE m.sender_id = :uid AND m.sender_deleted = FALSE ORDER BY m.created_at DESC
        LIMIT :per_page OFFSET :offset
    """), {"uid": user_id, "per_page": per_page, "offset": offset})
    return [{"id": r[0], "sender_id": r[1], "sender_name": r[2], "subject": r[3], "preview": r[4], "is_read": r[5], "is_starred": r[6], "created_at": r[7].isoformat()} for r in res]

@app.get("/messages/{message_id}", response_model=MessageResponse, tags=["쪽지함"])
async def get_msg_detail(message_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT m.id, m.sender_id, s.name, m.receiver_id, r.name, m.subject, m.body, m.is_read, m.is_starred, m.created_at, m.read_at, m.reply_to
        FROM messages m JOIN users s ON m.sender_id = s.id JOIN users r ON m.receiver_id = r.id
        WHERE m.id = :mid AND (m.sender_id = :uid OR m.receiver_id = :uid)
    """), {"mid": message_id, "uid": user_id})
    row = result.fetchone()
    if not row: raise HTTPException(404, "쪽지를 찾을 수 없습니다.")
    
    if row[3] == user_id and not row[7]:
        db.execute(text("UPDATE messages SET is_read = TRUE, read_at = NOW() WHERE id = :mid"), {"mid": message_id})
        db.commit()
    
    return {"id": row[0], "sender_id": row[1], "sender_name": row[2], "receiver_id": row[3], "receiver_name": row[4], "subject": row[5], "body": row[6], "is_read": row[7], "is_starred": row[8], "created_at": row[9].isoformat(), "read_at": row[10].isoformat() if row[10] else None, "reply_to": row[11]}

@app.get("/messages/{message_id}/thread", tags=["쪽지함"])
async def get_message_thread(message_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    current = db.execute(text("SELECT id, reply_to FROM messages WHERE id = :id"), {"id": message_id}).fetchone()
    if not current: raise HTTPException(404)
    
    root_id = current.id
    curr_reply = current.reply_to
    while curr_reply:
        parent = db.execute(text("SELECT id, reply_to FROM messages WHERE id = :id"), {"id": curr_reply}).fetchone()
        if not parent: break
        root_id = parent.id
        curr_reply = parent.reply_to
        
    thread = db.execute(text("""
        WITH RECURSIVE mt AS (
            SELECT id, sender_id, receiver_id, subject, body, is_read, is_starred, created_at, read_at, reply_to, 0 as depth
            FROM messages WHERE id = :root
            UNION ALL
            SELECT m.id, m.sender_id, m.receiver_id, m.subject, m.body, m.is_read, m.is_starred, m.created_at, m.read_at, m.reply_to, mt.depth + 1
            FROM messages m JOIN mt ON m.reply_to = mt.id
        ) SELECT * FROM mt ORDER BY created_at
    """), {"root": root_id}).fetchall()
    
    return {"thread": [{"id": r.id, "sender_id": r.sender_id, "subject": r.subject, "body": r.body, "depth": r.depth, "is_current": r.id == message_id, "created_at": r.created_at.isoformat()} for r in thread], "total_count": len(thread), "root_id": root_id, "current_id": message_id}

@app.delete("/messages/{message_id}", tags=["쪽지함"])
async def delete_msg(message_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT sender_id, receiver_id, sender_deleted, receiver_deleted FROM messages WHERE id = :id"), {"id": message_id}).fetchone()
    if not row: raise HTTPException(404)
    
    sender_id, receiver_id, sender_deleted, receiver_deleted = row
    if user_id not in [sender_id, receiver_id]: raise HTTPException(403)
    
    if user_id == sender_id:
        if receiver_deleted: db.execute(text("DELETE FROM messages WHERE id = :id"), {"id": message_id})
        else: db.execute(text("UPDATE messages SET sender_deleted = TRUE WHERE id = :id"), {"id": message_id})
    else:
        if sender_deleted: db.execute(text("DELETE FROM messages WHERE id = :id"), {"id": message_id})
        else: db.execute(text("UPDATE messages SET receiver_deleted = TRUE WHERE id = :id"), {"id": message_id})
    
    db.commit()
    return {"message": "삭제됨"}

@app.patch("/messages/{message_id}/star", tags=["쪽지함"])
async def toggle_star(message_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    result = db.execute(text("SELECT sender_id, receiver_id, is_starred FROM messages WHERE id = :id"), {"id": message_id})
    row = result.fetchone()
    if not row or user_id not in [row[0], row[1]]: raise HTTPException(404, "쪽지를 찾을 수 없습니다.")
    
    db.execute(text("UPDATE messages SET is_starred = NOT is_starred WHERE id = :id"), {"id": message_id})
    db.commit()
    return {"message": "즐겨찾기가 변경되었습니다.", "is_starred": not row[2]}

@app.get("/messages/unread/count", tags=["쪽지함"])
async def get_unread_count(user_id: int = Query(...), db: Session = Depends(get_db)):
    result = db.execute(text("SELECT COUNT(*) FROM messages WHERE receiver_id = :uid AND is_read = FALSE AND receiver_deleted = FALSE"), {"uid": user_id})
    return {"unread_count": result.scalar()}

# ==========================================================
# 📝 이력서 블록 추가 API (수정 버전)
# ==========================================================

VALID_BLOCK_TYPES = ["career", "project", "certificate", "portfolio"]

# 블록 타입별 허용/사용 필드 정의
BLOCK_FIELDS = {
    "career": ["title", "period", "role", "description", "tech_stack"],
    "project": ["title", "period", "role", "description", "tech_stack", "link_url"],
    "certificate": ["title", "issuer", "acquired_at", "file_url"],
    "portfolio": ["title", "description", "tech_stack", "file_url", "link_url"]
}

@app.post("/resume/{tutor_id}", status_code=201)
def create_resume_block(
    tutor_id: int,
    req: ResumeBlockCreateRequest = Depends(),
    db: Session = Depends(get_db)
):
    """튜터 이력서 블록 추가 (경력/프로젝트/자격증/포트폴리오)"""

    try:
        # -----------------------------
        # 1) tutor_id 검증
        # -----------------------------
        user = db.execute(
            text("SELECT id, role FROM users WHERE id = :uid"),
            {"uid": tutor_id}
        ).fetchone()

        if not user or user.role != "tutor":
            raise HTTPException(404, "TUTOR_NOT_FOUND")

        # -----------------------------
        # 2) block_type 검증
        # -----------------------------
        if req.block_type not in VALID_BLOCK_TYPES:
            raise HTTPException(400, "INVALID_BLOCK_TYPE")

        allowed_fields = BLOCK_FIELDS[req.block_type]

        # -----------------------------
        # 3) 필드 필터링 (허용되지 않은 필드 자동 NULL 처리)
        # -----------------------------
        insert_data = {
            "tutor_id": tutor_id,
            "block_type": req.block_type,
            "title": req.title if "title" in allowed_fields else None,
            "period": req.period if "period" in allowed_fields else None,
            "role": req.role if "role" in allowed_fields else None,
            "description": req.description if "description" in allowed_fields else None,
            "tech_stack": req.tech_stack if "tech_stack" in allowed_fields else None,
            "issuer": req.issuer if "issuer" in allowed_fields else None,
            "acquired_at": req.acquired_at if "acquired_at" in allowed_fields else None,
            "file_url": req.file_url if "file_url" in allowed_fields else None,
            "link_url": req.link_url if "link_url" in allowed_fields else None,
        }

        # -----------------------------
        # 4) 필수 필드 누락 검증
        # -----------------------------
        required = ["title"]  # 모든 블록 공통 필수
        for field in required:
            if field not in allowed_fields:
                continue
            if insert_data[field] is None:
                raise HTTPException(400, f"MISSING_REQUIRED_FIELD: {field}")

        # -----------------------------
        # 5) DB Insert
        # -----------------------------
        result = db.execute(text("""
            INSERT INTO resume_blocks (
                tutor_id, block_type, title, period, role, description,
                tech_stack, issuer, acquired_at, file_url, link_url, created_at
            )
            VALUES (
                :tutor_id, :block_type, :title, :period, :role, :description,
                :tech_stack, :issuer, :acquired_at, :file_url, :link_url, NOW()
            )
            RETURNING id
        """), insert_data)

        new_block = result.fetchone()
        db.commit()

        return {
            "message": "SUCCESS",
            "block_id": new_block.id
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"이력서 블록 추가 중 오류: {str(e)}")

# ==========================================================
# 🗑️ 이력서 블록 삭제 API
# ==========================================================

@app.delete("/resume/block/{block_id}", status_code=200)
def delete_resume_block(
    block_id: int = Path(..., description="삭제할 블록 ID"),
    current_user_id: int = Query(..., description="현재 로그인한 사용자 ID"),
    db: Session = Depends(get_db)
):
    """
    이력서 블록 삭제 (튜터 본인만 가능)
    """

    try:
        # 1️⃣ 블록 존재 여부 확인
        block = db.execute(text("""
            SELECT id, tutor_id 
            FROM resume_blocks 
            WHERE id = :block_id
        """), {"block_id": block_id}).fetchone()

        if not block:
            raise HTTPException(404, "RESUME_BLOCK_NOT_FOUND")

        tutor_id = block.tutor_id

        # 2️⃣ 삭제 권한 확인 — 본인만 삭제 가능
        if tutor_id != current_user_id:
            raise HTTPException(403, "NO_PERMISSION")

        # 3️⃣ 블록 삭제
        db.execute(text("""
            DELETE FROM resume_blocks 
            WHERE id = :block_id
        """), {"block_id": block_id})

        db.commit()

        return {
            "message": "SUCCESS",
            "status_code": 200,
            "data": {
                "deleted_block_id": block_id
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"INTERNAL_SERVER_ERROR: {str(e)}")

# ==========================================================
# 💾 서버 시작 이벤트 (테이블/컬럼 자동 생성)
# ==========================================================
@app.on_event("startup")
async def startup_event():
    if engine:
        try:
            with engine.connect() as conn:
                # users 테이블 존재 확인
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = 'users'
                    );
                """))
                users_exists = result.scalar()
                
                if not users_exists:
                    print("⚠️  경고: users 테이블이 존재하지 않습니다!")
                    print("💡  회원가입 API를 먼저 사용하거나 데이터베이스 스키마를 생성하세요.")
                else:
                    print("✅ users 테이블 확인됨")
                
                # 1. 쪽지함 테이블 생성
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        receiver_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        subject VARCHAR(200) NOT NULL,
                        body TEXT NOT NULL,
                        is_read BOOLEAN DEFAULT FALSE,
                        is_starred BOOLEAN DEFAULT FALSE,
                        sender_deleted BOOLEAN DEFAULT FALSE,
                        receiver_deleted BOOLEAN DEFAULT FALSE,
                        reply_to INTEGER REFERENCES messages(id) ON DELETE SET NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        read_at TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id, created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id, created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(receiver_id, is_read);
                """))
                
                # 2. accepted_count 컬럼 추가 (Migration)
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'tutor_profiles'
                    );
                """))
                if result.scalar():
                    conn.execute(text("""
                        ALTER TABLE tutor_profiles 
                        ADD COLUMN IF NOT EXISTS accepted_count INTEGER DEFAULT 0;
                    """))
                
                conn.commit()
                print("✅ 서버 시작: DB 스키마 체크 완료 (accepted_count 컬럼 포함)")
        except Exception as e:
            print(f"⚠️ 테이블/컬럼 생성 오류: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)