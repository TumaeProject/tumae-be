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
# 🗃️ Fake DB (메모리 저장)
# ==========================================================
fake_users = {}
fake_tutor_details = {}
fake_student_details = {}

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

# ==========================================================
# 🚀 공통 회원가입 (User 생성)
# ==========================================================
@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(user: SignupRequest):
    """회원가입 - 기본 정보 등록"""
    
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
    """로그인 - JWT 토큰 발급"""
    
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
    """튜터 상세 정보 등록"""
    
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
    fake_tutor_details[req.user_id] = req.model_dump()

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
    """학생 상세 정보 등록"""
    
    target_user = None
    for u in fake_users.values():
        if u["user_id"] == req.user_id:
            target_user = u
            break

    if not target_user:
        raise HTTPException(404, "USER_NOT_FOUND")

    if target_user["role"] != "student":
        raise HTTPException(403, "FORBIDDEN_ROLE")

    fake_student_details[req.user_id] = req.model_dump()

    target_user["signup_status"] = "active"

    return {
        "message": "SUCCESS",
        "data": {
            "user_id": req.user_id,
            "signup_status": "active"
        }
    }

# ==========================================================
# 👨‍🎓 학생 찾기 APIs
# ==========================================================

@app.get("/api/students", response_model=List[StudentListResponse])
async def get_students(
    db: Session = Depends(get_db),
    subject: Optional[str] = Query(None, description="과목 필터 (예: 웹개발)"),
    region: Optional[str] = Query(None, description="지역 필터 (예: 서울특별시)"),
    price_min: Optional[int] = Query(None, description="최소 희망 시급"),
    price_max: Optional[int] = Query(None, description="최대 희망 시급"),
    skill_level: Optional[str] = Query(None, description="실력 수준 (예: 초급자)"),
    goal: Optional[str] = Query(None, description="학습 목적 (예: 취업 준비)"),
    lesson_type: Optional[str] = Query(None, description="수업 방식 (예: 1:1과외)"),
    limit: int = Query(20, description="결과 개수 제한"),
    offset: int = Query(0, description="결과 시작 위치")
):
    """학생 목록 검색 - 튜터가 과외 요청한 학생들의 선호 스타일과 비슷한 학생을 보여줌"""
    
    query = """
        SELECT DISTINCT
            u.id, u.name, u.email, u.created_at, u.signup_status,
            sp.preferred_price_min, sp.preferred_price_max
        FROM users u
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        WHERE u.role = 'student' AND u.signup_status = 'active'
    """
    
    params = {}
    
    if subject:
        query += " AND EXISTS (SELECT 1 FROM student_subjects ss JOIN subjects s ON ss.subject_id = s.id WHERE ss.user_id = u.id AND s.name = :subject)"
        params['subject'] = subject
    
    if region:
        query += " AND EXISTS (SELECT 1 FROM student_regions sr JOIN regions r ON sr.region_id = r.id WHERE sr.user_id = u.id AND (r.name = :region OR r.name LIKE :region_like))"
        params['region'] = region
        params['region_like'] = f"%{region}%"
    
    if price_min:
        query += " AND (sp.preferred_price_max IS NULL OR sp.preferred_price_max >= :price_min)"
        params['price_min'] = price_min
    
    if price_max:
        query += " AND (sp.preferred_price_min IS NULL OR sp.preferred_price_min <= :price_max)"
        params['price_max'] = price_max
    
    if skill_level:
        query += " AND EXISTS (SELECT 1 FROM student_skill_levels ssl JOIN skill_levels sl ON ssl.skill_level_id = sl.id WHERE ssl.user_id = u.id AND sl.name = :skill_level)"
        params['skill_level'] = skill_level
    
    if goal:
        query += " AND EXISTS (SELECT 1 FROM student_goals sg JOIN goals g ON sg.goal_id = g.id WHERE sg.user_id = u.id AND g.name = :goal)"
        params['goal'] = goal
    
    if lesson_type:
        query += " AND EXISTS (SELECT 1 FROM student_lesson_types slt JOIN lesson_types lt ON slt.lesson_type_id = lt.id WHERE slt.user_id = u.id AND lt.name = :lesson_type)"
        params['lesson_type'] = lesson_type
    
    query += " ORDER BY u.id LIMIT :limit OFFSET :offset"
    params['limit'] = limit
    params['offset'] = offset
    
    result = db.execute(text(query), params)
    students = result.fetchall()
    
    student_list = []
    for student in students:
        user_id = student[0]
        
        # 과목 조회
        subjects_result = db.execute(text("""
            SELECT s.name FROM student_subjects ss
            JOIN subjects s ON ss.subject_id = s.id
            WHERE ss.user_id = :user_id
        """), {'user_id': user_id})
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
        """), {'user_id': user_id})
        regions = [row[0] for row in regions_result.fetchall()]
        
        # 실력 수준 조회
        skill_result = db.execute(text("""
            SELECT sl.name FROM student_skill_levels ssl
            JOIN skill_levels sl ON ssl.skill_level_id = sl.id
            WHERE ssl.user_id = :user_id
            LIMIT 1
        """), {'user_id': user_id})
        skill_level = skill_result.scalar()
        
        # 학습 목적 조회
        goals_result = db.execute(text("""
            SELECT g.name FROM student_goals sg
            JOIN goals g ON sg.goal_id = g.id
            WHERE sg.user_id = :user_id
        """), {'user_id': user_id})
        goals = [row[0] for row in goals_result.fetchall()]
        
        # 수업 방식 조회
        lesson_types_result = db.execute(text("""
            SELECT lt.name FROM student_lesson_types slt
            JOIN lesson_types lt ON slt.lesson_type_id = lt.id
            WHERE slt.user_id = :user_id
        """), {'user_id': user_id})
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
            lesson_types=lesson_types
        ))
    
    return student_list

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

# ==========================================================
# 🍀 헬스체크
# ==========================================================
@app.get("/")
def root():
    return {
        "message": "SUCCESS", 
        "service": "Tumae API - 코딩 과외 매칭 플랫폼",
        "version": "3.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": {
                "signup": "/auth/signup",
                "login": "/auth/login",
                "tutor_onboarding": "/auth/tutors/details",
                "student_onboarding": "/auth/students/details"
            },
            "search": {
                "students": "/api/students",
                "tutors": "/api/tutors"
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    # 환경에 따른 설정
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    
    print("🚀 Tumae API 서버 시작!")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🔐 회원가입: POST /auth/signup")
    print("🔐 로그인: POST /auth/login")
    print("🔍 학생 검색: GET /api/students")
    print("🔍 튜터 검색: GET /api/tutors")
    
    # 프로덕션에서는 reload=False
    reload = os.getenv('ENVIRONMENT', 'development') == 'development'
    
    uvicorn.run(app, host=host, port=port, reload=reload)