from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "difyai123456",
    "database": "jobsdb"
}

BLOCKED = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE
)

class QueryRequest(BaseModel):
    sql: str

class ApplicationRequest(BaseModel):
    company: str
    position: str
    applied_date: str | None = None
    location: str | None = None
    link: str | None = None
    feedback: str | None = None
    work_type: str | None = None

@app.post("/applications")
def add_application(req: ApplicationRequest):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO job_applications (company, position, applied_date, location, link, feedback, work_type)
            VALUES (%s, %s, %s::date, %s, %s, %s, %s)
        """, (
            req.company,
            req.position,
            req.applied_date or None,
            req.location,
            req.link,
            req.feedback,
            req.work_type,
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def run_query(req: QueryRequest):
    if BLOCKED.search(req.sql):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(req.sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"result": [dict(r) for r in rows], "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/applications")
def get_applications():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, company, position, applied_date, location, link, feedback, work_type
        FROM job_applications
        ORDER BY applied_date DESC NULLS LAST, id DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    for r in rows:
        if r['applied_date']:
            r['applied_date'] = r['applied_date'].isoformat()
    return rows

@app.put("/applications/{app_id}")
def update_application(app_id: int, req: ApplicationRequest):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            UPDATE job_applications
            SET company=%s, position=%s, applied_date=%s::date,
                location=%s, link=%s, feedback=%s, work_type=%s
            WHERE id=%s
        """, (
            req.company, req.position, req.applied_date or None,
            req.location, req.link, req.feedback, req.work_type, app_id
        ))
        conn.commit()
        cur.close(); conn.close()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/stats/countries")
def stats_countries():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT location, COUNT(*) as count
        FROM job_applications
        WHERE location IS NOT NULL AND location != 'NaN'
        GROUP BY location ORDER BY count DESC LIMIT 10
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

@app.get("/stats/worktype")
def stats_worktype():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE work_type = 'Remote') as remote,
            COUNT(*) FILTER (WHERE work_type = 'Onsite') as onsite,
            COUNT(*) FILTER (WHERE work_type IS NULL OR work_type NOT IN ('Remote','Onsite')) as unspecified
        FROM job_applications
    """)
    row = dict(cur.fetchone())
    cur.close(); conn.close()
    return row

@app.get("/stats/feedback")
def stats_feedback():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE feedback IS NULL) as pending,
            COUNT(*) FILTER (WHERE feedback = 'Fail') as rejected
        FROM job_applications
    """)
    row = dict(cur.fetchone())
    cur.close(); conn.close()
    return row

@app.get("/stats/monthly")
def stats_monthly():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT applied_date as month, COUNT(*) as count
        FROM job_applications
        WHERE applied_date IS NOT NULL
        GROUP BY applied_date ORDER BY applied_date
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

@app.get("/stats/summary")
def stats_summary():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE feedback IS NULL) as pending,
            COUNT(DISTINCT location) as countries
        FROM job_applications
    """)
    row = dict(cur.fetchone())
    cur.close(); conn.close()
    return row
