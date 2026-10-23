with open('C:/Users/shashank/edtech-review-engine/portal/server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = """@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(file_path, filename=filename)"""

addition = """

@app.get("/download/docx/{job_id}")
async def download_docx_by_job_id(job_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT docx_filename FROM submissions WHERE job_id = ?", (job_id,)).fetchone()
    if not row or not row["docx_filename"]:
        raise HTTPException(status_code=404, detail="Document not found for this job ID")
    file_path = OUTPUT_DIR / row["docx_filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing from output directory")
    return FileResponse(file_path, filename=row["docx_filename"])


@app.get("/download/report/{job_id}")
async def download_report_by_job_id(job_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT html_filename FROM submissions WHERE job_id = ?", (job_id,)).fetchone()
    if not row or not row["html_filename"]:
        raise HTTPException(status_code=404, detail="Report not found for this job ID")
    file_path = OUTPUT_DIR / row["html_filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file missing from output directory")
    return FileResponse(file_path, filename=row["html_filename"])"""

if target in text:
    text = text.replace(target, target + addition, 1)
    with open('C:/Users/shashank/edtech-review-engine/portal/server.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Added /download/docx/{job_id} and /download/report/{job_id}")
else:
    print("Target not found!")
