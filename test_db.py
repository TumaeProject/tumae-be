# test_db.py 파일을 다음 내용으로 교체
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def test_postgresql():
    """PostgreSQL 직접 연결 테스트"""
    
    # .env 파일에서 DATABASE_URL 읽기
    from dotenv import load_dotenv
    load_dotenv()
    
    # 환경 변수에서 DATABASE_URL 가져오기
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost/coding_tutor_db')
    
    print("🔍 PostgreSQL 연결 테스트 시작...")
    print(f"📋 연결 정보: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    
    try:
        # 엔진 생성
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # 연결 테스트
        with SessionLocal() as db:
            result = db.execute(text("SELECT 1"))
            print("✅ PostgreSQL 연결 성공!")
            
            # 버전 확인
            result = db.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"📊 PostgreSQL 버전: {version[:80]}...")
            
            # 데이터베이스 이름 확인
            result = db.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"📁 현재 데이터베이스: {db_name}")
            
            # 테이블 목록 확인
            result = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()
            
            print(f"\n📋 테이블 개수: {len(tables)}개")
            if tables:
                print("📄 기존 테이블들:")
                for table in tables:
                    print(f"   - {table[0]}")
            else:
                print("⚠️  테이블이 없습니다. 스키마 생성이 필요합니다.")
                
            return True
            
    except Exception as e:
        print(f"❌ 연결 실패: {str(e)}")
        print("\n💡 가능한 해결책:")
        print("1. PostgreSQL 서비스 실행 확인")
        print("2. .env 파일의 사용자명/비밀번호 확인")
        print("3. 데이터베이스 'coding_tutor_db' 생성 확인")
        return False

if __name__ == "__main__":
    # python-dotenv 설치 확인
    try:
        import dotenv
    except ImportError:
        print("📦 python-dotenv 설치 중...")
        os.system("pip install python-dotenv")
        import dotenv
    
    test_postgresql()