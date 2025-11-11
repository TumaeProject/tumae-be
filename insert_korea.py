#!/usr/bin/env python3
"""
한국 전체 지역 데이터를 계층구조로 삽입하고, 학생/교사 데이터에 지역 정보를 완벽하게 연결하는 스크립트
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

# 🗺️ 한국 전체 지역 데이터 (제공된 데이터 기반)
KOREA_REGIONS = {
    "서울특별시": [
        "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구", 
        "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구", 
        "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구"
    ],
    "부산광역시": [
        "중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구", 
        "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군"
    ],
    "대구광역시": [
        "중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군"
    ],
    "인천광역시": [
        "중구", "동구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구", "강화군", "옹진군"
    ],
    "광주광역시": [
        "동구", "서구", "남구", "북구", "광산구"
    ],
    "대전광역시": [
        "동구", "중구", "서구", "유성구", "대덕구"
    ],
    "울산광역시": [
        "중구", "남구", "동구", "북구", "울주군"
    ],
    "세종특별자치시": [],  # 시군구 없음
    "경기도": [
        "수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시", "동두천시", 
        "안산시", "고양시", "과천시", "구리시", "남양주시", "오산시", "시흥시", "군포시", 
        "의왕시", "하남시", "용인시", "파주시", "이천시", "안성시", "김포시", "화성시", 
        "광주시", "양주시", "포천시", "여주시", "연천군", "가평군", "양평군"
    ],
    "강원특별자치도": [
        "춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "홍천군", 
        "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군", 
        "고성군", "양양군"
    ],
    "충청북도": [
        "청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "진천군", "괴산군", "음성군", "단양군"
    ],
    "충청남도": [
        "천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시", "당진시", 
        "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군"
    ],
    "전라북도": [
        "전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군", "진안군", 
        "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"
    ],
    "전라남도": [
        "목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군", "구례군", 
        "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군", "무안군", 
        "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"
    ],
    "경상북도": [
        "포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시", "상주시", 
        "문경시", "경산시", "군위군", "의성군", "청송군", "영양군", "영덕군", "청도군", 
        "고령군", "성주군", "칠곡군", "예천군", "봉화군", "울진군", "울릉군"
    ],
    "경상남도": [
        "창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시", "양산시", 
        "의령군", "함안군", "창녕군", "고성군", "남해군", "하동군", "산청군", "함양군", 
        "거창군", "합천군"
    ],
    "제주특별자치도": [
        "제주시", "서귀포시"
    ]
}

def setup_regions(db):
    """한국 전체 지역을 계층구조로 데이터베이스에 삽입"""
    
    print("🗺️ 한국 지역 데이터 설정 시작...")
    
    # 기존 지역 데이터 확인
    existing_regions = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    if existing_regions > 100:  # 이미 충분한 지역 데이터가 있다면
        print(f"✅ 기존 지역 데이터 {existing_regions}개 발견. 건너뛰기...")
        return get_region_mappings(db)
    
    sido_mapping = {}
    sigungu_mapping = {}
    total_sido = 0
    total_sigungu = 0
    
    try:
        for sido_name, sigungu_list in KOREA_REGIONS.items():
            # 1. 시도 삽입/조회
            result = db.execute(text("""
                SELECT id FROM regions WHERE name = :name AND level = '시도'
            """), {'name': sido_name})
            
            existing_sido = result.fetchone()
            if existing_sido:
                sido_id = existing_sido[0]
            else:
                result = db.execute(text("""
                    INSERT INTO regions (name, level, parent_id)
                    VALUES (:name, '시도', NULL)
                    RETURNING id
                """), {'name': sido_name})
                sido_id = result.scalar()
                total_sido += 1
            
            sido_mapping[sido_name] = sido_id
            
            # 2. 시군구 삽입
            for sigungu_name in sigungu_list:
                result = db.execute(text("""
                    SELECT id FROM regions 
                    WHERE name = :name AND level = '시군구' AND parent_id = :parent_id
                """), {'name': sigungu_name, 'parent_id': sido_id})
                
                existing_sigungu = result.fetchone()
                if existing_sigungu:
                    sigungu_id = existing_sigungu[0]
                else:
                    result = db.execute(text("""
                        INSERT INTO regions (name, level, parent_id)
                        VALUES (:name, '시군구', :parent_id)
                        RETURNING id
                    """), {'name': sigungu_name, 'parent_id': sido_id})
                    sigungu_id = result.scalar()
                    total_sigungu += 1
                
                # 전체 이름으로 매핑 (예: "서울특별시 종로구")
                full_name = f"{sido_name} {sigungu_name}"
                sigungu_mapping[full_name] = {
                    'sido_id': sido_id,
                    'sigungu_id': sigungu_id,
                    'sido_name': sido_name,
                    'sigungu_name': sigungu_name
                }
        
        db.commit()
        print(f"✅ 지역 데이터 설정 완료!")
        print(f"   📍 시도: {total_sido}개 추가")
        print(f"   📍 시군구: {total_sigungu}개 추가")
        
        return sido_mapping, sigungu_mapping
        
    except Exception as e:
        db.rollback()
        print(f"❌ 지역 설정 실패: {str(e)}")
        return {}, {}

def get_region_mappings(db):
    """기존 지역 데이터에서 매핑 정보 가져오기"""
    
    # 시도 매핑
    sido_result = db.execute(text("SELECT id, name FROM regions WHERE level = '시도'"))
    sido_mapping = {row[1]: row[0] for row in sido_result.fetchall()}
    
    # 시군구 매핑 (전체 이름으로)
    sigungu_result = db.execute(text("""
        SELECT s.id, s.name, s.parent_id, p.name as parent_name
        FROM regions s
        LEFT JOIN regions p ON s.parent_id = p.id
        WHERE s.level = '시군구'
    """))
    
    sigungu_mapping = {}
    for row in sigungu_result.fetchall():
        full_name = f"{row[3]} {row[1]}"  # "시도명 시군구명"
        sigungu_mapping[full_name] = {
            'sido_id': row[2],
            'sigungu_id': row[0],
            'sido_name': row[3],
            'sigungu_name': row[1]
        }
    
    return sido_mapping, sigungu_mapping

def parse_and_match_region(region_str, sido_mapping, sigungu_mapping):
    """지역 문자열을 파싱해서 데이터베이스 지역과 매칭"""
    
    # 직접 매칭 시도 (예: "서울특별시 종로구")
    if region_str in sigungu_mapping:
        return sigungu_mapping[region_str]
    
    # 공백으로 분리해서 매칭
    parts = region_str.strip().split()
    if len(parts) >= 2:
        sido_name = parts[0]
        sigungu_name = parts[1]
        full_name = f"{sido_name} {sigungu_name}"
        
        if full_name in sigungu_mapping:
            return sigungu_mapping[full_name]
        elif sido_name in sido_mapping:
            # 시군구를 찾을 수 없으면 시도만
            return {
                'sido_id': sido_mapping[sido_name],
                'sigungu_id': None,
                'sido_name': sido_name,
                'sigungu_name': None
            }
    
    # 시도만 있는 경우
    elif len(parts) == 1:
        sido_name = parts[0]
        if sido_name in sido_mapping:
            return {
                'sido_id': sido_mapping[sido_name],
                'sigungu_id': None,
                'sido_name': sido_name,
                'sigungu_name': None
            }
    
    return None

def insert_students_with_complete_regions(json_file_path="student_data_korea_500.json", limit=100, start_idx=0):
    """학생 데이터를 완전한 지역 정보와 함께 삽입"""
    
    print(f"\n👨‍🎓 학생 데이터 (완전한 지역) 삽입 시작...")
    
    if not os.path.exists(json_file_path):
        print(f"❌ {json_file_path} 파일을 찾을 수 없습니다.")
        return 0
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        students_data = json.load(f)
    
    with SessionLocal() as db:
        # 지역 매핑 정보 가져오기
        sido_mapping, sigungu_mapping = get_region_mappings(db)
        
        # 기본 데이터 매핑
        subjects_result = db.execute(text("SELECT id, name FROM subjects"))
        subjects_map = {row[1]: row[0] for row in subjects_result.fetchall()}
        
        skill_levels_result = db.execute(text("SELECT id, name FROM skill_levels"))
        skill_levels_map = {row[1]: row[0] for row in skill_levels_result.fetchall()}
        
        goals_result = db.execute(text("SELECT id, name FROM goals"))
        goals_map = {row[1]: row[0] for row in goals_result.fetchall()}
        
        lesson_types_result = db.execute(text("SELECT id, name FROM lesson_types"))
        lesson_types_map = {row[1]: row[0] for row in lesson_types_result.fetchall()}
        
        success_count = 0
        duplicate_count = 0
        
        for i, student in enumerate(students_data[start_idx:start_idx+limit]):
            try:
                student_name = f'학생{student["id"]}'
                student_email = f'student{student["id"]}@example.com'
                
                # 중복 체크
                existing = db.execute(text("""
                    SELECT id FROM users WHERE name = :name OR email = :email
                """), {'name': student_name, 'email': student_email}).fetchone()
                
                if existing:
                    duplicate_count += 1
                    continue
                
                print(f"\n👨‍🎓 {student_name} (원본 ID: {student['id']})")
                
                # 사용자 생성
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
                
                # 학생 프로필 생성
                preferred_price = student.get('price_per_hour', 25000)
                db.execute(text("""
                    INSERT INTO student_profiles (user_id, preferred_price_min, preferred_price_max)
                    VALUES (:user_id, :price_min, :price_max)
                """), {
                    'user_id': user_id,
                    'price_min': max(18000, preferred_price - 5000),
                    'price_max': min(50000, preferred_price + 5000)
                })
                
                # 관계 데이터 삽입 (과목, 실력, 목적, 수업방식)
                for subject_name in student.get('subject', []):
                    if subject_name in subjects_map:
                        db.execute(text("""
                            INSERT INTO student_subjects (user_id, subject_id)
                            VALUES (:user_id, :subject_id) ON CONFLICT DO NOTHING
                        """), {'user_id': user_id, 'subject_id': subjects_map[subject_name]})
                
                # 🗺️ 지역 처리 (핵심!)
                regions_added = 0
                for region_str in student.get('region', []):
                    region_info = parse_and_match_region(region_str, sido_mapping, sigungu_mapping)
                    
                    if region_info:
                        # 시도 지역 추가
                        db.execute(text("""
                            INSERT INTO student_regions (user_id, region_id)
                            VALUES (:user_id, :region_id)
                        """), {'user_id': user_id, 'region_id': region_info['sido_id']})
                        regions_added += 1
                        
                        # 시군구 지역 추가 (있다면)
                        if region_info['sigungu_id']:
                            db.execute(text("""
                                INSERT INTO student_regions (user_id, region_id)
                                VALUES (:user_id, :region_id)
                            """), {'user_id': user_id, 'region_id': region_info['sigungu_id']})
                            regions_added += 1
                            
                        print(f"   🗺️ 지역: {region_str} → {region_info['sido_name']}" + 
                              (f" {region_info['sigungu_name']}" if region_info['sigungu_name'] else ""))
                    else:
                        print(f"   ⚠️ 매칭 실패: {region_str}")
                
                print(f"   ✅ 선호 지역 {regions_added}개, 희망시급 {preferred_price:,}원")
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ 학생 {start_idx + i + 1} 실패: {str(e)}")
                continue
        
        db.commit()
        print(f"\n📊 학생 삽입 결과: ✅성공 {success_count}명, ⚠️중복 {duplicate_count}명")
        return success_count

def insert_teachers_with_complete_regions(json_file_path="teacher_data.json", limit=50, start_idx=0):
    """교사 데이터를 완전한 지역 정보와 함께 삽입"""
    
    print(f"\n👨‍🏫 교사 데이터 (완전한 지역) 삽입 시작...")
    
    if not os.path.exists(json_file_path):
        print(f"❌ {json_file_path} 파일을 찾을 수 없습니다.")
        return 0
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        teachers_data = json.load(f)
    
    with SessionLocal() as db:
        # 지역 매핑 정보 가져오기
        sido_mapping, sigungu_mapping = get_region_mappings(db)
        
        # 기본 데이터 매핑
        subjects_result = db.execute(text("SELECT id, name FROM subjects"))
        subjects_map = {row[1]: row[0] for row in subjects_result.fetchall()}
        
        skill_levels_result = db.execute(text("SELECT id, name FROM skill_levels"))
        skill_levels_map = {row[1]: row[0] for row in skill_levels_result.fetchall()}
        
        lesson_types_result = db.execute(text("SELECT id, name FROM lesson_types"))
        lesson_types_map = {row[1]: row[0] for row in lesson_types_result.fetchall()}
        
        success_count = 0
        duplicate_count = 0
        
        for i, teacher in enumerate(teachers_data[start_idx:start_idx+limit]):
            try:
                teacher_name = teacher.get('name', f'튜터{start_idx + i + 1}')
                teacher_email = f'{teacher_name.lower()}@example.com'
                
                # 중복 체크
                existing = db.execute(text("""
                    SELECT id FROM users WHERE name = :name OR email = :email
                """), {'name': teacher_name, 'email': teacher_email}).fetchone()
                
                if existing:
                    duplicate_count += 1
                    continue
                
                print(f"\n👨‍🏫 {teacher_name}")
                
                # 사용자 생성
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
                
                # 튜터 프로필 생성
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
                
                # 과목 관계
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
                
                # 🗺️ 지역 처리 (핵심!)
                regions_added = 0
                for region_str in teacher.get('region', []):
                    region_info = parse_and_match_region(region_str, sido_mapping, sigungu_mapping)
                    
                    if region_info:
                        # 시도 지역 추가
                        db.execute(text("""
                            INSERT INTO tutor_regions (tutor_id, region_id)
                            VALUES (:tutor_id, :region_id)
                        """), {'tutor_id': user_id, 'region_id': region_info['sido_id']})
                        regions_added += 1
                        
                        # 시군구 지역 추가 (있다면)
                        if region_info['sigungu_id']:
                            db.execute(text("""
                                INSERT INTO tutor_regions (tutor_id, region_id)
                                VALUES (:tutor_id, :region_id)
                            """), {'tutor_id': user_id, 'region_id': region_info['sigungu_id']})
                            regions_added += 1
                            
                        print(f"   🗺️ 지역: {region_str} → {region_info['sido_name']}" + 
                              (f" {region_info['sigungu_name']}" if region_info['sigungu_name'] else ""))
                    else:
                        print(f"   ⚠️ 매칭 실패: {region_str}")
                
                print(f"   ✅ 활동 지역 {regions_added}개, 시급 {hourly_rate:,}원, 경력 {experience}년")
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ 교사 {start_idx + i + 1} 실패: {str(e)}")
                continue
        
        db.commit()
        print(f"\n📊 교사 삽입 결과: ✅성공 {success_count}명, ⚠️중복 {duplicate_count}명")
        return success_count

def main():
    """메인 실행 함수"""
    print("🗺️ 한국 지역 계층구조 + 학생/교사 데이터 완전 삽입 스크립트")
    
    with SessionLocal() as db:
        try:
            # 1. 한국 전체 지역 데이터 설정
            setup_regions(db)
            
            # 2. 현재 상태 확인
            current_students = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'student'")).scalar()
            current_tutors = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'tutor'")).scalar()
            total_regions = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
            
            print(f"\n📊 현재 상태:")
            print(f"   👨‍🎓 학생: {current_students}명")
            print(f"   👨‍🏫 교사: {current_tutors}명")
            print(f"   🗺️ 지역: {total_regions}개")
            
        except Exception as e:
            print(f"❌ 초기 설정 실패: {str(e)}")
            return
    
    # 3. 학생 데이터 삽입
    if os.path.exists("student_data_korea_500.json"):
        insert_students_with_complete_regions("student_data_korea_500.json", limit=100, start_idx=0)
    
    # 4. 교사 데이터 삽입  
    if os.path.exists("teacher_data.json"):
        insert_teachers_with_complete_regions("teacher_data.json", limit=50, start_idx=0)
    
    # 5. 최종 결과
    with SessionLocal() as db:
        final_students = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'student'")).scalar()
        final_tutors = db.execute(text("SELECT COUNT(*) FROM users WHERE role = 'tutor'")).scalar()
        total_regions = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
        
        # 지역별 통계
        sido_count = db.execute(text("SELECT COUNT(*) FROM regions WHERE level = '시도'")).scalar()
        sigungu_count = db.execute(text("SELECT COUNT(*) FROM regions WHERE level = '시군구'")).scalar()
        
        print(f"\n🎉 최종 결과:")
        print(f"   👨‍🎓 전체 학생: {final_students}명")
        print(f"   👨‍🏫 전체 교사: {final_tutors}명")
        print(f"   🗺️ 전체 지역: {total_regions}개 (시도: {sido_count}, 시군구: {sigungu_count})")
        
        # 지역 연결 통계
        student_regions = db.execute(text("SELECT COUNT(*) FROM student_regions")).scalar()
        tutor_regions = db.execute(text("SELECT COUNT(*) FROM tutor_regions")).scalar()
        
        print(f"\n🔗 지역 연결:")
        print(f"   👨‍🎓 학생-지역: {student_regions}개 연결")
        print(f"   👨‍🏫 교사-지역: {tutor_regions}개 연결")

if __name__ == "__main__":
    main()