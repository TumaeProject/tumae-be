from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Tuple
from app.models.models import *

class StudentService:
    """학생 관련 서비스 로직"""
    
    @staticmethod
    def get_students(
        db: Session,
        page: int = 1,
        limit: int = 20,
        subject_id: Optional[int] = None,
        lesson_type_id: Optional[int] = None,
        region_id: Optional[int] = None,
        preferred_price_min: Optional[int] = None,
        preferred_price_max: Optional[int] = None,
        goal_id: Optional[int] = None,
        skill_level_id: Optional[int] = None,
        weekday: Optional[int] = None,
        time_band_id: Optional[int] = None,
        sort: str = "created_at"
    ) -> Tuple[List[User], int]:
        """학생 목록 검색"""
        
        query = db.query(User).filter(User.role == UserRole.student)
        
        # 필터링 조건 추가
        if subject_id:
            query = query.join(StudentSubject).filter(StudentSubject.subject_id == subject_id)
        
        if lesson_type_id:
            query = query.join(StudentLessonType).filter(StudentLessonType.lesson_type_id == lesson_type_id)
        
        if region_id:
            query = query.join(StudentRegion).filter(StudentRegion.region_id == region_id)
        
        if goal_id:
            query = query.join(StudentGoal).filter(StudentGoal.goal_id == goal_id)
        
        if skill_level_id:
            query = query.join(StudentSkillLevel).filter(StudentSkillLevel.skill_level_id == skill_level_id)
        
        if weekday is not None and time_band_id:
            query = query.join(StudentAvailability).filter(
                and_(
                    StudentAvailability.weekday == weekday,
                    StudentAvailability.time_band_id == time_band_id
                )
            )
        
        if preferred_price_min is not None or preferred_price_max is not None:
            query = query.join(StudentProfile)
            if preferred_price_min is not None:
                query = query.filter(StudentProfile.preferred_price_min >= preferred_price_min)
            if preferred_price_max is not None:
                query = query.filter(StudentProfile.preferred_price_max <= preferred_price_max)
        
        # 정렬
        if sort == "price_desc":
            query = query.join(StudentProfile).order_by(StudentProfile.preferred_price_max.desc())
        elif sort == "price_asc":
            query = query.join(StudentProfile).order_by(StudentProfile.preferred_price_min.asc())
        else:  # created_at
            query = query.order_by(User.created_at.desc())
        
        # 중복 제거
        query = query.distinct()
        
        # 총 개수 계산
        total_count = query.count()
        
        # 페이지네이션
        offset = (page - 1) * limit
        students = query.offset(offset).limit(limit).all()
        
        return students, total_count
    
    @staticmethod
    def get_student_detail(db: Session, user_id: int) -> Optional[User]:
        """학생 상세 정보 조회"""
        return db.query(User).filter(
            and_(User.id == user_id, User.role == UserRole.student)
        ).first()
    
    @staticmethod
    def get_student_subjects(db: Session, user_id: int) -> List[Subject]:
        """학생의 관심 과목 조회"""
        return db.query(Subject).join(StudentSubject).filter(
            StudentSubject.user_id == user_id
        ).all()
    
    @staticmethod
    def get_student_lesson_types(db: Session, user_id: int) -> List[LessonType]:
        """학생의 선호 수업 형태 조회"""
        return db.query(LessonType).join(StudentLessonType).filter(
            StudentLessonType.user_id == user_id
        ).all()
    
    @staticmethod
    def get_student_regions(db: Session, user_id: int) -> List[Region]:
        """학생의 선호 지역 조회"""
        return db.query(Region).join(StudentRegion).filter(
            StudentRegion.user_id == user_id
        ).all()
    
    @staticmethod
    def get_student_goals(db: Session, user_id: int) -> List[Goal]:
        """학생의 과외 목적 조회"""
        return db.query(Goal).join(StudentGoal).filter(
            StudentGoal.user_id == user_id
        ).all()
    
    @staticmethod
    def get_student_skill_levels(db: Session, user_id: int) -> List[SkillLevel]:
        """학생의 실력 수준 조회"""
        return db.query(SkillLevel).join(StudentSkillLevel).filter(
            StudentSkillLevel.user_id == user_id
        ).all()
    
    @staticmethod
    def get_student_availabilities(db: Session, user_id: int) -> List[StudentAvailability]:
        """학생의 가능 시간 조회"""
        return db.query(StudentAvailability).filter(
            StudentAvailability.user_id == user_id
        ).all()


