from sqlalchemy import Column, Integer, String, Boolean, Text, DECIMAL, ForeignKey, DateTime, Enum, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import enum
from app.database.database import Base

# Enum 타입 정의 (PostgreSQL ENUM 타입과 매칭)
class UserRole(enum.Enum):
    student = "student"
    tutor = "tutor" 
    admin = "admin"

class GenderType(enum.Enum):
    male = "male"
    female = "female"
    none = "none"

class SignupStatusType(enum.Enum):
    pending_profile = "pending_profile"
    active = "active"

class RequestStatus(enum.Enum):
    requested = "requested"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"

class SessionStatus(enum.Enum):
    requested = "requested"
    accepted = "accepted"
    done = "done"
    cancelled = "cancelled"

class RegionLevel(enum.Enum):
    시도 = "시도"
    시군구 = "시군구"
    동 = "동"

# 사용자 기본 정보
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    gender = Column(Enum(GenderType), default=GenderType.none)
    terms_agreed = Column(Boolean, default=False)
    privacy_policy_agreed = Column(Boolean, default=False)
    profile_image_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    signup_status = Column(Enum(SignupStatusType), default=SignupStatusType.pending_profile)

    # Relationships
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False)
    tutor_profile = relationship("TutorProfile", back_populates="user", uselist=False)

# 학생 프로필
class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    preferred_price_min = Column(Integer, default=18000)
    preferred_price_max = Column(Integer, default=50000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="student_profile")

# 튜터 프로필
class TutorProfile(Base):
    __tablename__ = "tutor_profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    hourly_rate_min = Column(Integer)
    hourly_rate_max = Column(Integer)
    experience_years = Column(Integer, default=0)
    education_level = Column(String(500))
    intro = Column(Text)
    rating_avg = Column(DECIMAL(3, 2), default=0.00)
    rating_count = Column(Integer, default=0)
    github_url = Column(String(500))
    portfolio_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="tutor_profile")
    resumes = relationship("TutorResume", back_populates="tutor")

# 과목
class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 실력 수준
class SkillLevel(Base):
    __tablename__ = "skill_levels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    rank = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 수업 방식
class LessonType(Base):
    __tablename__ = "lesson_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 과외 목적
class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 시간대
class TimeBand(Base):
    __tablename__ = "time_bands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 지역
class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("regions.id"))

    parent = relationship("Region", remote_side=[id])

# 학생-과목 관계
class StudentSubject(Base):
    __tablename__ = "student_subjects"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True)

    user = relationship("User")
    subject = relationship("Subject")

# 학생-수업형태 관계
class StudentLessonType(Base):
    __tablename__ = "student_lesson_types"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    lesson_type_id = Column(Integer, ForeignKey("lesson_types.id", ondelete="CASCADE"), primary_key=True)

    user = relationship("User")
    lesson_type = relationship("LessonType")

# 학생-목적 관계
class StudentGoal(Base):
    __tablename__ = "student_goals"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), primary_key=True)

    user = relationship("User")
    goal = relationship("Goal")

# 학생-실력수준 관계
class StudentSkillLevel(Base):
    __tablename__ = "student_skill_levels"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill_level_id = Column(Integer, ForeignKey("skill_levels.id", ondelete="CASCADE"), primary_key=True)

    user = relationship("User")
    skill_level = relationship("SkillLevel")

# 학생-지역 관계
class StudentRegion(Base):
    __tablename__ = "student_regions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"))

    user = relationship("User")
    region = relationship("Region")

# 학생-가능시간 관계
class StudentAvailability(Base):
    __tablename__ = "student_availabilities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    weekday = Column(Integer)  # 0=월 ~ 6=일
    time_band_id = Column(Integer, ForeignKey("time_bands.id", ondelete="CASCADE"))

    user = relationship("User")
    time_band = relationship("TimeBand")

# 튜터-과목 관계
class TutorSubject(Base):
    __tablename__ = "tutor_subjects"

    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True)
    skill_level_id = Column(Integer, ForeignKey("skill_levels.id", ondelete="CASCADE"), nullable=False)

    tutor = relationship("User")
    subject = relationship("Subject")
    skill_level = relationship("SkillLevel")

# 튜터-실력수준 관계
class TutorSkillLevel(Base):
    __tablename__ = "tutor_skill_levels"

    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill_level_id = Column(Integer, ForeignKey("skill_levels.id", ondelete="CASCADE"), primary_key=True)

    tutor = relationship("User")
    skill_level = relationship("SkillLevel")

# 튜터-수업형태 관계
class TutorLessonType(Base):
    __tablename__ = "tutor_lesson_types"

    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    lesson_type_id = Column(Integer, ForeignKey("lesson_types.id", ondelete="CASCADE"), primary_key=True)

    tutor = relationship("User")
    lesson_type = relationship("LessonType")

# 튜터-목적 관계
class TutorGoal(Base):
    __tablename__ = "tutor_goals"

    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), primary_key=True)

    tutor = relationship("User")
    goal = relationship("Goal")

# 튜터-지역 관계
class TutorRegion(Base):
    __tablename__ = "tutor_regions"

    id = Column(Integer, primary_key=True, index=True)
    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"))

    tutor = relationship("User")
    region = relationship("Region")

# 튜터-가능시간 관계
class TutorAvailability(Base):
    __tablename__ = "tutor_availabilities"

    id = Column(Integer, primary_key=True, index=True)
    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    weekday = Column(Integer)
    time_band_id = Column(Integer, ForeignKey("time_bands.id", ondelete="CASCADE"))

    tutor = relationship("User")
    time_band = relationship("TimeBand")

# 튜터 이력
class TutorResume(Base):
    __tablename__ = "tutor_resumes"

    id = Column(Integer, primary_key=True, index=True)
    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    career_title = Column(String(200), nullable=False)
    career_desc = Column(Text)
    certificate_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tutor = relationship("TutorProfile", back_populates="resumes")

# 과외 요청
class LessonRequest(Base):
    __tablename__ = "lesson_requests"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    message = Column(Text)
    status = Column(Enum(RequestStatus), default=RequestStatus.requested)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True))

    student = relationship("User", foreign_keys=[student_id])
    tutor = relationship("User", foreign_keys=[tutor_id])

# 세션
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    lesson_type_id = Column(Integer, ForeignKey("lesson_types.id"))
    region_id = Column(Integer, ForeignKey("regions.id"))
    scheduled_at = Column(DateTime(timezone=True))
    duration_min = Column(Integer, default=60)
    status = Column(Enum(SessionStatus), default=SessionStatus.requested)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("User", foreign_keys=[student_id])
    tutor = relationship("User", foreign_keys=[tutor_id])
    subject = relationship("Subject")
    lesson_type = relationship("LessonType")
    region = relationship("Region")

# 리뷰
class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    rating = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session")
    tutor = relationship("User", foreign_keys=[tutor_id])
    student = relationship("User", foreign_keys=[student_id])

# 메시지
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False)

    session = relationship("Session")
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

# 커뮤니티 게시글
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    region_id = Column(Integer, ForeignKey("regions.id"))
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    author = relationship("User")
    subject = relationship("Subject")
    region = relationship("Region")

# 커뮤니티 답변
class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"))
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    body = Column(Text, nullable=False)
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("Post")
    author = relationship("User")

# 태그
class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 게시글-태그 관계
class PostTag(Base):
    __tablename__ = "post_tags"

    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    post = relationship("Post")
    tag = relationship("Tag")

# 알림
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")

# 이벤트 로그
class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    tutor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    type = Column(String(50), nullable=False)
    context = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
    tutor = relationship("User", foreign_keys=[tutor_id])