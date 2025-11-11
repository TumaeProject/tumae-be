#!/usr/bin/env python3
"""
트랜잭션 문제를 완전히 해결한 최종 데이터 삽입 스크립트
학생 500명 + 교사 전체, 완벽한 지역 연결
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
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 🗺️ 한국 전체 지역 데이터
KOREA_REGIONS = {
    "서울특별시": ["종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구"],
    "부산광역시": ["중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구", "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군"],
    "대구광역시": ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군"],
    "인천광역시": ["중구", "동구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구", "강화군", "옹진군"],
    "광주광역시": ["동구", "서구", "남구", "북구", "광산구"],
    "대전광역시": ["동구", "중구", "서구", "유성구", "대덕구"],
    "울산광역시": ["중구", "남구", "동구", "북구", "울주군"],
    "세종특별자치시": [],
    "경기도": ["수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시", "동두천시", "안산시", "고양시", "과천시", "구리시", "남양주시", "오산시", "시흥시", "군포시", "의왕시", "하남시", "용인시", "파주시", "이천시", "안성시", "김포시", "화성시", "광주시", "양주시", "포천시", "여주시", "연천군", "가평군", "양평군"],
    "강원특별자치도": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군", "고성군", "양양군"],
    "충청북도": ["청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "진천군", "괴산군", "음성군", "단양군"],
    "충청남도": ["천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시", "당진시", "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군"],
    "전라북도": ["전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군", "진안군", "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"],
    "전라남도": ["목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군", "구례군", "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군", "무안군", "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"],
    "경상북도": ["포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시", "상주시", "문경시", "경산시", "군위군", "의성군", "청송군", "영양군", "영덕군", "청도군", "고령군", "성주군", "칠곡군", "예천군", "봉화군", "울진군", "울릉군"],
    "경상남도": ["창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시", "양산시", "의령군", "함안군", "창녕군", "고성군", "남해군", "하동군", "산청군", "함양군", "거창군", "합천군"],
    "제주특별자치도": ["제주시", "서귀포시"]
}

def get_region_mappings():
    """지역 매핑 정보 가져오기"""
    with SessionLocal() as db:
        # 시도 매핑
        sido_result = db.execute(text("SELECT id, name FROM regions WHERE level = '시도'"))
        sido_mapping = {row[1]: row[0] for row in sido_result.fetchall()}
        
        # 시군구 매핑
        sigungu_result = db.execute(text("""
            SELECT s.id, s.name, s.parent_id, p.name as parent_name
            FROM regions s
            LEFT JOIN regions p ON s.parent_id = p.id
            WHERE s.level = '시군구'
        """))
        
        sigungu_mapping = {}
        for row in sigungu_result.fetchall():
            if row[3]:  # parent_name이 있는 경우만
                full_name = f"{row[3]} {row[1]}"
                sigungu_mapping[full_name] = {
                    'sido_id': row[2],
                    'sigungu_id': row[0],
                    'sido_name': row[3],
                    'sigungu_name': row[1]
                }
        
        return sido_mapping, sigungu_mapping

def parse_region_safe(region_str, sido_mapping, sigungu_mapping):
    """안전한 지역 파싱"""
    if not region_str:
        return None
        
    # 직접 매칭
    if region_str in sigungu_mapping:
        return sigungu_mapping[region_str]
    
    # 파싱 매칭
    parts = region_str.strip().split()
    if len(parts) >= 2:
        sido_name = parts[0]
        sigungu_name = parts[1]
        full_name = f"{sido_name} {sigungu_name}"
        
        if full_name in sigungu_mapping:
            return sigungu_mapping[full_name]
        elif sido_name in sido_mapping:
            return {
                'sido_id': sido_mapping[sido_name],
                'sigungu_id': None,
                'sido_name': sido_name,
                'sigungu_name': None
            }
    
    return None

def insert_one_student(student_data, sido_mapping, sigungu_mapping, subjects_map, skill_levels_map, goals_map, lesson_types_map):
    """개별 학생 하나씩 안전하게 삽입"""
    
    # 각 학생마다 새로운 세션 생성
    with SessionLocal() as db:
        try:
            student_name = f'학생{student_data["id"]}'
            student_email = f'student{student_data["id"]}@example.com'
            
            # 중복 체크
            existing = db.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {'email': student_email}).fetchone()
            
            if existing:
                return False, f"중복: {student_name}"
            
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
            preferred_price = student_data.get('price_per_hour', 25000)
            db.execute(text("""
                INSERT INTO student_profiles (user_id, preferred_price_min, preferred_price_max)
                VALUES (:user_id, :price_min, :price_max)
            """), {
                'user_id': user_id,
                'price_min': max(18000, preferred_price - 5000),
                'price_max': min(50000, preferred_price + 5000)
            })
            
            # 3. 과목 관계
            for subject_name in student_data.get('subject', []):
                if subject_name in subjects_map:
                    db.execute(text("""
                        INSERT INTO student_subjects (user_id, subject_id)
                        VALUES (:user_id, :subject_id)
                    """), {'user_id': user_id, 'subject_id': subjects_map[subject_name]})
            
            # 4. 실력 수준
            student_level = student_data.get('student_level')
            if student_level and student_level in skill_levels_map:
                db.execute(text("""
                    INSERT INTO student_skill_levels (user_id, skill_level_id)
                    VALUES (:user_id, :skill_level_id)
                """), {'user_id': user_id, 'skill_level_id': skill_levels_map[student_level]})
            
            # 5. 목적
            purpose = student_data.get('purpose')
            if purpose and purpose in goals_map:
                db.execute(text("""
                    INSERT INTO student_goals (user_id, goal_id)
                    VALUES (:user_id, :goal_id)
                """), {'user_id': user_id, 'goal_id': goals_map[purpose]})
            
            # 6. 수업 방식
            for lesson_type_name in student_data.get('lesson_type', []):
                mapped_type = lesson_type_name
                if lesson_type_name == '학원':
                    mapped_type = '그룹과외'
                elif lesson_type_name == '기타':
                    mapped_type = '무관'
                
                if mapped_type in lesson_types_map:
                    db.execute(text("""
                        INSERT INTO student_lesson_types (user_id, lesson_type_id)
                        VALUES (:user_id, :lesson_type_id)
                    """), {'user_id': user_id, 'lesson_type_id': lesson_types_map[mapped_type]})
            
            # 7. 🗺️ 지역 처리 (핵심!)
            added_regions = set()
            region_count = 0
            
            for region_str in student_data.get('region', []):
                region_info = parse_region_safe(region_str, sido_mapping, sigungu_mapping)
                
                if region_info:
                    # 시도 추가 (중복 방지)
                    if region_info['sido_id'] not in added_regions:
                        db.execute(text("""
                            INSERT INTO student_regions (user_id, region_id)
                            VALUES (:user_id, :region_id)
                        """), {'user_id': user_id, 'region_id': region_info['sido_id']})
                        added_regions.add(region_info['sido_id'])
                        region_count += 1
                    
                    # 시군구 추가 (있는 경우)
                    if region_info['sigungu_id'] and region_info['sigungu_id'] not in added_regions:
                        db.execute(text("""
                            INSERT INTO student_regions (user_id, region_id)
                            VALUES (:user_id, :region_id)
                        """), {'user_id': user_id, 'region_id': region_info['sigungu_id']})
                        added_regions.add(region_info['sigungu_id'])
                        region_count += 1
            
            # 트랜잭션 커밋
            db.commit()
            
            return True, f"성공: {student_name} (지역 {region_count}개, 시급 {preferred_price:,}원)"
            
        except Exception as e:
            db.rollback()
            return False, f"실패: {student_name} - {str(e)}"

def insert_one_teacher(teacher_data, idx, sido_mapping, sigungu_mapping, subjects_map, skill_levels_map, lesson_types_map):
    """개별 교사 하나씩 안전하게 삽입"""
    
    # 각 교사마다 새로운 세션 생성
    with SessionLocal() as db:
        try:
            teacher_name = teacher_data.get('name', f'튜터{idx+1}')
            teacher_email = f'{teacher_name.lower().replace(" ", "")}@example.com'
            
            # 중복 체크
            existing = db.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {'email': teacher_email}).fetchone()
            
            if existing:
                return False, f"중복: {teacher_name}"
            
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
            hourly_rate = teacher_data.get('price_per_hour', 35000)
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
            for subject_name in teacher_data.get('subject', []):
                if subject_name in subjects_map:
                    db.execute(text("""
                        INSERT INTO tutor_subjects (tutor_id, subject_id, skill_level_id)
                        VALUES (:tutor_id, :subject_id, :skill_id)
                    """), {
                        'tutor_id': user_id,
                        'subject_id': subjects_map[subject_name],
                        'skill_id': skill_levels_map.get('실무활용 가능', 4)
                    })
            
            # 4. 수업 방식
            for lesson_type in teacher_data.get('lesson_type', []):
                if lesson_type in lesson_types_map:
                    db.execute(text("""
                        INSERT INTO tutor_lesson_types (tutor_id, lesson_type_id)
                        VALUES (:tutor_id, :lesson_type_id)
                    """), {'tutor_id': user_id, 'lesson_type_id': lesson_types_map[lesson_type]})
            
            # 5. 🗺️ 지역 처리
            added_regions = set()
            region_count = 0
            
            for region_str in teacher_data.get('region', []):
                region_info = parse_region_safe(region_str, sido_mapping, sigungu_mapping)
                
                if region_info:
                    # 시도 추가
                    if region_info['sido_id'] not in added_regions:
                        db.execute(text("""
                            INSERT INTO tutor_regions (tutor_id, region_id)
                            VALUES (:tutor_id, :region_id)
                        """), {'tutor_id': user_id, 'region_id': region_info['sido_id']})
                        added_regions.add(region_info['sido_id'])
                        region_count += 1
                    
                    # 시군구 추가
                    if region_info['sigungu_id'] and region_info['sigungu_id'] not in added_regions:
                        db.execute(text("""
                            INSERT INTO tutor_regions (tutor_id, region_id)
                            VALUES (:tutor_id, :region_id)
                        """), {'tutor_id': user_id, 'region_id': region_info['sigungu_id']})
                        added_regions.add(region_info['sigungu_id'])
                        region_count += 1
            
            # 트랜잭션 커밋
            db.commit()
            
            return True, f"성공: {teacher_name} (지역 {region_count}개, 시급 {hourly_rate:,}원)"
            
        except Exception as e:
            db.rollback()
            return False, f"실패: {teacher_name} - {str(e)}"

def main():
    """메인 실행 함수"""
    print("🚀 트랜잭션 문제 해결! 학생 500명 + 교사 전체 완전 삽입!")
    
    # 1. 지역 매핑 가져오기
    sido_mapping, sigungu_mapping = get_region_mappings()
    print(f"🗺️ 지역 로드: 시도 {len(sido_mapping)}개, 시군구 {len(sigungu_mapping)}개")
    
    # 2. 기본 매핑 데이터 가져오기
    with SessionLocal() as db:
        subjects_result = db.execute(text("SELECT id, name FROM subjects"))
        subjects_map = {row[1]: row[0] for row in subjects_result.fetchall()}
        
        skill_levels_result = db.execute(text("SELECT id, name FROM skill_levels"))
        skill_levels_map = {row[1]: row[0] for row in skill_levels_result.fetchall()}
        
        goals_result = db.execute(text("SELECT id, name FROM goals"))
        goals_map = {row[1]: row[0] for row in goals_result.fetchall()}
        
        lesson_types_result = db.execute(text("SELECT id, name FROM lesson_types"))
        lesson_types_map = {row[1]: row[0] for row in lesson_types_result.fetchall()}
    
    # 3. 학생 500명 삽입
    print(f"\n👨‍🎓 학생 500명 삽입 시작...")
    
    if os.path.exists("student_data_korea_500.json"):
        with open("student_data_korea_500.json", 'r', encoding='utf-8') as f:
            students_data = json.load(f)
        
        student_success = 0
        student_duplicate = 0
        student_error = 0
        
        for i, student in enumerate(students_data):
            success, message = insert_one_student(
                student, sido_mapping, sigungu_mapping, 
                subjects_map, skill_levels_map, goals_map, lesson_types_map
            )
            
            if success:
                student_success += 1
                if student_success % 50 == 0:
                    print(f"   ✅ 진행: {student_success}명 성공!")
            else:
                if "중복" in message:
                    student_duplicate += 1
                else:
                    student_error += 1
                    if student_error <= 3:
                        print(f"   ❌ {message}")
        
        print(f"\n📊 학생 삽입 결과: ✅{student_success}명 성공, ⚠️{student_duplicate}명 중복, ❌{student_error}명 실패")
    
    # 4. 교사 삽입
    print(f"\n👨‍🏫 교사 삽입 시작...")
    
    if os.path.exists("teacher_data.json"):
        with open("teacher_data.json", 'r', encoding='utf-8') as f:
            teachers_data = json.load(f)
        
        teacher_success = 0
        teacher_duplicate = 0
        teacher_error = 0
        
        for i, teacher in enumerate(teachers_data):
            success, message = insert_one_teacher(
                teacher, i, sido_mapping, sigungu_mapping,
                subjects_map, skill_levels_map, lesson_types_map
            )
            
            if success:
                teacher_success += 1
                if teacher_success % 100 == 0:
                    print(f"   ✅ 진행: {teacher_success}명 성공!")
            else:
                if "중복" in message:
                    teacher_duplicate += 1
                else:
                    teacher_error += 1
                    if teacher_error <= 3:
                        print(f"   ❌ {message}")
        
        print(f"\n📊 교사 삽입 결과: ✅{teacher_success}명 성공, ⚠️{teacher_duplicate}명 중복, ❌{teacher_error}명 실패")
    
    # 5. 최종 결과 확인
    with SessionLocal() as db:
        final_students = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'student'")).scalar()
        final_tutors = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'tutor'")).scalar()
        total_regions = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
        
        student_regions = db.execute(text("SELECT COUNT(*) FROM student_regions")).scalar()
        tutor_regions = db.execute(text("SELECT COUNT(*) FROM tutor_regions")).scalar()
        
        print(f"\n🎉 최종 완성 결과:")
        print(f"   👨‍🎓 전체 학생: {final_students}명")
        print(f"   👨‍🏫 전체 교사: {final_tutors}명")
        print(f"   🗺️ 전체 지역: {total_regions}개")
        print(f"   🔗 학생-지역 연결: {student_regions}개")
        print(f"   🔗 교사-지역 연결: {tutor_regions}개")
        
        print(f"\n🚀 API 테스트:")
        print(f"   python simple_api_with_db.py")
        print(f"   http://localhost:8000/api/students")

if __name__ == "__main__":
    main()