#!/usr/bin/env python3
"""
튜터 지역 연결 상태 빠른 확인
"""

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

def check_tutor_regions():
    """튜터 지역 연결 상태 확인"""
    
    with engine.connect() as conn:
        print("🔍 튜터 지역 연결 상태 확인")
        
        # 1. 전체 통계
        total_tutors = conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'tutor'")).scalar()
        total_tutor_regions = conn.execute(text("SELECT COUNT(*) FROM tutor_regions")).scalar()
        
        tutors_with_regions = conn.execute(text("""
            SELECT COUNT(DISTINCT tutor_id) FROM tutor_regions
        """)).scalar()
        
        print(f"📊 전체 튜터: {total_tutors}명")
        print(f"📊 튜터 지역 연결: {total_tutor_regions}개")
        print(f"📊 지역이 있는 튜터: {tutors_with_regions}명 ({tutors_with_regions/total_tutors*100:.1f}%)")
        
        # 2. 특정 튜터 ID 51 확인
        print(f"\n🔍 튜터 ID 51 지역 확인:")
        
        tutor_51_regions = conn.execute(text("""
            SELECT 
                r.id,
                r.name,
                r.level,
                CASE 
                    WHEN r.level = '시군구' THEN p.name || ' ' || r.name
                    ELSE r.name
                END as full_name
            FROM tutor_regions tr
            JOIN regions r ON tr.region_id = r.id
            LEFT JOIN regions p ON r.parent_id = p.id
            WHERE tr.tutor_id = 51
        """)).fetchall()
        
        if tutor_51_regions:
            print(f"   ✅ 튜터 ID 51의 지역 {len(tutor_51_regions)}개:")
            for region in tutor_51_regions:
                print(f"      📍 {region[3]} (ID: {region[0]}, Level: {region[2]})")
        else:
            print(f"   ❌ 튜터 ID 51에게 연결된 지역이 없습니다!")
        
        # 3. 지역이 있는 튜터 샘플
        print(f"\n✅ 지역이 있는 튜터 샘플:")
        
        tutors_with_regions_sample = conn.execute(text("""
            SELECT 
                u.id,
                u.name,
                COUNT(tr.region_id) as region_count
            FROM users u
            JOIN tutor_regions tr ON u.id = tr.tutor_id
            WHERE u.role = 'tutor'
            GROUP BY u.id, u.name
            ORDER BY u.id
            LIMIT 5
        """)).fetchall()
        
        if tutors_with_regions_sample:
            for tutor in tutors_with_regions_sample:
                print(f"   👨‍🏫 {tutor[1]} (ID: {tutor[0]}): {tutor[2]}개 지역")
        else:
            print(f"   ❌ 지역이 있는 튜터가 없습니다!")
        
        # 4. 문제 진단
        print(f"\n💡 문제 진단:")
        
        if total_tutor_regions == 0:
            print(f"   ⚠️ 모든 튜터의 지역 연결이 없습니다!")
            print(f"   🛠️ 해결책: python insert_final_fixed.py 실행")
        elif tutors_with_regions < total_tutors * 0.5:
            print(f"   ⚠️ 많은 튜터들이 지역 연결이 안되어 있습니다!")
            print(f"   🛠️ 해결책: python add_random_regions.py 실행")
        else:
            print(f"   ✅ 대부분의 튜터들이 지역 연결되어 있습니다.")

if __name__ == "__main__":
    check_tutor_regions()