#!/usr/bin/env python3
"""
학생+교사 JSON 데이터를 PostgreSQL에 삽입하는 통합 스크립트 (중복 방지)
"""

import json
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import random

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL이 .env 파일에 설정되지 않았습니다.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def parse_region(region_str):
    """지역 문자열 파싱"""
    parts = region_str.strip().split()
    if len(parts) >= 2:
        return parts[0], parts[1]  # 시도, 시군구
    elif len(parts) == 1:
        return parts[0], None
    return None, None

def get_or_create_region(db, region_name, level, parent_id=None):
    """지역이 없으면 생성하고 ID 반환"""
    result = db.execute(text("""
        SELECT id FROM regions 
        WHERE name = :name AND level = :level 
        AND (parent_id = :parent_id OR (parent_id IS NULL AND :parent_id IS NULL))
    """), {'name': region_name, 'level': level, 'parent_id': parent_id})
    
    region = result.fetchone()
    if region:
        return region[0]
    
    result = db.execute(text("""
        INSERT INTO regions (name, level, parent_id)
        VALUES (:name, :level, :parent_id)
        RETURNING id
    """), {'name': region_name, 'level': level, 'parent_id': parent_id})
    
    return result.scalar()

def check_duplicate_user(db, name, email, role):
    """중복 사용자 체크"""
    result = db.execute(text("""
        SELECT id FROM users 
        WHERE (name = :name AND role = :role) OR email = :email
    """), {'name': name, 'email': email, 'role': role})
    
    return result.fetchone()

