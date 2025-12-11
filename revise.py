@app.patch("/resume/block/{block_id}", status_code=200)
def update_resume_block(
    block_id: int,
    req: ResumeBlockUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    이력서 블록 수정
    """

    try:
        # 1) 블록 존재 여부 확인 + tutor_id 가져오기
        block = db.execute(text("""
            SELECT id, tutor_id
            FROM resume_blocks
            WHERE id = :bid
        """), {"bid": block_id}).fetchone()

        if not block:
            raise HTTPException(404, "BLOCK_NOT_FOUND")

        tutor_id = block.tutor_id

        # 3) 업데이트할 필드만 동적으로 생성
        update_fields = []
        params = {"block_id": block_id}

        if req.title is not None:
            update_fields.append("title = :title")
            params["title"] = req.title

        if req.period is not None:
            update_fields.append("period = :period")
            params["period"] = req.period

        if req.role is not None:
            update_fields.append("role = :role")
            params["role"] = req.role

        if req.description is not None:
            update_fields.append("description = :description")
            params["description"] = req.description

        if req.tech_stack is not None:
            update_fields.append("tech_stack = :tech_stack")
            params["tech_stack"] = req.tech_stack

        if req.issuer is not None:
            update_fields.append("issuer = :issuer")
            params["issuer"] = req.issuer

        if req.acquired_at is not None:
            update_fields.append("acquired_at = :acquired_at")
            params["acquired_at"] = req.acquired_at

        if req.file_url is not None:
            update_fields.append("file_url = :file_url")
            params["file_url"] = req.file_url

        if req.link_url is not None:
            update_fields.append("link_url = :link_url")
            params["link_url"] = req.link_url

        # 업데이트할 필드가 없다면 실행하지 않음
        if update_fields:
            db.execute(text(f"""
                UPDATE resume_blocks
                SET {', '.join(update_fields)}
                WHERE id = :block_id
            """), params)

        db.commit()

        return {"message": "UPDATED"}

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"INTERNAL_SERVER_ERROR: {str(e)}")
