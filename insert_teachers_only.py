#!/usr/bin/env python3
"""
teacher_data.json 데이터만 PostgreSQL Capstone 데이터베이스에 삽입하는 스크립트
"""

import json
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import random

# 환경변수 로드
load_dotenv()

# 데이터베이스 연결
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL이 .env 파일에 설정되지 않았습니다.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def insert_teachers_only(json_file_path="teacher_data.json", limit=50):
    """교사 데이터만 데이터베이스에 삽입"""
    
    print(f"👨‍🏫 교사 데이터 전용 삽입 시작...")
    print(f"📖 파일: {json_file_path}")
    print(f"📊 삽입 제한: {limit}명")
    
    # 파일 존재 확인
    if not os.path.exists(json_file_path):
        print(f"❌ {json_file_path} 파일을 찾을 수 없습니다.")
        return
    
    # JSON 데이터 로드
    with open(json_file_path, 'r', encoding='utf-8') as f:
        teachers_data = json.load(f)
    
    print(f"📋 총 {len(teachers_data)}명의 교사 데이터 발견")
    
    with SessionLocal() as db:
        try:
            # 데이터베이스 연결 테스트
            db.execute(text("SELECT 1"))
            print("✅ 데이터베이스 연결 성공")
            
            # 기본 데이터 매핑 가져오기
            print("🔍 기본 데이터 매핑 중...")
            
            # 과목 매핑
            subjects_result = db.execute(text("SELECT id, name FROM subjects ORDER BY name"))
            subjects_map = {row[1]: row[0] for row in subjects_result.fetchall()}
            print(f"📚 사용 가능한 과목 ({len(subjects_map)}개): {list(subjects_map.keys())}")
            
            # 실력 수준 매핑
            skill_levels_result = db.execute(text("SELECT id, name, rank FROM skill_levels ORDER BY rank"))
            skill_levels_map = {row[1]: row[0] for row in skill_levels_result.fetchall()}
            print(f"📈 사용 가능한 실력 수준: {list(skill_levels_map.keys())}")
            
            # 수업 방식 매핑  
            lesson_types_result = db.execute(text("SELECT id, name FROM lesson_types ORDER BY name"))
            lesson_types_map = {row[1]: row[0] for row in lesson_types_result.fetchall()}
            print(f"🏫 사용 가능한 수업 방식: {list(lesson_types_map.keys())}")
            
            # 목적 매핑
            goals_result = db.execute(text("SELECT id, name FROM goals ORDER BY name"))
            goals_map = {row[1]: row[0] for row in goals_result.fetchall()}
            print(f"🎯 사용 가능한 목적: {list(goals_map.keys())}")
            
            print(f"\n📝 교사 데이터 삽입 시작... (최대 {limit}명)")
            success_count = 0
            error_count = 0
            
            for i, teacher in enumerate(teachers_data[:limit]):
                try:
                    print(f"\n👨‍🏫 교사 {i+1}: {teacher.get('name', 'Unknown')}")
                    
                    # 1. 사용자 기본 정보 삽입
                    teacher_name = teacher.get('name', f'튜터{i+1}')
                    teacher_email = f'{teacher_name.lower()}@example.com'
                    
                    user_result = db.execute(text("""
                        INSERT INTO users (name, email, password_hash, role, gender, terms_agreed, privacy_policy_agreed, signup_status)
                        VALUES (:name, :email, :password_hash, 'tutor', 'none', true, true, 'active')
                        RETURNING id
                    """), {
                        'name': teacher_name,
                        'email': teacher_email,
                        'password_hash': '$2b$12$hashedpasswordplaceholder'  # 실제 해시된 비밀번호 placeholder
                    })
                    
                    user_id = user_result.scalar()
                    print(f"   ✅ 사용자 생성됨 (ID: {user_id})")
                    
                    # 2. 튜터 프로필 삽입
                    hourly_rate = teacher.get('price_per_hour', 35000)
                    experience_years = random.randint(1, 8)  # 1-8년 경력
                    rating_avg = round(random.uniform(3.8, 5.0), 2)  # 3.8-5.0 평점
                    rating_count = random.randint(3, 40)  # 3-40개 리뷰
                    
                    db.execute(text("""
                        INSERT INTO tutor_profiles (
                            user_id, hourly_rate_min, hourly_rate_max, experience_years, 
                            rating_avg, rating_count, intro
                        )
                        VALUES (:user_id, :rate_min, :rate_max, :experience, :rating, :rating_count, :intro)
                    """), {
                        'user_id': user_id,
                        'rate_min': max(20000, hourly_rate - 8000),  # 시급 범위 설정
                        'rate_max': hourly_rate + 12000,
                        'experience': experience_years,
                        'rating': rating_avg,
                        'rating_count': rating_count,
                        'intro': f'{teacher_name} 튜터입니다. {experience_years}년 경력으로 열정적으로 지도하겠습니다!'
                    })
                    
                    print(f"   ✅ 튜터 프로필 생성됨 (시급: {hourly_rate:,}원, 경력: {experience_years}년, 평점: {rating_avg})")
                    
                    # 3. 튜터 과목 관계 삽입
                    subjects_added = 0
                    for subject_name in teacher.get('subject', []):
                        if subject_name in subjects_map:
                            # 튜터는 보통 실무 수준으로 가르칠 수 있다고 가정
                            skill_level_id = skill_levels_map.get('실무활용 가능', 4)
                            
                            db.execute(text("""
                                INSERT INTO tutor_subjects (tutor_id, subject_id, skill_level_id)
                                VALUES (:tutor_id, :subject_id, :skill_level_id)
                                ON CONFLICT DO NOTHING
                            """), {
                                'tutor_id': user_id,
                                'subject_id': subjects_map[subject_name],
                                'skill_level_id': skill_level_id
                            })
                            subjects_added += 1
                        else:
                            print(f"   ⚠️ 알 수 없는 과목: {subject_name}")
                    
                    print(f"   ✅ 지도 과목 {subjects_added}개 추가됨")
                    
                    # 4. 튜터 수업 방식 삽입
                    lesson_types_added = 0
                    for lesson_type_name in teacher.get('lesson_type', []):
                        if lesson_type_name in lesson_types_map:
                            db.execute(text("""
                                INSERT INTO tutor_lesson_types (tutor_id, lesson_type_id)
                                VALUES (:tutor_id, :lesson_type_id)
                                ON CONFLICT DO NOTHING
                            """), {
                                'tutor_id': user_id,
                                'lesson_type_id': lesson_types_map[lesson_type_name]
                            })
                            lesson_types_added += 1
                        else:
                            print(f"   ⚠️ 알 수 없는 수업 방식: {lesson_type_name}")
                    
                    print(f"   ✅ 수업 방식 {lesson_types_added}개 추가됨")
                    
                    # 5. 랜덤으로 지도 목적 추가 (선택적)
                    if random.choice([True, False]):  # 50% 확률로 목적 추가
                        random_goal = random.choice(list(goals_map.keys()))
                        db.execute(text("""
                            INSERT INTO tutor_goals (tutor_id, goal_id)
                            VALUES (:tutor_id, :goal_id)
                            ON CONFLICT DO NOTHING
                        """), {
                            'tutor_id': user_id,
                            'goal_id': goals_map[random_goal]
                        })
                        print(f"   ✅ 지도 목적 추가: {random_goal}")
                    
                    success_count += 1
                    print(f"   🎉 교사 {teacher_name} 삽입 완료! (총 {success_count}명)")
                        
                except Exception as e:
                    error_count += 1
                    print(f"   ❌ 교사 {i+1} 삽입 실패: {str(e)}")
                    continue
            
            # 커밋
            db.commit()
            print(f"\n🎉 교사 데이터 삽입 작업 완료!")
            print(f"✅ 성공: {success_count}명")
            print(f"❌ 실패: {error_count}명")
            
            # 최종 확인
            total_tutors = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'tutor'")).scalar()
            print(f"📊 전체 튜터 수: {total_tutors}명")
            
        except Exception as e:
            db.rollback()
            print(f"❌ 전체 작업 실패: {str(e)}")

def main():
    """메인 실행 함수"""
    print("🚀 교사 데이터 전용 삽입 스크립트 시작...")
    
    # 데이터베이스 연결 테스트
    try:
        with SessionLocal() as db:
            result = db.execute(text("SELECT current_database(), version()"))
            db_info = result.fetchone()
            print(f"✅ 데이터베이스: {db_info[0]}")
            print(f"📊 PostgreSQL: {db_info[1][:50]}...")
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return
    
    # 교사 데이터 삽입 (기본 50명)
    insert_teachers_only("teacher_data.json", limit=50)
    
    print("\n🔗 API로 확인해보세요:")
    print("   python simple_api_with_db.py")
    print("   http://localhost:8000/api/users")

if __name__ == "__main__":
    main()