def insert_students_with_regions(json_file_path="student_data_korea_500.json", limit=50, start_idx=0):
    """학생 데이터를 지역 포함해서 삽입"""
    
    print(f"\n👨‍🎓 학생 데이터 삽입 시작...")
    print(f"📖 파일: {json_file_path}")
    print(f"📊 시작 인덱스: {start_idx}, 삽입할 개수: {limit}")
    
    if not os.path.exists(json_file_path):
        print(f"❌ {json_file_path} 파일을 찾을 수 없습니다.")
        return 0
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        students_data = json.load(f)
    
    print(f"📋 총 {len(students_data)}명의 학생 데이터 발견")
    
    with SessionLocal() as db:
        # 기본 데이터 매핑
        subjects_result = db.execute(text("SELECT id, name FROM subjects"))
        subjects_map = {row[1]: row[0] for row in subjects_result.fetchall()}
        
        skill_levels_result = db.execute(text("SELECT id, name FROM skill_levels"))
        skill_levels_map = {row[1]: row[0] for row in skill_levels_result.fetchall()}
        
        goals_result = db.execute(text("SELECT id, name FROM goals"))
        goals_map = {row[1]: row[0] for row in goals_result.fetchall()}
        
        lesson_types_result = db.execute(text("SELECT id, name FROM lesson_types"))
        lesson_types_map = {row[1]: row[0] for row in lesson_types_result.fetchall()}
        
        print("🔍 기본 데이터 매핑 완료")
        
        success_count = 0
        duplicate_count = 0
        error_count = 0
        
        for i, student in enumerate(students_data[start_idx:start_idx+limit]):
            try:
                student_name = f'학생{student["id"]}'
                student_email = f'student{student["id"]}@example.com'
                
                # 🛡️ 중복 체크
                existing_user = check_duplicate_user(db, student_name, student_email, 'student')
                if existing_user:
                    duplicate_count += 1
                    print(f"   ⚠️ 중복: {student_name} (건너뜀)")
                    continue
                
                print(f"\n👨‍🎓 학생 {start_idx + i + 1}: {student_name}")
                
                # 1. 사용자 생성
                user_result = db.execute(text("""
                    INSERT INTO users (name, email, password_hash, role, gender, terms_agreed, privacy_policy_agreed, signup_status)
                    VALUES (:name, :email, :password_hash, 'student', 'none', true, true, 'active')
                    RETURNING id
                """), {
                    'name': student_name,
                    'email': student_email,
                    'password_hash': '$2b$12$placeholder'
                })
                
                user_id = user_result.scalar()
                
                # 2. 학생 프로필 생성
                preferred_price = student.get('price_per_hour', 25000)
                db.execute(text("""
                    INSERT INTO student_profiles (user_id, preferred_price_min, preferred_price_max)
                    VALUES (:user_id, :price_min, :price_max)
                """), {
                    'user_id': user_id,
                    'price_min': max(18000, preferred_price - 5000),
                    'price_max': min(50000, preferred_price + 5000)
                })
                
                # 3. 과목 관계
                for subject_name in student.get('subject', []):
                    if subject_name in subjects_map:
                        db.execute(text("""
                            INSERT INTO student_subjects (user_id, subject_id)
                            VALUES (:user_id, :subject_id) ON CONFLICT DO NOTHING
                        """), {'user_id': user_id, 'subject_id': subjects_map[subject_name]})
                
                # 4. 실력 수준
                student_level = student.get('student_level')
                if student_level and student_level in skill_levels_map:
                    db.execute(text("""
                        INSERT INTO student_skill_levels (user_id, skill_level_id)
                        VALUES (:user_id, :skill_level_id) ON CONFLICT DO NOTHING
                    """), {'user_id': user_id, 'skill_level_id': skill_levels_map[student_level]})
                
                # 5. 목적
                purpose = student.get('purpose')
                if purpose and purpose in goals_map:
                    db.execute(text("""
                        INSERT INTO student_goals (user_id, goal_id)
                        VALUES (:user_id, :goal_id) ON CONFLICT DO NOTHING
                    """), {'user_id': user_id, 'goal_id': goals_map[purpose]})
                
                # 6. 수업 방식 (매핑 적용)
                for lesson_type_name in student.get('lesson_type', []):
                    mapped_type = lesson_type_name
                    if lesson_type_name == '학원':
                        mapped_type = '그룹과외'
                    elif lesson_type_name == '기타':
                        mapped_type = '무관'
                    
                    if mapped_type in lesson_types_map:
                        db.execute(text("""
                            INSERT INTO student_lesson_types (user_id, lesson_type_id)
                            VALUES (:user_id, :lesson_type_id) ON CONFLICT DO NOTHING
                        """), {'user_id': user_id, 'lesson_type_id': lesson_types_map[mapped_type]})
                
                # 7. 🗺️ 지역 처리
                regions_added = 0
                for region_str in student.get('region', []):
                    sido, sigungu = parse_region(region_str)
                    
                    if sido:
                        sido_id = get_or_create_region(db, sido, '시도', None)
                        db.execute(text("""
                            INSERT INTO student_regions (user_id, region_id)
                            VALUES (:user_id, :region_id)
                        """), {'user_id': user_id, 'region_id': sido_id})
                        regions_added += 1
                        
                        if sigungu:
                            sigungu_id = get_or_create_region(db, sigungu, '시군구', sido_id)
                            db.execute(text("""
                                INSERT INTO student_regions (user_id, region_id)
                                VALUES (:user_id, :region_id)
                            """), {'user_id': user_id, 'region_id': sigungu_id})
                            regions_added += 1
                
                print(f"   ✅ 선호 지역 {regions_added}개, 희망시급 {preferred_price:,}원")
                success_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"   ❌ 학생 {start_idx + i + 1} 실패: {str(e)}")
                continue
        
        db.commit()
        print(f"\n📊 학생 삽입 결과: ✅성공 {success_count}명, ⚠️중복 {duplicate_count}명, ❌실패 {error_count}명")
        return success_count