class TutorService:
    """튜터 관련 서비스 로직"""
    
    @staticmethod
    def get_tutors(
        db: Session,
        page: int = 1,
        limit: int = 20,
        subject_id: Optional[int] = None,
        lesson_type_id: Optional[int] = None,
        region_id: Optional[int] = None,
        skill_level_id: Optional[int] = None,
        hourly_rate_min: Optional[int] = None,
        hourly_rate_max: Optional[int] = None,
        experience_years_min: Optional[int] = None,
        rating_avg_min: Optional[float] = None,
        goal_id: Optional[int] = None,
        weekday: Optional[int] = None,
        time_band_id: Optional[int] = None,
        sort: str = "rating"
    ) -> Tuple[List[User], int]:
        """튜터 목록 검색"""
        
        query = db.query(User).filter(User.role == UserRole.tutor)
        
        # 필터링 조건 추가
        if subject_id:
            query = query.join(TutorSubject).filter(TutorSubject.subject_id == subject_id)
        
        if lesson_type_id:
            query = query.join(TutorLessonType).filter(TutorLessonType.lesson_type_id == lesson_type_id)
        
        if region_id:
            query = query.join(TutorRegion).filter(TutorRegion.region_id == region_id)
        
        if skill_level_id:
            query = query.join(TutorSkillLevel).filter(TutorSkillLevel.skill_level_id == skill_level_id)
        
        if goal_id:
            query = query.join(TutorGoal).filter(TutorGoal.goal_id == goal_id)
        
        if weekday is not None and time_band_id:
            query = query.join(TutorAvailability).filter(
                and_(
                    TutorAvailability.weekday == weekday,
                    TutorAvailability.time_band_id == time_band_id
                )
            )
        
        # 튜터 프로필 조건
        tutor_profile_filters = []
        if hourly_rate_min is not None:
            tutor_profile_filters.append(TutorProfile.hourly_rate_min >= hourly_rate_min)
        if hourly_rate_max is not None:
            tutor_profile_filters.append(TutorProfile.hourly_rate_max <= hourly_rate_max)
        if experience_years_min is not None:
            tutor_profile_filters.append(TutorProfile.experience_years >= experience_years_min)
        if rating_avg_min is not None:
            tutor_profile_filters.append(TutorProfile.rating_avg >= rating_avg_min)
        
        if tutor_profile_filters:
            query = query.join(TutorProfile).filter(and_(*tutor_profile_filters))
        
        # 정렬
        if sort == "rating":
            query = query.join(TutorProfile).order_by(TutorProfile.rating_avg.desc())
        elif sort == "hourly_rate_asc":
            query = query.join(TutorProfile).order_by(TutorProfile.hourly_rate_min.asc())
        elif sort == "hourly_rate_desc":
            query = query.join(TutorProfile).order_by(TutorProfile.hourly_rate_max.desc())
        elif sort == "experience_desc":
            query = query.join(TutorProfile).order_by(TutorProfile.experience_years.desc())
        else:
            query = query.order_by(User.created_at.desc())
        
        # 중복 제거
        query = query.distinct()
        
        # 총 개수 계산
        total_count = query.count()
        
        # 페이지네이션
        offset = (page - 1) * limit
        tutors = query.offset(offset).limit(limit).all()
        
        return tutors, total_count
    
    @staticmethod
    def get_tutor_detail(db: Session, user_id: int) -> Optional[User]:
        """튜터 상세 정보 조회"""
        return db.query(User).filter(
            and_(User.id == user_id, User.role == UserRole.tutor)
        ).first()
    
    @staticmethod
    def get_tutor_subjects(db: Session, tutor_id: int) -> List[TutorSubject]:
        """튜터의 지도 가능 과목 조회"""
        return db.query(TutorSubject).filter(
            TutorSubject.tutor_id == tutor_id
        ).all()
    
    @staticmethod
    def get_tutor_lesson_types(db: Session, tutor_id: int) -> List[LessonType]:
        """튜터의 수업 형태 조회"""
        return db.query(LessonType).join(TutorLessonType).filter(
            TutorLessonType.tutor_id == tutor_id
        ).all()
    
    @staticmethod
    def get_tutor_regions(db: Session, tutor_id: int) -> List[Region]:
        """튜터의 활동 지역 조회"""
        return db.query(Region).join(TutorRegion).filter(
            TutorRegion.tutor_id == tutor_id
        ).all()
    
    @staticmethod
    def get_tutor_goals(db: Session, tutor_id: int) -> List[Goal]:
        """튜터의 지도 목적 조회"""
        return db.query(Goal).join(TutorGoal).filter(
            TutorGoal.tutor_id == tutor_id
        ).all()
    
    @staticmethod
    def get_tutor_skill_levels(db: Session, tutor_id: int) -> List[SkillLevel]:
        """튜터의 지도 가능 수준 조회"""
        return db.query(SkillLevel).join(TutorSkillLevel).filter(
            TutorSkillLevel.tutor_id == tutor_id
        ).all()
    
    @staticmethod
    def get_tutor_availabilities(db: Session, tutor_id: int) -> List[TutorAvailability]:
        """튜터의 가능 시간 조회"""
        return db.query(TutorAvailability).filter(
            TutorAvailability.tutor_id == tutor_id
        ).all()
    
    @staticmethod
    def get_tutor_resumes(db: Session, tutor_id: int) -> List[TutorResume]:
        """튜터의 이력 조회"""
        return db.query(TutorResume).filter(
            TutorResume.tutor_id == tutor_id
        ).order_by(TutorResume.created_at.desc()).all()
    
    @staticmethod
    def get_tutor_recent_reviews(db: Session, tutor_id: int, limit: int = 5) -> List[Review]:
        """튜터의 최근 리뷰 조회"""
        return db.query(Review).filter(
            Review.tutor_id == tutor_id
        ).order_by(Review.created_at.desc()).limit(limit).all()


def build_pagination_info(page: int, limit: int, total_count: int) -> dict:
    """페이지네이션 정보 생성"""
    total_pages = (total_count + limit - 1) // limit
    return {
        "current_page": page,
        "total_pages": total_pages,
        "total_count": total_count,
        "per_page": limit
    }