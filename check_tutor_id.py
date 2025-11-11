#!/usr/bin/env python3
"""
존재하는 튜터 ID를 확인하는 스크립트
"""

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

def check_existing_tutors():
    """존재하는 튜터들 확인"""
    
    with engine.connect() as conn:
        print("🔍 존재하는 튜터 ID 확인")
        
        # 1. 전체 튜터 수
        total_tutors = conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'tutor'")).scalar()
        print(f"📊 전체 튜터 수: {total_tutors}명")
        
        # 2. 튜터 ID 범위
        id_range = conn.execute(text("""
            SELECT MIN(id) as min_id, MAX(id) as max_id 
            FROM users WHERE role = 'tutor'
        """)).fetchone()
        
        if id_range[0]:
            print(f"📊 튜터 ID 범위: {id_range[0]} ~ {id_range[1]}")
        
        # 3. 처음 10명의 튜터 ID
        print(f"\n✅ 존재하는 튜터 ID (처음 10명):")
        tutors = conn.execute(text("""
            SELECT id, name, email 
            FROM users 
            WHERE role = 'tutor' 
            ORDER BY id 
            LIMIT 10
        """)).fetchall()
        
        if tutors:
            for tutor in tutors:
                print(f"   👨‍🏫 ID: {tutor[0]} - {tutor[1]} ({tutor[2]})")
        else:
            print("   ❌ 튜터가 없습니다!")
        
        # 4. API 테스트 가능한 ID 제안
        if tutors:
            print(f"\n💡 API 테스트용 추천 ID:")
            print(f"   http://localhost:8000/api/tutors/{tutors[0][0]}")
            if len(tutors) > 1:
                print(f"   http://localhost:8000/api/tutors/{tutors[1][0]}")

if __name__ == "__main__":
    check_existing_tutors()