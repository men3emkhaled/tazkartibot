import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
c = conn.cursor()
c.execute("SELECT match_id, team1_ar, team2_ar, last_status FROM match_status_tracker;")
rows = c.fetchall()
for row in rows:
    print(row)
c.close()
conn.close()
