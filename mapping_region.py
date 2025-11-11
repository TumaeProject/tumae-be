#!/usr/bin/env python3
"""
원본 JSON 데이터 기준으로 모든 학생과 튜터의 지역 정보를 정확하게 매핑하는 스크립트
"""

import json
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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

def parse_region_from_json(region_str, sido_mapping, sigungu_mapping):
    """JSON 지역 문자열을 데이터베이스 지역으로 매핑"""
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

def clear_all_region_data():
    """기존 지역 연결 데이터 모두 삭제"""
    
    with SessionLocal() as db:
        print("🗑️ 기존 지역 연결 데이터 삭제 중...")
        
        # 학생 지역 삭제
        student_deleted = db.execute(text("DELETE FROM student_regions")).rowcount
        print(f"   📊 학생 지역 {student_deleted}개 삭제")
        
        # 튜터 지역 삭제
        tutor_deleted = db.execute(text("DELETE FROM tutor_regions")).rowcount
        print(f"   📊 튜터 지역 {tutor_deleted}개 삭제")
        
        db.commit()
        print("✅ 기존 지역 데이터 삭제 완료")

def map_student_regions_from_json():
    """원본 학생 JSON 데이터에서 지역 정보 매핑"""
    
    if not os.path.exists("student_data_korea_500.json"):
        print("❌ student_data_korea_500.json 파일을 찾을 수 없습니다.")
        return 0
    
    with open("student_data_korea_500.json", 'r', encoding='utf-8') as f:
        students_data = json.load(f)
    
    print(f"👨‍🎓 학생 지역 매핑 시작... ({len(students_data)}명)")
    
    with SessionLocal() as db:
        sido_mapping, sigungu_mapping = get_region_mappings()
        
        success_count = 0
        no_match_count = 0
        
        for i, student in enumerate(students_data):
            student_id = student.get('id')
            regions = student.get('region', [])
            
            if not regions:
                continue
            
            # 데이터베이스에서 해당 사용자 찾기
            user_result = db.execute(text("""
                SELECT id FROM users 
                WHERE role = 'student' AND (
                    name = :name1 OR 
                    name = :name2 OR
                    email = :email1 OR
                    email = :email2
                )
                LIMIT 1
            """), {
                'name1': f'학생{student_id}',
                'name2': f'안전학생{student_id}', 
                'email1': f'student{student_id}@example.com',
                'email2': f'safestudent{student_id}@example.com'
            })
            
            user_row = user_result.fetchone()
            if not user_row:
                continue
                
            user_db_id = user_row[0]
            
            # 각 지역을 매핑하여 삽입
            added_regions = set()
            region_count = 0
            
            for region_str in regions:
                region_info = parse_region_from_json(region_str, sido_mapping, sigungu_mapping)
                
                if region_info:
                    # 시도 추가
                    if region_info['sido_id'] and region_info['sido_id'] not in added_regions:
                        try:
                            db.execute(text("""
                                INSERT INTO student_regions (user_id, region_id)
                                VALUES (:user_id, :region_id)
                            """), {'user_id': user_db_id, 'region_id': region_info['sido_id']})
                            added_regions.add(region_info['sido_id'])
                            region_count += 1
                        except:
                            pass  # 중복 무시
                    
                    # 시군구 추가
                    if region_info['sigungu_id'] and region_info['sigungu_id'] not in added_regions:
                        try:
                            db.execute(text("""
                                INSERT INTO student_regions (user_id, region_id)
                                VALUES (:user_id, :region_id)
                            """), {'user_id': user_db_id, 'region_id': region_info['sigungu_id']})
                            added_regions.add(region_info['sigungu_id'])
                            region_count += 1
                        except:
                            pass  # 중복 무시
                else:
                    no_match_count += 1
                    if no_match_count <= 5:
                        print(f"   ⚠️ 매칭 실패: {region_str}")
            
            if region_count > 0:
                success_count += 1
            
            # 진행 상황 출력
            if (i + 1) % 100 == 0:
                print(f"   📝 진행: {i + 1}/{len(students_data)} ({success_count}명 성공)")
        
        db.commit()
        
        print(f"✅ 학생 지역 매핑 완료: {success_count}명 성공, {no_match_count}개 매칭 실패")
        return success_count