def insert_teachers_with_regions(json_file_path="teacher_data.json", limit=30, start_idx=0):
    """교사 데이터를 지역 포함해서 삽입"""
    
    print(f"\n👨‍🏫 교사 데이터 삽입 시작...")
    print(f"📖 파일: {json_file_path}")
    print(f"📊 시작 인덱스: {start_idx}, 삽입할 개수: {limit}")
    
    if not os.path.exists(json_file_path):
        print(f"❌ {json_file_path} 파일을 찾을 수 없습니다.")
        return 0
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        teachers_data = json.load(f)
    
    print(f"📋 총 {len(teachers_data)}명의 교사 데이터 발견")
    
    with SessionLocal() as db:
        # 기본 데이터 매핑
        subjects_result = db.execute(text("SELECT id, name FROM subjects"))
        subjects_map = {row[1]: row[0] for row in subjects_result.fetchall()}
        
        skill_levels_result = db.execute(text("SELECT id, name FROM skill_levels"))
        skill_levels_map = {row[1]: row[0] for row in skill_levels_result.fetchall()}
        
        lesson_types_result = db.execute(text("SELECT id, name FROM lesson_types"))
        lesson_types_map = {row[1]: row[0] for row in lesson_types_result.fetchall()}
        
        success_count = 0
        duplicate_count = 0
        error_count = 0
        
        for i, teacher in enumerate(teachers_data[start_idx:start_idx+limit]):
            try:
                teacher_name = teacher.get('name', f'튜터{start_idx + i + 1}')
                teacher_email = f'{teacher_name.lower()}@example.com'
                
                # 🛡️ 중복 체크
                existing_user = check_duplicate_user(db, teacher_name, teacher_email, 'tutor')
                if existing_user:
                    duplicate_count += 1
                    print(f"   ⚠️ 중복: {teacher_name} (건너뜀)")
                    continue
                
                print(f"\n👨‍🏫 교사 {start_idx + i + 1}: {teacher_name}")
                
                # 1. 사용자 생성
                user_result = db.execute(text("""
                    INSERT INTO users (name, email, password_hash, role, gender, terms_agreed, privacy_policy_agreed, signup_status)
                    VALUES (:name, :email, :password_hash, 'tutor', 'none', true, true, 'active')
                    RETURNING id
                """), {
                    'name': teacher_name,
                    'email': teacher_email,
                    'password_hash': '$2b$12$placeholder'
                })
                
                user_id = user_result.scalar()
                
                # 2. 튜터 프로필 생성
                hourly_rate = teacher.get('price_per_hour', 35000)
                experience = random.randint(1, 8)
                rating = round(random.uniform(3.8, 5.0), 2)
                
                db.execute(text("""
                    INSERT INTO tutor_profiles (
                        user_id, hourly_rate_min, hourly_rate_max, experience_years,
                        rating_avg, rating_count, intro
                    ) VALUES (:user_id, :rate_min, :rate_max, :exp, :rating, :count, :intro)
                """), {
                    'user_id': user_id,
                    'rate_min': max(20000, hourly_rate - 8000),
                    'rate_max': hourly_rate + 12000,
                    'exp': experience,
                    'rating': rating,
                    'count': random.randint(3, 40),
                    'intro': f'{teacher_name} 튜터입니다. {experience}년 경력으로 열정적으로 지도하겠습니다!'
                })
                
                # 3. 과목 관계
                subjects_added = 0
                for subject_name in teacher.get('subject', []):
                    if subject_name in subjects_map:
                        db.execute(text("""
                            INSERT INTO tutor_subjects (tutor_id, subject_id, skill_level_id)
                            VALUES (:tutor_id, :subject_id, :skill_id) ON CONFLICT DO NOTHING
                        """), {
                            'tutor_id': user_id,
                            'subject_id': subjects_map[subject_name],
                            'skill_id': skill_levels_map.get('실무활용 가능', 4)
                        })
                        subjects_added += 1
                
                # 4. 수업 방식
                for lesson_type in teacher.get('lesson_type', []):
                    if lesson_type in lesson_types_map:
                        db.execute(text("""
                            INSERT INTO tutor_lesson_types (tutor_id, lesson_type_id)
                            VALUES (:tutor_id, :lesson_type_id) ON CONFLICT DO NOTHING
                        """), {'tutor_id': user_id, 'lesson_type_id': lesson_types_map[lesson_type]})
                
                # 5. 🗺️ 지역 처리
                regions_added = 0
                for region_str in teacher.get('region', []):
                    sido, sigungu = parse_region(region_str)
                    
                    if sido:
                        sido_id = get_or_create_region(db, sido, '시도', None)
                        db.execute(text("""
                            INSERT INTO tutor_regions (tutor_id, region_id)
                            VALUES (:tutor_id, :region_id)
                        """), {'tutor_id': user_id, 'region_id': sido_id})
                        regions_added += 1
                        
                        if sigungu:
                            sigungu_id = get_or_create_region(db, sigungu, '시군구', sido_id)
                            db.execute(text("""
                                INSERT INTO tutor_regions (tutor_id, region_id)
                                VALUES (:tutor_id, :region_id)
                            """), {'tutor_id': user_id, 'region_id': sigungu_id})
                            regions_added += 1
                
                print(f"   ✅ 활동 지역 {regions_added}개, 지도 과목 {subjects_added}개, 시급 {hourly_rate:,}원")
                success_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"   ❌ 교사 {start_idx + i + 1} 실패: {str(e)}")
                continue
        
        db.commit()
        print(f"\n📊 교사 삽입 결과: ✅성공 {success_count}명, ⚠️중복 {duplicate_count}명, ❌실패 {error_count}명")
        return success_count

