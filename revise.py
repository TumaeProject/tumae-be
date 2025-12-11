# ==========================================================
# 📝 이력서 블록 추가 API (수정 버전)
# ==========================================================

VALID_BLOCK_TYPES = ["career", "project", "certificate", "portfolio"]

# 블록 타입별 허용/사용 필드 정의
BLOCK_FIELDS = {
    "career": ["title", "period", "role", "description", "tech_stack"],
    "project": ["title", "period", "role", "description", "tech_stack", "link_url"],
    "certificate": ["title", "issuer", "acquired_at", "file_url"],
    "portfolio": ["title", "description", "tech_stack", "file_url", "link_url"]
}

@app.post("/resume/{tutor_id}", status_code=201)
def create_resume_block(
    tutor_id: int,
    req: ResumeBlockCreateRequest = Depends(),
    db: Session = Depends(get_db)
):
    """튜터 이력서 블록 추가 (경력/프로젝트/자격증/포트폴리오)"""

    try:
        # -----------------------------
        # 1) tutor_id 검증
        # -----------------------------
        user = db.execute(
            text("SELECT id, role FROM users WHERE id = :uid"),
            {"uid": tutor_id}
        ).fetchone()

        if not user or user.role != "tutor":
            raise HTTPException(404, "TUTOR_NOT_FOUND")

        # -----------------------------
        # 2) block_type 검증
        # -----------------------------
        if req.block_type not in VALID_BLOCK_TYPES:
            raise HTTPException(400, "INVALID_BLOCK_TYPE")

        allowed_fields = BLOCK_FIELDS[req.block_type]

        # -----------------------------
        # 3) 필드 필터링 (허용되지 않은 필드 자동 NULL 처리)
        # -----------------------------
        insert_data = {
            "tutor_id": tutor_id,
            "block_type": req.block_type,
            "title": req.title if "title" in allowed_fields else None,
            "period": req.period if "period" in allowed_fields else None,
            "role": req.role if "role" in allowed_fields else None,
            "description": req.description if "description" in allowed_fields else None,
            "tech_stack": req.tech_stack if "tech_stack" in allowed_fields else None,
            "issuer": req.issuer if "issuer" in allowed_fields else None,
            "acquired_at": req.acquired_at if "acquired_at" in allowed_fields else None,
            "file_url": req.file_url if "file_url" in allowed_fields else None,
            "link_url": req.link_url if "link_url" in allowed_fields else None,
        }

        # -----------------------------
        # 4) 필수 필드 누락 검증
        # -----------------------------
        required = ["title"]  # 모든 블록 공통 필수
        for field in required:
            if field not in allowed_fields:
                continue
            if insert_data[field] is None:
                raise HTTPException(400, f"MISSING_REQUIRED_FIELD: {field}")

        # -----------------------------
        # 5) DB Insert
        # -----------------------------
        result = db.execute(text("""
            INSERT INTO resume_blocks (
                tutor_id, block_type, title, period, role, description,
                tech_stack, issuer, acquired_at, file_url, link_url, created_at
            )
            VALUES (
                :tutor_id, :block_type, :title, :period, :role, :description,
                :tech_stack, :issuer, :acquired_at, :file_url, :link_url, NOW()
            )
            RETURNING id
        """), insert_data)

        new_block = result.fetchone()
        db.commit()

        return {
            "message": "SUCCESS",
            "block_id": new_block.id
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"이력서 블록 추가 중 오류: {str(e)}")

# ==========================================================
# 🗑️ 이력서 블록 삭제 API
# ==========================================================

@app.delete("/resume/block/{block_id}", status_code=200)
def delete_resume_block(
    block_id: int = Path(..., description="삭제할 블록 ID"),
    current_user_id: int = Query(..., description="현재 로그인한 사용자 ID"),
    db: Session = Depends(get_db)
):
    """
    이력서 블록 삭제 (튜터 본인만 가능)
    """

    try:
        # 1️⃣ 블록 존재 여부 확인
        block = db.execute(text("""
            SELECT id, tutor_id 
            FROM resume_blocks 
            WHERE id = :block_id
        """), {"block_id": block_id}).fetchone()

        if not block:
            raise HTTPException(404, "RESUME_BLOCK_NOT_FOUND")

        tutor_id = block.tutor_id

        # 2️⃣ 삭제 권한 확인 — 본인만 삭제 가능
        if tutor_id != current_user_id:
            raise HTTPException(403, "NO_PERMISSION")

        # 3️⃣ 블록 삭제
        db.execute(text("""
            DELETE FROM resume_blocks 
            WHERE id = :block_id
        """), {"block_id": block_id})

        db.commit()

        return {
            "message": "SUCCESS",
            "status_code": 200,
            "data": {
                "deleted_block_id": block_id
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"INTERNAL_SERVER_ERROR: {str(e)}")