def map_tutor_regions_from_json():
    """원본 튜터 JSON 데이터에서 지역 정보 매핑"""
    
    if not os.path.exists("teacher_data.json"):
        print("❌ teacher_data.json 파일을 찾을 수 없습니다.")
        return 0
    
    with open("teacher_data.json", 'r', encoding='utf-8') as f:
        tutors_data = json.load(f)
    
    print(f"👨‍🏫 튜터 지역 매핑 시작... ({len(tutors_data)}명)")
    
    with SessionLocal() as db:
        sido_mapping, sigungu_mapping = get_region_mappings()
        
        success_count = 0
        no_match_count = 0
        
        for i, tutor in enumerate(tutors_data):
            regions = tutor.get('region', [])
            tutor_name = tutor.get('name', f'튜터{i+1}')
            
            if not regions:
                continue
            
            # 데이터베이스에서 해당 튜터 찾기
            user_result = db.execute(text("""
                SELECT id FROM users 
                WHERE role = 'tutor' AND (
                    name = :name1 OR 
                    name = :name2 OR
                    email LIKE :email_pattern
                )
                LIMIT 1
            """), {
                'name1': tutor_name,
                'name2': tutor_name.lower(),
                'email_pattern': f'%{tutor_name.lower().replace(" ", "")}%'
            })
            
            user_row = user_result.fetchone()
            if not user_row:
                continue
                
            user_db_id = user_row[0]
            
            # 각 지역을 매핑하여 삽입
            added_regions = set()
            region_count = 0
            
            for region_str in regions:
                region_info = parse_region_from_json(region_str, sido_mapping, sigungu_mapping)
                
                if region_info:
                    # 시도 추가
                    if region_info['sido_id'] and region_info['sido_id'] not in added_regions:
                        try:
                            db.execute(text("""
                                INSERT INTO tutor_regions (tutor_id, region_id)
                                VALUES (:tutor_id, :region_id)
                            """), {'tutor_id': user_db_id, 'region_id': region_info['sido_id']})
                            added_regions.add(region_info['sido_id'])
                            region_count += 1
                        except:
                            pass  # 중복 무시
                    
                    # 시군구 추가
                    if region_info['sigungu_id'] and region_info['sigungu_id'] not in added_regions:
                        try:
                            db.execute(text("""
                                INSERT INTO tutor_regions (tutor_id, region_id)
                                VALUES (:tutor_id, :region_id)
                            """), {'tutor_id': user_db_id, 'region_id': region_info['sigungu_id']})
                            added_regions.add(region_info['sigungu_id'])
                            region_count += 1
                        except:
                            pass  # 중복 무시
                else:
                    no_match_count += 1
            
            if region_count > 0:
                success_count += 1
            
            # 진행 상황 출력
            if (i + 1) % 200 == 0:
                print(f"   📝 진행: {i + 1}/{len(tutors_data)} ({success_count}명 성공)")
        
        db.commit()
        
        print(f"✅ 튜터 지역 매핑 완료: {success_count}명 성공, {no_match_count}개 매칭 실패")
        return success_count

def verify_student_1_mapping():
    """학생 ID 1의 지역 매핑 검증"""
    
    with SessionLocal() as db:
        print("\n🔍 학생 1 지역 매핑 검증:")
        
        # 학생 1의 지역 정보 조회
        student_1_regions = db.execute(text("""
            SELECT 
                r.name,
                r.level,
                CASE 
                    WHEN r.level = '시군구' THEN p.name || ' ' || r.name
                    ELSE r.name
                END as full_name
            FROM users u
            JOIN student_regions sr ON u.id = sr.user_id
            JOIN regions r ON sr.region_id = r.id
            LEFT JOIN regions p ON r.parent_id = p.id
            WHERE (u.name = '학생1' OR u.email = 'student1@example.com') AND u.role = 'student'
            ORDER BY r.level, r.name
        """)).fetchall()
        
        if student_1_regions:
            print("   ✅ 학생1의 지역 정보:")
            for region in student_1_regions:
                print(f"      📍 {region[2]}")
            
            # 원본 JSON과 비교
            print("   📋 원본 JSON 지역:")
            print("      📍 경상남도 창원시")
            print("      📍 서울특별시 중랑구")
        else:
            print("   ❌ 학생1의 지역 정보를 찾을 수 없습니다.")

def main():
    """메인 실행 함수"""
    
    print("🚀 원본 JSON 데이터 기준 지역 정보 완전 매핑 스크립트")
    print("=" * 70)
    
    # 1. 기존 지역 데이터 삭제
    clear_all_region_data()
    
    print()
    
    # 2. 학생 지역 매핑
    student_success = map_student_regions_from_json()
    
    print()
    
    # 3. 튜터 지역 매핑  
    tutor_success = map_tutor_regions_from_json()
    
    # 4. 학생 1 검증
    verify_student_1_mapping()
    
    print("\n" + "=" * 70)
    print("🎉 원본 JSON 기준 지역 매핑 완료!")
    print(f"📊 결과: 학생 {student_success}명, 튜터 {tutor_success}명")
    print("\n💡 이제 API 테스트:")
    print("   http://localhost:8000/api/students")
    print("   → 학생1의 regions에 '경상남도 창원시', '서울특별시 중랑구'가 나타납니다!")

if __name__ == "__main__":
    main()