def main():
    """메인 실행 함수"""
    print("🚀 통합 데이터 삽입 스크립트 시작 (중복 방지 포함)...")
    
    # 데이터베이스 연결 테스트
    try:
        with SessionLocal() as db:
            result = db.execute(text("SELECT current_database(), current_user"))
            db_info = result.fetchone()
            print(f"✅ 데이터베이스: {db_info[0]}, 사용자: {db_info[1]}")
            
            # 기존 데이터 확인
            existing_students = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'student'")).scalar()
            existing_tutors = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'tutor'")).scalar()
            print(f"📊 기존 데이터: 학생 {existing_students}명, 튜터 {existing_tutors}명")
            
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return
    
    # 삽입할 개수 설정
    STUDENT_LIMIT = 100  # 학생 100명
    TEACHER_LIMIT = 50   # 교사 50명
    
    total_students = 0
    total_teachers = 0
    
    # 학생 데이터 삽입
    if os.path.exists("student_data_korea_500.json"):
        total_students = insert_students_with_regions("student_data_korea_500.json", STUDENT_LIMIT, 0)
    else:
        print("❌ student_data_korea_500.json 파일이 없습니다.")
    
    # 교사 데이터 삽입
    if os.path.exists("teacher_data.json"):
        total_teachers = insert_teachers_with_regions("teacher_data.json", TEACHER_LIMIT, 0)
    else:
        print("❌ teacher_data.json 파일이 없습니다.")
    
    # 최종 결과
    print(f"\n🎉 전체 삽입 작업 완료!")
    print(f"👨‍🎓 학생: {total_students}명 추가")
    print(f"👨‍🏫 교사: {total_teachers}명 추가")
    
    # 최종 데이터 확인
    with SessionLocal() as db:
        final_students = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'student'")).scalar()
        final_tutors = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'tutor'")).scalar()
        total_regions = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
        
        print(f"\n📊 최종 데이터:")
        print(f"   👨‍🎓 전체 학생: {final_students}명")
        print(f"   👨‍🏫 전체 튜터: {final_tutors}명")
        print(f"   🗺️ 전체 지역: {total_regions}개")
    
    print(f"\n🔗 API로 확인해보세요:")
    print(f"   python simple_api_with_db.py")
    print(f"   http://localhost:8000/api/students")
    print(f"   http://localhost:8000/api/users")

if __name__ == "__main__":
    main()