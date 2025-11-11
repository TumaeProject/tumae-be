#!/usr/bin/env python3
"""
JSON 데이터를 PostgreSQL Capstone 데이터베이스에 삽입하는 스크립트
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

def insert_students_data(json_file_path):
    """학생 데이터를 데이터베이스에 삽입"""
    
    print(f"📖 학생 데이터 파일 로딩: {json_file_path}")
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        students_data = json.load(f)
    
    print(f"📊 총 {len(students_data)}명의 학생 데이터 발견")
    
    with SessionLocal() as db:
        try:
            # 기본 데이터 매핑 확인
            print("🔍 기본 데이터 확인 중...")
            
            # 과목 매핑
            subjects_result = db.execute(text("SELECT id, name FROM subjects"))
            subjects_map = {row[1]: row[0] for row in subjects_result.fetchall()}
            print(f"📚 과목: {list(subjects_map.keys())}")
            
            # 실력 수준 매핑
            skill_levels_result = db.execute(text("SELECT id, name FROM skill_levels"))
            skill_levels_map = {row[1]: row[0] for row in skill_levels_result.fetchall()}
            print(f"📈 실력 수준: {list(skill_levels_map.keys())}")
            
            # 목적 매핑
            goals_result = db.execute(text("SELECT id, name FROM goals"))
            goals_map = {row[1]: row[0] for row in goals_result.fetchall()}
            print(f"🎯 목적: {list(goals_map.keys())}")
            
            # 수업 방식 매핑  
            lesson_types_result = db.execute(text("SELECT id, name FROM lesson_types"))
            lesson_types_map = {row[1]: row[0] for row in lesson_types_result.fetchall()}
            print(f"🏫 수업 방식: {list(lesson_types_map.keys())}")
            
            print(f"\n📝 학생 데이터 삽입 시작...")
            success_count = 0
            
            for i, student in enumerate(students_data[:50]):  # 처음 50명만 테스트
                try:
                    # 1. 사용자 기본 정보 삽입
                    user_result = db.execute(text("""
                        INSERT INTO users (name, email, password_hash, role, gender, terms_agreed, privacy_policy_agreed, signup_status)
                        VALUES (:name, :email, :password_hash, 'student', 'none', true, true, 'active')
                        RETURNING id
                    """), {
                        'name': f'학생{student["id"]}',
                        'email': f'student{student["id"]}@example.com',
                        'password_hash': 'hashed_password_placeholder'
                    })
                    
                    user_id = user_result.scalar()
                    
                    # 2. 학생 프로필 삽입
                    preferred_price = student.get('price_per_hour', 25000)
                    db.execute(text("""
                        INSERT INTO student_profiles (user_id, preferred_price_min, preferred_price_max)
                        VALUES (:user_id, :price_min, :price_max)
                    """), {
                        'user_id': user_id,
                        'price_min': max(18000, preferred_price - 5000),  # 최소 18000
                        'price_max': min(50000, preferred_price + 5000)   # 최대 50000
                    })
                    
                    # 3. 학생 과목 관계 삽입
                    for subject_name in student.get('subject', []):
                        if subject_name in subjects_map:
                            db.execute(text("""
                                INSERT INTO student_subjects (user_id, subject_id)
                                VALUES (:user_id, :subject_id)
                                ON CONFLICT DO NOTHING
                            """), {
                                'user_id': user_id,
                                'subject_id': subjects_map[subject_name]
                            })
                    
                    # 4. 학생 실력 수준 삽입
                    student_level = student.get('student_level')
                    if student_level and student_level in skill_levels_map:
                        db.execute(text("""
                            INSERT INTO student_skill_levels (user_id, skill_level_id)
                            VALUES (:user_id, :skill_level_id)
                            ON CONFLICT DO NOTHING
                        """), {
                            'user_id': user_id,
                            'skill_level_id': skill_levels_map[student_level]
                        })
                    
                    # 5. 학생 목적 삽입
                    purpose = student.get('purpose')
                    if purpose and purpose in goals_map:
                        db.execute(text("""
                            INSERT INTO student_goals (user_id, goal_id)
                            VALUES (:user_id, :goal_id)
                            ON CONFLICT DO NOTHING
                        """), {
                            'user_id': user_id,
                            'goal_id': goals_map[purpose]
                        })
                    
                    # 6. 수업 방식 삽입
                    for lesson_type_name in student.get('lesson_type', []):
                        # JSON의 수업 방식을 DB 수업 방식으로 매핑
                        if lesson_type_name == '학원':
                            lesson_type_name = '그룹과외'
                        elif lesson_type_name == '기타':
                            lesson_type_name = '무관'
                            
                        if lesson_type_name in lesson_types_map:
                            db.execute(text("""
                                INSERT INTO student_lesson_types (user_id, lesson_type_id)
                                VALUES (:user_id, :lesson_type_id)
                                ON CONFLICT DO NOTHING
                            """), {
                                'user_id': user_id,
                                'lesson_type_id': lesson_types_map[lesson_type_name]
                            })
                    
                    success_count += 1
                    if success_count % 10 == 0:
                        print(f"   ✅ {success_count}명 완료...")
                        
                except Exception as e:
                    print(f"   ❌ 학생 {i+1} 삽입 실패: {str(e)}")
                    continue
            
            # 커밋
            db.commit()
            print(f"🎉 학생 데이터 삽입 완료! 성공: {success_count}명")
            
        except Exception as e:
            db.rollback()
            print(f"❌ 전체 작업 실패: {str(e)}")

def insert_teachers_data(json_file_path):
    """교사 데이터를 데이터베이스에 삽입"""
    
    print(f"\n📖 교사 데이터 파일 로딩: {json_file_path}")
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        teachers_data = json.load(f)
    
    print(f"📊 총 {len(teachers_data)}명의 교사 데이터 발견")
    
    with SessionLocal() as db:
        try:
            # 기본 데이터 매핑 확인
            subjects_result = db.execute(text("SELECT id, name FROM subjects"))
            subjects_map = {row[1]: row[0] for row in subjects_result.fetchall()}
            
            skill_levels_result = db.execute(text("SELECT id, name FROM skill_levels"))
            skill_levels_map = {row[1]: row[0] for row in skill_levels_result.fetchall()}
            
            lesson_types_result = db.execute(text("SELECT id, name FROM lesson_types"))
            lesson_types_map = {row[1]: row[0] for row in lesson_types_result.fetchall()}
            
            print(f"\n📝 교사 데이터 삽입 시작...")
            success_count = 0
            
            for i, teacher in enumerate(teachers_data[:30]):  # 처음 30명만 테스트
                try:
                    # 1. 사용자 기본 정보 삽입
                    user_result = db.execute(text("""
                        INSERT INTO users (name, email, password_hash, role, gender, terms_agreed, privacy_policy_agreed, signup_status)
                        VALUES (:name, :email, :password_hash, 'tutor', 'none', true, true, 'active')
                        RETURNING id
                    """), {
                        'name': teacher['name'],
                        'email': f'{teacher["name"]}@example.com',
                        'password_hash': 'hashed_password_placeholder'
                    })
                    
                    user_id = user_result.scalar()
                    
                    # 2. 튜터 프로필 삽입
                    hourly_rate = teacher.get('price_per_hour', 30000)
                    db.execute(text("""
                        INSERT INTO tutor_profiles (user_id, hourly_rate_min, hourly_rate_max, experience_years, rating_avg, rating_count)
                        VALUES (:user_id, :rate_min, :rate_max, :experience, :rating, :rating_count)
                    """), {
                        'user_id': user_id,
                        'rate_min': max(20000, hourly_rate - 5000),
                        'rate_max': hourly_rate + 10000,
                        'experience': random.randint(1, 10),  # 랜덤 경력
                        'rating': round(random.uniform(3.5, 5.0), 2),  # 랜덤 평점
                        'rating_count': random.randint(5, 50)  # 랜덤 리뷰 수
                    })
                    
                    # 3. 튜터 과목 관계 삽입
                    for subject_name in teacher.get('subject', []):
                        if subject_name in subjects_map:
                            # 튜터의 지도 실력 수준 (보통 실무활용가능)
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
                    
                    # 4. 튜터 수업 방식 삽입
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
                    
                    success_count += 1
                    if success_count % 5 == 0:
                        print(f"   ✅ {success_count}명 완료...")
                        
                except Exception as e:
                    print(f"   ❌ 교사 {i+1} 삽입 실패: {str(e)}")
                    continue
            
            # 커밋
            db.commit()
            print(f"🎉 교사 데이터 삽입 완료! 성공: {success_count}명")
            
        except Exception as e:
            db.rollback()
            print(f"❌ 전체 작업 실패: {str(e)}")

def main():
    """메인 실행 함수"""
    print("🚀 JSON 데이터를 Capstone PostgreSQL에 삽입 시작...")
    
    # 데이터베이스 연결 테스트
    try:
        with SessionLocal() as db:
            result = db.execute(text("SELECT 1"))
            print("✅ 데이터베이스 연결 성공")
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return
    
    # 학생 데이터 삽입
    student_file = "student_data_korea_500.json"
    if os.path.exists(student_file):
        insert_students_data(student_file)
    else:
        print(f"❌ {student_file} 파일을 찾을 수 없습니다.")
    
    # 교사 데이터 삽입  
    teacher_file = "teacher_data.json"
    if os.path.exists(teacher_file):
        insert_teachers_data(teacher_file)
    else:
        print(f"❌ {teacher_file} 파일을 찾을 수 없습니다.")
    
    print("\n🎯 데이터 삽입 작업 완료!")
    print("📊 결과 확인:")
    
    # 결과 확인
    with SessionLocal() as db:
        student_count = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'student'")).scalar()
        tutor_count = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'tutor'")).scalar()
        print(f"   👨‍🎓 학생: {student_count}명")
        print(f"   👨‍🏫 튜터: {tutor_count}명")

if __name__ == "__main__":
    main()