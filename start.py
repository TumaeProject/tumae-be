# start.py 파일 내용
#!/usr/bin/env python3
"""
개발 서버 실행 스크립트
"""
import uvicorn
import sys
import os

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 코딩 과외 매칭 API 서버를 시작합니다...")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🔧 ReDoc: http://localhost:8000/redoc")
    print("⭐ 메인 페이지: http://localhost:8000/")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        log_level="info"
    )