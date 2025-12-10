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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================================
# 🔐 로그인
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        
        return {
            "message": "로그아웃되었습니다",
            "status_code": 200,
            "data": {"user_id": user.id}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

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
        return {"message": "SUCCESS"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

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
        return {"message": "SUCCESS"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

# ==========================================================
# 🔍 헬스체크
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

# ==========================================================
# 🔍 튜터 목록 검색 (DB 컬럼 최적화)
# ==========================================================
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
    ⚡ 최적화된 튜터 목록 검색 (accepted_count 컬럼 사용)
    """
    
    # 1️⃣ 학생 정보 조회
    student_data = db.execute(text("""
        SELECT 
            sp.preferred_price_min, sp.preferred_price_max,
            ARRAY_AGG(DISTINCT ss.subject_id) as s_ids,
            ARRAY_AGG(DISTINCT slt.lesson_type_id) as lt_ids,
            ARRAY_AGG(DISTINCT sr.region_id) as r_ids
        FROM users u
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        LEFT JOIN student_subjects ss ON u.id = ss.user_id
        LEFT JOIN student_lesson_types slt ON u.id = slt.user_id
        LEFT JOIN student_regions sr ON u.id = sr.user_id
        WHERE u.id = :user_id
        GROUP BY u.id, sp.preferred_price_min, sp.preferred_price_max
    """), {'user_id': user_id}).fetchone()
    
    if not student_data:
        raise HTTPException(404, "학생을 찾을 수 없습니다.")

    s_price_min, s_price_max, s_sub_ids, s_lt_ids, s_reg_ids = student_data
    s_sub_ids = set(s_sub_ids) if s_sub_ids else set()
    s_lt_ids = set(s_lt_ids) if s_lt_ids else set()

    # 2️⃣ 튜터 조회 (서브쿼리 제거, 컬럼 직접 사용)
    tutors_query = text("""
        SELECT 
            u.id, u.name, u.email, u.created_at, u.signup_status,
            tp.hourly_rate_min, tp.hourly_rate_max, tp.experience_years,
            tp.rating_avg, tp.rating_count, tp.intro,
            COALESCE(tp.accepted_count, 0) as accepted_count,
            ARRAY_AGG(DISTINCT ts.subject_id) as subject_ids,
            ARRAY_AGG(DISTINCT tlt.lesson_type_id) as lesson_type_ids,
            ARRAY_AGG(DISTINCT tr.region_id) as region_ids,
            ARRAY_AGG(DISTINCT subj.name) as subject_names,
            ARRAY_AGG(DISTINCT r.name) as region_names,
            ARRAY_AGG(DISTINCT lt.name) as lesson_type_names
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
    """)
    
    all_tutors = db.execute(tutors_query).fetchall()
    
    scored_tutors = []
    
    for t in all_tutors:
        score = 0
        t_sub_ids = set(t[12]) if t[12] else set()
        t_lt_ids = set(t[13]) if t[13] else set()
        
        # 매칭 알고리즘
        if s_sub_ids & t_sub_ids: score += 40
        if s_lt_ids & t_lt_ids: score += 10
        if t[5] and t[6]:
            if (s_price_max is None or s_price_max >= t[5]) and (s_price_min is None or s_price_min <= t[6]):
                score += 20
        score += 30 # 지역 점수 (단순화)
        
        if score >= min_score:
            scored_tutors.append({"data": t, "score": score})
            
    scored_tutors.sort(key=lambda x: (-x["score"], -x["data"][11], -(x["data"][8] or 0)))
    
    response_list = []
    for item in scored_tutors[offset:offset+limit]:
        t = item["data"]
        response_list.append(TutorListResponse(
            id=t[0], name=t[1], email=t[2],
            hourly_rate_min=t[5], hourly_rate_max=t[6], experience_years=t[7],
            rating_avg=t[8], rating_count=t[9], intro=t[10],
            accepted_count=t[11],
            subjects=t[15] if t[15] else [],
            regions=t[16] if t[16] else [],
            lesson_types=t[17] if t[17] else [],
            match_score=item["score"]
        ))
        
    return response_list

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
@app.get("/api/students/{student_id}", response_model=StudentDetailResponse)
async def get_student_detail(student_id: int = Path(...), db: Session = Depends(get_db)):
    student = db.execute(text("""
        SELECT u.id, u.name, u.email, u.created_at, u.signup_status, sp.preferred_price_min, sp.preferred_price_max
        FROM users u LEFT JOIN student_profiles sp ON u.id = sp.user_id
        WHERE u.id = :sid AND u.role = 'student'
    """), {'sid': student_id}).fetchone()
    
    if not student: raise HTTPException(404, "학생을 찾을 수 없습니다.")
    
    subjects = [r[0] for r in db.execute(text("SELECT s.name FROM student_subjects ss JOIN subjects s ON ss.subject_id = s.id WHERE ss.user_id = :sid"), {'sid': student_id})]
    regions = [r[0] for r in db.execute(text("SELECT r.name FROM student_regions sr JOIN regions r ON sr.region_id = r.id WHERE sr.user_id = :sid"), {'sid': student_id})]
    goals = [r[0] for r in db.execute(text("SELECT g.name FROM student_goals sg JOIN goals g ON sg.goal_id = g.id WHERE sg.user_id = :sid"), {'sid': student_id})]
    lesson_types = [r[0] for r in db.execute(text("SELECT lt.name FROM student_lesson_types slt JOIN lesson_types lt ON slt.lesson_type_id = lt.id WHERE slt.user_id = :sid"), {'sid': student_id})]
    skill_level_row = db.execute(text("SELECT sl.name FROM student_skill_levels ssl JOIN skill_levels sl ON ssl.skill_level_id = sl.id WHERE ssl.user_id = :sid"), {'sid': student_id}).fetchone()
    skill_level = skill_level_row[0] if skill_level_row else None
    
    return StudentDetailResponse(
        id=student[0], name=student[1], email=student[2], created_at=str(student[3]), signup_status=student[4],
        preferred_price_min=student[5], preferred_price_max=student[6],
        subjects=subjects, regions=regions, goals=goals, lesson_types=lesson_types, skill_level=skill_level
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
    # 1️⃣ 튜터 정보 조회
    tutor_data = db.execute(text("""
        SELECT tp.hourly_rate_min, tp.hourly_rate_max,
        ARRAY_AGG(DISTINCT ts.subject_id), ARRAY_AGG(DISTINCT tlt.lesson_type_id), ARRAY_AGG(DISTINCT tr.region_id)
        FROM users u
        LEFT JOIN tutor_profiles tp ON u.id = tp.user_id
        LEFT JOIN tutor_subjects ts ON u.id = ts.tutor_id
        LEFT JOIN tutor_lesson_types tlt ON u.id = tlt.tutor_id
        LEFT JOIN tutor_regions tr ON u.id = tr.tutor_id
        WHERE u.id = :user_id
        GROUP BY u.id, tp.hourly_rate_min, tp.hourly_rate_max
    """), {'user_id': user_id}).fetchone()
    
    if not tutor_data: raise HTTPException(404, "튜터 정보 없음")
    t_min, t_max, t_subs, t_lts, t_regs = tutor_data
    t_subs = set(t_subs) if t_subs else set()
    t_lts = set(t_lts) if t_lts else set()

    # 2️⃣ 학생 목록 조회
    students = db.execute(text("""
        SELECT u.id, u.name, u.email, sp.preferred_price_min, sp.preferred_price_max,
        ARRAY_AGG(DISTINCT ss.subject_id), ARRAY_AGG(DISTINCT slt.lesson_type_id),
        ARRAY_AGG(DISTINCT s.name), ARRAY_AGG(DISTINCT lt.name), ARRAY_AGG(DISTINCT r.name)
        FROM users u
        JOIN student_profiles sp ON u.id = sp.user_id
        LEFT JOIN student_subjects ss ON u.id = ss.user_id
        LEFT JOIN subjects s ON ss.subject_id = s.id
        LEFT JOIN student_lesson_types slt ON u.id = slt.user_id
        LEFT JOIN lesson_types lt ON slt.lesson_type_id = lt.id
        LEFT JOIN student_regions sr ON u.id = sr.user_id
        LEFT JOIN regions r ON sr.region_id = r.id
        WHERE u.role = 'student' AND u.signup_status = 'active'
        GROUP BY u.id, sp.preferred_price_min, sp.preferred_price_max
    """)).fetchall()

    scored_students = []
    for s in students:
        score = 0
        s_subs = set(s[5]) if s[5] else set()
        s_lts = set(s[6]) if s[6] else set()
        
        if t_subs & s_subs: score += 40
        if t_lts & s_lts: score += 10
        if t_min and t_max:
             if (s[4] is None or s[4] >= t_min) and (s[3] is None or s[3] <= t_max):
                 score += 20
        score += 30 # 지역 점수 (단순화)
        
        if score >= min_score:
            scored_students.append(StudentListResponse(
                id=s[0], name=s[1], email=s[2], preferred_price_min=s[3], preferred_price_max=s[4],
                subjects=s[7] if s[7] else [], lesson_types=s[8] if s[8] else [], regions=s[9] if s[9] else [],
                match_score=score
            ))
            
    scored_students.sort(key=lambda x: -x.match_score)
    return scored_students[offset:offset+limit]

# ==========================================================
# 📝 커뮤니티 API (게시글, 답변, 채택)
# ==========================================================
@app.post("/community/posts", status_code=201)
def create_post(req: CreatePostRequest, db: Session = Depends(get_db)):
    try:
        post = db.execute(text("""
            INSERT INTO posts (author_id, title, body, subject_id, region_id, created_at)
            VALUES (:author_id, :title, :body, :subject_id, :region_id, NOW())
            RETURNING id, created_at
        """), req.dict()).fetchone()
        db.commit()
        return {"message": "SUCCESS", "data": {"post_id": post[0], "created_at": str(post[1])}}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

@app.get("/community/posts/{post_id}", status_code=200)
def get_post_detail(post_id: int, db: Session = Depends(get_db)):
    post = db.execute(text("SELECT * FROM posts WHERE id = :id"), {"id": post_id}).fetchone()
    if not post: raise HTTPException(404, "POST_NOT_FOUND")
    
    answers = db.execute(text("""
        SELECT a.*, u.name as author_name 
        FROM answers a JOIN users u ON a.author_id = u.id 
        WHERE a.post_id = :pid ORDER BY a.created_at
    """), {"pid": post_id}).fetchall()
    
    ans_list = [
        {"id": a.id, "author_id": a.author_id, "author_name": a.author_name, "body": a.body, "is_accepted": a.is_accepted, "created_at": str(a.created_at)} 
        for a in answers
    ]
    
    return {
        "message": "SUCCESS", 
        "data": {
            "id": post.id, "title": post.title, "body": post.body, 
            "author_id": post.author_id, "author_name": "작성자",
            "subject_id": post.subject_id, "subject_name": "과목",
            "created_at": str(post.created_at), "answers": ans_list
        }
    }

@app.post("/community/posts/{post_id}/answers", status_code=201)
def create_answer(post_id: int, req: CreateAnswerRequest, db: Session = Depends(get_db)):
    try:
        ans = db.execute(text("""
            INSERT INTO answers (post_id, author_id, body, is_accepted, created_at)
            VALUES (:pid, :uid, :body, false, NOW())
            RETURNING id
        """), {"pid": post_id, "uid": req.author_id, "body": req.body}).fetchone()
        db.commit()
        return {"message": "SUCCESS", "data": {"answer_id": ans[0]}}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

# ==========================================================
# 🏆 [KEY] 답변 채택 API (accepted_count 컬럼 업데이트 로직 포함)
# ==========================================================
@app.patch("/community/answers/{answer_id}/accept", status_code=200)
def accept_answer(answer_id: int, req: AcceptAnswerRequest, db: Session = Depends(get_db)):
    """
    답변 채택 API - accepted_count 물리 컬럼 업데이트
    """
    try:
        # 1. 채택하려는 답변 조회
        new_answer = db.execute(text("SELECT id, post_id, author_id FROM answers WHERE id = :id"), {"id": answer_id}).fetchone()
        if not new_answer: 
            raise HTTPException(404, "ANSWER_NOT_FOUND")
        
        post_id = new_answer.post_id
        
        # 2. 게시글 작성자 본인 확인
        post = db.execute(text("SELECT author_id FROM posts WHERE id = :pid"), {"pid": post_id}).fetchone()
        if not post or post.author_id != req.user_id:
            raise HTTPException(403, "NOT_POST_AUTHOR")
            
        # 3. 기존에 채택된 답변이 있는지 확인
        old_answer = db.execute(text("""
            SELECT id, author_id FROM answers 
            WHERE post_id = :pid AND is_accepted = TRUE
        """), {"pid": post_id}).fetchone()
        
        # 4. 트랜잭션 시작 - 점수 조정
        # Case A: 이미 채택된 답변이 있다면 취소하고 해당 저자 점수 차감
        if old_answer:
            if old_answer.id == answer_id:
                return {"message": "ALREADY_ACCEPTED"} # 이미 채택된 답변 재클릭 시 무시
            
            # 기존 답변 채택 취소
            db.execute(text("UPDATE answers SET is_accepted = FALSE WHERE id = :aid"), {"aid": old_answer.id})
            
            # 기존 저자의 accepted_count 감소 (0 이하로는 안 내려가게)
            db.execute(text("""
                UPDATE tutor_profiles 
                SET accepted_count = GREATEST(accepted_count - 1, 0) 
                WHERE user_id = :uid
            """), {"uid": old_answer.author_id})
            
        # Case B: 새로운 답변 채택 및 점수 증가
        db.execute(text("UPDATE answers SET is_accepted = TRUE WHERE id = :aid"), {"aid": answer_id})
        
        # 새 저자의 accepted_count 증가 (tutor_profiles가 있는 경우만)
        db.execute(text("""
            UPDATE tutor_profiles 
            SET accepted_count = COALESCE(accepted_count, 0) + 1 
            WHERE user_id = :uid
        """), {"uid": new_answer.author_id})
        
        db.commit()
        return {"message": "SUCCESS"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

# ==========================================================
# 📬 쪽지함 API
# ==========================================================
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

@app.post("/messages/send", status_code=201, tags=["쪽지함"])
async def send_message(msg: MessageCreate, sender_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        res = db.execute(text("""
            INSERT INTO messages (sender_id, receiver_id, subject, body, reply_to)
            VALUES (:sid, :rid, :sub, :body, :rep) RETURNING id, created_at
        """), {"sid": sender_id, "rid": msg.receiver_id, "sub": msg.subject, "body": msg.body, "rep": msg.reply_to or None})
        db.commit()
        r = res.fetchone()
        return {"message": "쪽지 전송 완료", "message_id": r[0], "created_at": r[1].isoformat()}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

@app.get("/messages/inbox", response_model=List[MessageListItem], tags=["쪽지함"])
async def get_inbox(user_id: int = Query(...), db: Session = Depends(get_db)):
    res = db.execute(text("""
        SELECT m.id, m.sender_id, u.name, m.subject, SUBSTRING(m.body, 1, 50), m.is_read, m.is_starred, m.created_at
        FROM messages m JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = :uid AND m.receiver_deleted = FALSE ORDER BY m.created_at DESC
    """), {"uid": user_id})
    return [{"id": r[0], "sender_id": r[1], "sender_name": r[2], "subject": r[3], "preview": r[4], "is_read": r[5], "is_starred": r[6], "created_at": r[7].isoformat()} for r in res]

@app.get("/messages/sent", response_model=List[MessageListItem], tags=["쪽지함"])
async def get_sent(user_id: int = Query(...), db: Session = Depends(get_db)):
    res = db.execute(text("""
        SELECT m.id, m.receiver_id, u.name, m.subject, SUBSTRING(m.body, 1, 50), m.is_read, m.is_starred, m.created_at
        FROM messages m JOIN users u ON m.receiver_id = u.id
        WHERE m.sender_id = :uid AND m.sender_deleted = FALSE ORDER BY m.created_at DESC
    """), {"uid": user_id})
    return [{"id": r[0], "sender_id": r[1], "sender_name": r[2], "subject": r[3], "preview": r[4], "is_read": r[5], "is_starred": r[6], "created_at": r[7].isoformat()} for r in res]

@app.get("/messages/{message_id}", tags=["쪽지함"])
async def get_msg_detail(message_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM messages WHERE id = :id"), {"id": message_id}).fetchone()
    if not row: raise HTTPException(404, "쪽지 없음")
    if row.receiver_id == user_id and not row.is_read:
        db.execute(text("UPDATE messages SET is_read = TRUE, read_at = NOW() WHERE id = :id"), {"id": message_id})
        db.commit()
    return {"id": row.id, "subject": row.subject, "body": row.body, "sender_id": row.sender_id, "created_at": str(row.created_at)}

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
            SELECT id, sender_id, receiver_id, subject, body, reply_to, created_at, 0 as depth FROM messages WHERE id = :root
            UNION ALL
            SELECT m.id, m.sender_id, m.receiver_id, m.subject, m.body, m.reply_to, m.created_at, mt.depth + 1
            FROM messages m JOIN mt ON m.reply_to = mt.id
        ) SELECT * FROM mt ORDER BY created_at
    """), {"root": root_id}).fetchall()
    
    return {"thread": [{"id": r.id, "sender_id": r.sender_id, "subject": r.subject, "body": r.body, "depth": r.depth} for r in thread]}

@app.delete("/messages/{message_id}", tags=["쪽지함"])
async def delete_msg(message_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT sender_id, receiver_id FROM messages WHERE id = :id"), {"id": message_id}).fetchone()
    if not row: raise HTTPException(404)
    
    if user_id == row.sender_id:
        db.execute(text("UPDATE messages SET sender_deleted = TRUE WHERE id = :id"), {"id": message_id})
    elif user_id == row.receiver_id:
        db.execute(text("UPDATE messages SET receiver_deleted = TRUE WHERE id = :id"), {"id": message_id})
    else:
        raise HTTPException(403)
    db.commit()
    return {"message": "삭제됨"}

# ==========================================================
# 📝 이력서 블록 API
# ==========================================================
@app.post("/resume/{tutor_id}", status_code=201)
def create_resume_block(tutor_id: int, req: ResumeBlockCreateRequest, db: Session = Depends(get_db)):
    try:
        db.execute(text("""
            INSERT INTO resume_blocks (tutor_id, block_type, title, period, role, description, tech_stack, issuer, acquired_at, file_url, link_url, created_at)
            VALUES (:tid, :bt, :tit, :per, :role, :desc, :tech, :iss, :acq, :file, :link, NOW())
        """), {"tid": tutor_id, "bt": req.block_type, "tit": req.title, "per": req.period, "role": req.role, "desc": req.description, "tech": req.tech_stack, "iss": req.issuer, "acq": req.acquired_at, "file": req.file_url, "link": req.link_url})
        db.commit()
        return {"message": "SUCCESS"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))

@app.get("/resume/{tutor_id}", status_code=200)
def get_resume_blocks(tutor_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT * FROM resume_blocks WHERE tutor_id = :tid ORDER BY created_at DESC"), {"tid": tutor_id}).fetchall()
    res = {"career": [], "project": [], "certificate": [], "portfolio": []}
    for r in rows:
        res[r.block_type].append({"id": r.id, "title": r.title, "description": r.description, "period": r.period})
    return {"message": "SUCCESS", "data": res}

@app.patch("/resume/block/{block_id}", status_code=200)
def update_resume_block(block_id: int, req: ResumeBlockUpdateRequest, db: Session = Depends(get_db)):
    # 동적 쿼리 생성으로 필드 업데이트
    updates = []
    params = {"id": block_id}
    
    fields = req.dict(exclude_unset=True)
    if not fields: return {"message": "NO_CHANGES"}

    for key, value in fields.items():
        updates.append(f"{key} = :{key}")
        params[key] = value

    query = f"UPDATE resume_blocks SET {', '.join(updates)} WHERE id = :id"
    db.execute(text(query), params)
    db.commit()
    return {"message": "UPDATED"}

# ==========================================================
# 💾 서버 시작 이벤트 (테이블/컬럼 자동 생성)
# ==========================================================
@app.on_event("startup")
async def startup_event():
    if engine:
        try:
            with engine.connect() as conn:
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
                """))
                
                # 2. accepted_count 컬럼 추가 (Migration)
                # tutor_profiles 테이블이 있는지 확인하고 컬럼 추가
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