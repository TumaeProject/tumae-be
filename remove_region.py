#!/usr/bin/env python3
"""
학생과 튜터 모두에서 중복된 시도 정보를 제거하는 통합 스크립트
시군구가 있는 경우 상위 시도는 삭제 (중복 제거)
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def remove_all_redundant_sido():
    """학생과 튜터 모두에서 중복된 시도 지역 데이터 제거"""
    
    with SessionLocal() as db:
        print("🧹 학생 & 튜터 중복 시도 제거 시작...")
        print("=" * 50)
        
        try:
            # 1. 학생 중복 시도 제거
            print("📍 1단계: 학생 중복 시도 제거")
            
            # 현재 학생 지역 수 확인
            student_current = db.execute(text("SELECT COUNT(*) FROM student_regions")).scalar()
            print(f"   📊 현재 학생 지역: {student_current}개")
            
            # 학생 중복 시도 삭제
            student_delete_query = text("""
                DELETE FROM student_regions 
                WHERE region_id IN (
                    SELECT DISTINCT sr_sido.region_id
                    FROM student_regions sr_sido
                    JOIN regions sido ON sr_sido.region_id = sido.id
                    JOIN student_regions sr_sigungu ON sr_sido.user_id = sr_sigungu.user_id
                    JOIN regions sigungu ON sr_sigungu.region_id = sigungu.id
                    WHERE sido.level = '시도' 
                      AND sigungu.level = '시군구'
                      AND sigungu.parent_id = sido.id
                )
                AND region_id IN (
                    SELECT id FROM regions WHERE level = '시도'
                )
            """)
            
            student_deleted = db.execute(student_delete_query).rowcount
            print(f"   🗑️ 학생 중복 시도 {student_deleted}개 삭제")
            
            # 삭제 후 학생 지역 수 확인
            student_final = db.execute(text("SELECT COUNT(*) FROM student_regions")).scalar()
            print(f"   📊 삭제 후 학생 지역: {student_final}개")
            
            # 2. 튜터 중복 시도 제거
            print(f"\n📍 2단계: 튜터 중복 시도 제거")
            
            # 현재 튜터 지역 수 확인
            tutor_current = db.execute(text("SELECT COUNT(*) FROM tutor_regions")).scalar()
            print(f"   📊 현재 튜터 지역: {tutor_current}개")
            
            # 튜터 중복 시도 삭제
            tutor_delete_query = text("""
                DELETE FROM tutor_regions 
                WHERE region_id IN (
                    SELECT DISTINCT tr_sido.region_id
                    FROM tutor_regions tr_sido
                    JOIN regions sido ON tr_sido.region_id = sido.id
                    JOIN tutor_regions tr_sigungu ON tr_sido.tutor_id = tr_sigungu.tutor_id
                    JOIN regions sigungu ON tr_sigungu.region_id = sigungu.id
                    WHERE sido.level = '시도' 
                      AND sigungu.level = '시군구'
                      AND sigungu.parent_id = sido.id
                )
                AND region_id IN (
                    SELECT id FROM regions WHERE level = '시도'
                )
            """)
            
            tutor_deleted = db.execute(tutor_delete_query).rowcount
            print(f"   🗑️ 튜터 중복 시도 {tutor_deleted}개 삭제")
            
            # 삭제 후 튜터 지역 수 확인
            tutor_final = db.execute(text("SELECT COUNT(*) FROM tutor_regions")).scalar()
            print(f"   📊 삭제 후 튜터 지역: {tutor_final}개")
            
            # 3. 커밋
            db.commit()
            
            # 4. 결과 요약
            print(f"\n📊 정리 결과 요약:")
            print(f"   👨‍🎓 학생: {student_current} → {student_final}개 ({student_deleted}개 감소)")
            print(f"   👨‍🏫 튜터: {tutor_current} → {tutor_final}개 ({tutor_deleted}개 감소)")
            print(f"   🗑️ 총 삭제: {student_deleted + tutor_deleted}개")
            
            # 5. 샘플 확인
            print(f"\n🔍 정리 후 샘플 확인:")
            
            # 학생 샘플
            student_sample = db.execute(text("""
                SELECT 
                    u.id, u.name,
                    STRING_AGG(
                        CASE 
                            WHEN r.level = '시도' THEN r.name
                            WHEN r.level = '시군구' THEN p.name || ' ' || r.name
                            ELSE r.name
                        END, ', '
                        ORDER BY r.level, r.name
                    ) as regions
                FROM users u
                JOIN student_regions sr ON u.id = sr.user_id
                JOIN regions r ON sr.region_id = r.id
                LEFT JOIN regions p ON r.parent_id = p.id
                WHERE u.role = 'student'
                GROUP BY u.id, u.name
                ORDER BY u.id
                LIMIT 3
            """)).fetchall()
            
            if student_sample:
                print(f"   👨‍🎓 학생 샘플:")
                for user_id, name, regions in student_sample:
                    print(f"      - {name}: {regions}")
            
            # 튜터 샘플
            tutor_sample = db.execute(text("""
                SELECT 
                    u.id, u.name,
                    STRING_AGG(
                        CASE 
                            WHEN r.level = '시도' THEN r.name
                            WHEN r.level = '시군구' THEN p.name || ' ' || r.name
                            ELSE r.name
                        END, ', '
                        ORDER BY r.level, r.name
                    ) as regions
                FROM users u
                JOIN tutor_regions tr ON u.id = tr.tutor_id
                JOIN regions r ON tr.region_id = r.id
                LEFT JOIN regions p ON r.parent_id = p.id
                WHERE u.role = 'tutor'
                GROUP BY u.id, u.name
                ORDER BY u.id
                LIMIT 3
            """)).fetchall()
            
            if tutor_sample:
                print(f"   👨‍🏫 튜터 샘플:")
                for user_id, name, regions in tutor_sample:
                    print(f"      - {name}: {regions}")
            
            # 6. 검증
            print(f"\n🔍 중복 제거 검증:")
            
            # 남은 중복 확인
            remaining_student_duplicates = db.execute(text("""
                SELECT COUNT(*)
                FROM student_regions sr_sido
                JOIN regions sido ON sr_sido.region_id = sido.id
                JOIN student_regions sr_sigungu ON sr_sido.user_id = sr_sigungu.user_id
                JOIN regions sigungu ON sr_sigungu.region_id = sigungu.id
                WHERE sido.level = '시도' 
                  AND sigungu.level = '시군구'
                  AND sigungu.parent_id = sido.id
            """)).scalar()
            
            remaining_tutor_duplicates = db.execute(text("""
                SELECT COUNT(*)
                FROM tutor_regions tr_sido
                JOIN regions sido ON tr_sido.region_id = sido.id
                JOIN tutor_regions tr_sigungu ON tr_sido.tutor_id = tr_sigungu.tutor_id
                JOIN regions sigungu ON tr_sigungu.region_id = sigungu.id
                WHERE sido.level = '시도' 
                  AND sigungu.level = '시군구'
                  AND sigungu.parent_id = sido.id
            """)).scalar()
            
            print(f"   👨‍🎓 남은 학생 중복: {remaining_student_duplicates}개")
            print(f"   👨‍🏫 남은 튜터 중복: {remaining_tutor_duplicates}개")
            
            if remaining_student_duplicates == 0 and remaining_tutor_duplicates == 0:
                print("   ✅ 모든 중복 시도가 성공적으로 제거되었습니다!")
            else:
                print("   ⚠️ 일부 중복이 남아있습니다.")
            
            return student_deleted + tutor_deleted
            
        except Exception as e:
            db.rollback()
            print(f"❌ 중복 시도 제거 중 오류 발생: {str(e)}")
            return 0

def main():
    """메인 실행 함수"""
    
    print("🚀 학생 & 튜터 통합 중복 시도 제거 스크립트")
    print("🎯 목표: 시군구가 있는 경우 상위 시도 제거")
    print("=" * 60)
    
    total_deleted = remove_all_redundant_sido()
    
    print("\n" + "=" * 60)
    
    if total_deleted > 0:
        print("🎉 학생 & 튜터 중복 시도 제거 완료!")
        print(f"📊 총 {total_deleted}개의 중복 시도가 제거되었습니다.")
        print("\n💡 이제 API 응답이 깔끔해집니다:")
        print("   🔍 http://localhost:8000/api/students")
        print("   🔍 http://localhost:8000/api/tutors")
        print("\n✨ 예시 변경:")
        print('   이전: ["서울특별시 강남구", "서울특별시", "부산광역시 해운대구", "부산광역시"]')
        print('   이후: ["서울특별시 강남구", "부산광역시 해운대구"]')
    else:
        print("✅ 제거할 중복 시도가 없거나 오류가 발생했습니다.")

if __name__ == "__main__":
    main()