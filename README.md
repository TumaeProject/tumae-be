# Tumae API - 코딩 과외 매칭 플랫폼 백엔드

FastAPI 기반의 코딩 과외 매칭 플랫폼 백엔드 시스템입니다. 학생과 튜터를 연결하고, 커뮤니티, 쪽지함, 이력서 관리 등의 기능을 제공합니다.

---

## 🚀 두 가지 테스트 방법

### **Option 1: 배포된 서비스 (바로 테스트 가능) ⭐ 권장**

**설치 없이 브라우저에서 바로 테스트:**
- **API 문서**: https://tumae-jeonga.onrender.com/docs
- **실행 방법**: 위 링크 클릭 → Swagger UI에서 API 테스트
- **소요 시간**: 0분 (즉시)

### **Option 2: 로컬 환경 (코드 직접 실행)**

**GitHub 코드를 클론하여 로컬에서 실행:**
- **실행 방법**: [로컬 설치 및 실행 가이드](#-로컬-설치-및-실행-방법) 참조
- **소요 시간**: 약 10-15분

---

## 📋 목차
- [프로젝트 구조](#-프로젝트-구조)
- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
- [배포 환경 테스트](#-배포-환경에서-api-테스트)
- [로컬 설치 및 실행 방법](#-로컬-설치-및-실행-방법)
- [환경 변수 설정](#-환경-변수-설정)
- [API 문서](#-api-문서)
- [데이터베이스 구조](#-데이터베이스-구조)
- [문제 해결](#-문제-해결-troubleshooting)

---

## 📁 프로젝트 구조

```
tumae-backend/
├── __pycache__/          # Python 캐시 파일 (자동 생성)
├── app/                  # 애플리케이션 메인 디렉토리
├── venv/                 # Python 가상환경 (자동 생성, Git 제외)
├── .gitignore           # Git 제외 파일 목록
├── .env.example         # 환경 변수 예시 파일
├── main.py              # 🔥 FastAPI 메인 애플리케이션 파일 (2,088줄)
├── render.yaml          # Render 배포 설정 파일
├── requirements.txt     # Python 패키지 의존성 목록
├── runtime.txt          # Python 버전 명시 (3.12.7)
├── start.py             # 서버 시작 스크립트
├── student_data_korea_500.json  # 학생 테스트 데이터 (500개)
└── teacher_data.json    # 튜터 테스트 데이터
```

### 주요 파일 상세 설명

#### `main.py` ⭐ **핵심 파일**
- **크기**: 2,088줄
- **역할**: FastAPI 애플리케이션의 전체 로직
- **포함 내용**:
  ```python
  # 인증 시스템
  - JWT 토큰 발급 (Access Token + Refresh Token)
  - Bcrypt 비밀번호 암호화
  - 회원가입/로그인/로그아웃
  
  # 프로필 관리
  - 튜터 프로필 (자기소개, 과목, 시급, 경력 등)
  - 학생 프로필 (희망 과목, 희망 시급 등)
  
  # 커뮤니티 시스템
  - 게시글 CRUD
  - 답변 작성 및 채택
  - 채택 기반 튜터 랭킹
  - 과목/지역별 필터링
  
  # 쪽지함 시스템
  - 1:1 메시지 송수신
  - 읽음/별표 상태 관리
  - 답장 체인
  
  # 이력서 시스템
  - 4가지 블록 타입 (경력/프로젝트/자격증/포트폴리오)
  - 블록별 CRUD
  
  # 매칭 시스템
  - 과목, 지역, 시급 기반 매칭
  ```
- **API 엔드포인트**: 20개 이상
- **데이터베이스**: SQLAlchemy ORM 사용, Raw SQL 쿼리 실행

#### `requirements.txt`
프로젝트에 필요한 모든 Python 패키지와 버전:
```txt
fastapi==0.104.1          # 웹 프레임워크
uvicorn[standard]==0.24.0 # ASGI 서버
sqlalchemy==2.0.23        # ORM
psycopg2-binary==2.9.9    # PostgreSQL 드라이버
python-jose[cryptography]==3.3.0  # JWT 토큰
passlib[bcrypt]==1.7.4    # 비밀번호 암호화
python-dotenv==1.0.0      # 환경변수 관리
pydantic[email]==2.5.0    # 데이터 검증
python-multipart==0.0.6   # 파일 업로드
```

#### `runtime.txt`
```txt
python-3.12.7
```
- Python 버전을 명시적으로 고정
- Render 배포 시 이 버전을 사용

#### `start.py`
```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
```
- uvicorn 서버 시작 스크립트
- 포트 8000에서 main.py의 app 실행

#### `render.yaml`
```yaml
services:
  - type: web
    name: tumae-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python start.py
```
- Render.com 배포 설정
- 빌드 및 시작 명령어 정의

#### `.env.example` (Git에 포함)
```env
DATABASE_URL=postgresql://username:password@host:5432/database
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```
- 환경 변수 템플릿
- 실제 `.env` 파일은 Git에서 제외됨

#### `.gitignore`
```gitignore
.env
venv/
__pycache__/
*.pyc
*.log
.DS_Store
```
- Git에서 제외할 파일 목록
- 민감 정보와 자동 생성 파일 제외

#### `student_data_korea_500.json` & `teacher_data.json`
- 테스트용 더미 데이터
- 500명의 학생 데이터와 튜터 데이터
- 개발/테스트 환경에서 사용

---

## 🚀 주요 기능

### 1. 회원 인증 시스템
- **학생/튜터 역할 구분 회원가입**
  - 이메일 중복 검증
  - 역할별 프로필 초기화
- **JWT 기반 인증**
  - Access Token (30분)
  - Refresh Token (7일)
- **Bcrypt 비밀번호 암호화**
  - 단방향 해시 저장
  - 레인보우 테이블 공격 방어

### 2. 커뮤니티 시스템
- **질문 게시글 작성 및 답변**
  - 제목, 본문, 과목, 지역 태그
  - 다중 태그 지원
- **답변 채택 시스템**
  - 질문자가 답변 채택
  - 중복 채택 방지
- **채택 횟수 기반 튜터 랭킹**
  - `accepted_count` 컬럼으로 실시간 집계
  - 정렬 및 필터링 기능
- **과목/지역별 필터링**
  - Query Parameter 기반 필터
  - 동적 SQL 생성

### 3. 쪽지함 시스템
- **1:1 메시지 송수신**
  - sender_id, receiver_id로 관계 설정
- **읽음/안읽음 상태 관리**
  - `is_read` boolean 플래그
- **별표(중요) 표시**
  - `is_starred` boolean 플래그
- **답장 체인 연결**
  - `reply_to` Foreign Key로 체인 구성
- **양방향 삭제 처리**
  - `sender_deleted`, `receiver_deleted`
  - 양쪽 모두 삭제 시 DB에서 제거

### 4. 튜터 이력서 관리
- **4가지 블록 타입**
  - `career`: 경력 (회사명, 기간, 역할, 설명, 기술스택)
  - `project`: 프로젝트 (제목, 기간, 역할, 설명, 기술스택, URL)
  - `certificate`: 자격증 (이름, 발급기관, 취득일, 파일URL)
  - `portfolio`: 포트폴리오 (제목, 설명, 기술스택, 파일URL, URL)
- **블록별 맞춤 필드 검증**
  - `BLOCK_FIELDS` 딕셔너리로 타입별 필수 필드 관리
- **CRUD 기능**
  - 생성, 조회, 수정, 삭제 전체 지원
- **권한 기반 수정/삭제**
  - 본인 이력서만 수정 가능

### 5. 매칭 시스템
- **다중 조건 매칭**
  - 과목 (subject_id)
  - 지역 (region_id)
  - 시급 (hourly_rate)
  - 가능 시간대 (available_times)
- **매칭 점수 계산**
  - 조건별 가중치 부여
  - 정렬된 결과 반환

---

## 🛠 기술 스택

### Backend
- **FastAPI 0.104.1** - 고성능 비동기 웹 프레임워크
- **Python 3.12.7** - 최신 안정 버전

### Database
- **PostgreSQL 15+** - 관계형 데이터베이스
- **SQLAlchemy 2.0.23** - ORM 라이브러리
- **Raw SQL 쿼리** - 복잡한 조인 및 집계

### Authentication & Security
- **JWT (python-jose)** - 토큰 기반 인증
- **Bcrypt (passlib)** - 비밀번호 암호화
- **CORS Middleware** - 크로스 오리진 요청 처리

### Server & Deployment
- **Uvicorn** - ASGI 서버
- **Render.com** - 클라우드 배포 플랫폼
- **PostgreSQL (Managed)** - Render 관리형 DB

### Development Tools
- **Git & GitHub** - 버전 관리
- **VSCode** - 개발 환경
- **Swagger/OpenAPI** - API 문서 자동 생성

---

## 🌐 배포 환경에서 API 테스트

### **1단계: API 문서 접속**

브라우저에서 다음 URL 접속:
- **Swagger UI**: https://tumae-jeonga.onrender.com/docs
- **ReDoc**: https://tumae-jeonga.onrender.com/redoc
- 
### **2단계: API 테스트 실습**

#### **시나리오 1: 학생 회원가입 및 로그인**

1. **회원가입** - `POST /auth/signup` 클릭
   - "Try it out" 버튼 클릭
   - Request body:
   ```json
   {
     "name": "김학생",
     "email": "student1@test.com",
     "password": "password123",
     "role": "student",
     "gender": "male",
     "terms_agreed": true,
     "privacy_policy_agreed": true
   }
   ```
   - "Execute" 버튼 클릭
   - 응답 코드 `201` 확인

2. **로그인** - `POST /auth/login`
   ```json
   {
     "email": "student1@test.com",
     "password": "password123"
   }
   ```
   - 응답에서 `access_token` 복사

3. **인증 설정**
   - 상단 "Authorize" 버튼 클릭
   - Bearer Token에 access_token 붙여넣기
   - "Authorize" 클릭

4. **학생 프로필 등록** - `PATCH /auth/students/details`
   ```json
   {
     "subjects": [1, 2],
     "regions": [1],
     "desired_hourly_rate_min": 30000,
     "desired_hourly_rate_max": 50000
   }
   ```

#### **시나리오 2: 커뮤니티 - 질문 및 답변**

1. **게시글 작성** - `POST /community/posts`
   ```json
   {
     "title": "Python 기초 질문",
     "body": "리스트와 튜플의 차이가 뭔가요?",
     "subject_id": 1,
     "region_id": 1,
     "tags": ["python", "기초"]
   }
   ```

2. **게시글 목록** - `GET /community/posts`

3. **답변 작성** (튜터 계정으로 로그인 필요)
   - `POST /community/posts/{post_id}/answers`

4. **답변 채택** (질문 작성자가)
   - `POST /community/posts/{post_id}/accept/{answer_id}`

5. **튜터 랭킹 조회** - `GET /community/tutors/ranking`

#### **시나리오 3: 쪽지 기능**

1. **쪽지 보내기** - `POST /messages/send`
   ```json
   {
     "receiver_id": 2,
     "subject": "과외 문의",
     "body": "Python 과외 가능하신가요?",
     "reply_to": null
   }
   ```

2. **받은 쪽지함** - `GET /messages/inbox`

3. **쪽지 읽음 처리** - `PATCH /messages/{message_id}/read`

### **3단계: 전체 API 엔드포인트 확인**

Swagger UI에서 다음 그룹별로 확인:
- **auth** - 인증 관련 (6개)
- **matching** - 매칭 관련 (4개)
- **community** - 커뮤니티 (7개)
- **messages** - 쪽지함 (7개)
- **resume** - 이력서 (4개)

---


---

**프로젝트 상태**: ✅ 정상 운영 중 | 마지막 업데이트: 2025년 12월
