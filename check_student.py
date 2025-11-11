#!/usr/bin/env python3
"""
학생의 지역 연결 상태를 확인하는 스크립트
"""

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

def check_student_regions():
    """학생들의 지역 연결 상태 확인"""
    
    with engine.connect() as conn:
        print("🔍 학생-지역 연결 상태 확인\n")
        
        # 1. 전체 통계
        total_students = conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'student'")).scalar()
        total_connections = conn.execute(text("SELECT COUNT(*) FROM student_regions")).scalar()
        
        print(f"📊 전체 통계:")
        print(f"   👨‍🎓 총 학생: {total_students}명")
        print(f"   🔗 총 지역 연결: {total_connections}개")
        print(f"   📍 학생당 평균 지역: {total_connections/total_students:.1f}개" if total_students > 0 else "   📍 학생당 평균: 0개")
        
        # 2. 샘플 학생들의 지역 확인 (처음 10명)
        print(f"\n🎯 샘플 학생들의 희망 지역:")
        
        result = conn.execute(text("""
            SELECT 
                u.id,
                u.name,
                u.email,
                COUNT(sr.region_id) as region_count
            FROM users u
            LEFT JOIN student_regions sr ON u.id = sr.user_id
            WHERE u.role = 'student'
            GROUP BY u.id, u.name, u.email
            ORDER BY u.id
            LIMIT 10
        """))
        
        for row in result:
            user_id, name, email, region_count = row
            print(f"\n   👨‍🎓 {name} ({email})")
            print(f"      🗺️ 희망 지역: {region_count}개")
            
            # 해당 학생의 상세 지역 정보
            regions_result = conn.execute(text("""
                SELECT 
                    r.name,
                    r.level,
                    CASE 
                        WHEN r.level = '시군구' THEN 
                            (SELECT parent.name FROM regions parent WHERE parent.id = r.parent_id)
                        ELSE NULL 
                    END as parent_name
                FROM student_regions sr
                JOIN regions r ON sr.region_id = r.id
                WHERE sr.user_id = :user_id
                ORDER BY r.level, r.name
            """), {'user_id': user_id})
            
            for region_row in regions_result:
                region_name, level, parent_name = region_row
                if level == '시도':
                    print(f"         📍 {region_name} (시도)")
                else:
                    print(f"         📍 {parent_name} {region_name} (시군구)")
        
        # 3. 지역별 인기도 확인
        print(f"\n🏆 인기 지역 TOP 10:")
        
        popular_regions = conn.execute(text("""
            SELECT 
                r.name,
                r.level,
                COUNT(sr.user_id) as student_count,
                CASE 
                    WHEN r.level = '시군구' THEN 
                        (SELECT parent.name FROM regions parent WHERE parent.id = r.parent_id)
                    ELSE NULL 
                END as parent_name
            FROM student_regions sr
            JOIN regions r ON sr.region_id = r.id
            GROUP BY r.id, r.name, r.level, r.parent_id
            ORDER BY student_count DESC
            LIMIT 10
        """))
        
        for i, row in enumerate(popular_regions, 1):
            region_name, level, student_count, parent_name = row
            if level == '시도':
                print(f"   {i:2d}. {region_name} - {student_count}명")
            else:
                print(f"   {i:2d}. {parent_name} {region_name} - {student_count}명")
        
        # 4. 지역이 없는 학생 확인
        no_region_students = conn.execute(text("""
            SELECT COUNT(*)
            FROM users u
            LEFT JOIN student_regions sr ON u.id = sr.user_id
            WHERE u.role = 'student' AND sr.user_id IS NULL
        """)).scalar()
        
        print(f"\n⚠️ 지역 정보가 없는 학생: {no_region_students}명")

def check_specific_student_regions():
    """특정 학생의 지역 정보 상세 확인"""
    
    with engine.connect() as conn:
        print("\n🔍 학생1의 지역 정보 상세 확인:")
        
        result = conn.execute(text("""
            SELECT 
                u.name,
                r.id as region_id,
                r.name as region_name,
                r.level,
                CASE 
                    WHEN r.level = '시군구' THEN 
                        (SELECT parent.name || ' ' || r.name FROM regions parent WHERE parent.id = r.parent_id)
                    ELSE r.name 
                END as full_name
            FROM users u
            JOIN student_regions sr ON u.id = sr.user_id
            JOIN regions r ON sr.region_id = r.id
            WHERE u.name = '학생1'
            ORDER BY r.level, r.name
        """))
        
        regions = result.fetchall()
        if regions:
            student_name = regions[0][0]
            print(f"   👨‍🎓 {student_name}의 희망 지역 {len(regions)}개:")
            for row in regions:
                _, region_id, region_name, level, full_name = row
                print(f"      🗺️ {full_name} (ID: {region_id}, Level: {level})")
        else:
            print("   ❌ 학생1의 지역 정보를 찾을 수 없습니다.")

if __name__ == "__main__":
    check_student_regions()
    check_specific_student_regions()