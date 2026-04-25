from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
import re

app = FastAPI()

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
        GROUP BY location ORDER BY count DESC LIMIT 8
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows

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
