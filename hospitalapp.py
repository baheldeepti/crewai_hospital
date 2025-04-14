# 📁 hospital_ai_agent - AI Assistant for Hospital Analytics using CrewAI

# 👉 File: requirements.txt
'''
fastapi
uvicorn
crewai
langchain
openai
pandas
matplotlib
gradio
python-dotenv
langchainhub
langchain-memory
openpyxl
gspread
oauth2client
reportlab
'''

# 👉 File: .env (create this file and keep your OpenAI key here)
'''
OPENAI_API_KEY=your-openai-key-here
GOOGLE_SERVICE_ACCOUNT_JSON=your-service-account.json
GOOGLE_SHEET_NAME=HospitalQALog
'''

# 👉 File: .gitignore
'''
.env
__pycache__/
*.pyc
*.pyo
*.pyd
*.db
*.sqlite3
*.log
*.xlsx
*.pdf
qa_log.csv
hospital_data.csv
your-service-account.json
'''

# 👉 File: render.yaml
'''
services:
  - type: web
    name: hospital-ai-app
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python gradio_ui.py
    envVars:
      - key: OPENAI_API_KEY
        sync: true
      - key: GOOGLE_SHEET_NAME
        value: HospitalQALog
      - key: GOOGLE_SERVICE_ACCOUNT_JSON
        value: /etc/secrets/service-account.json
    secretFiles:
      - source: your-service-account.json
        destination: /etc/secrets/service-account.json
'''

# 👉 File: main.py
import os
import pandas as pd
import csv
from datetime import datetime
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from crew import create_hospital_crew
from agents.chart_agent import ChartAgent
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

app = FastAPI()
df = pd.read_csv("hospital_data.csv")
chart_generator = ChartAgent()
LOG_FILE = "qa_log.csv"

# Ensure CSV has headers
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "question", "answer"])

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
json_keyfile = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
if json_keyfile and os.path.exists(json_keyfile):
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)
    sheet_client = gspread.authorize(creds)
    sheet_name = os.getenv("GOOGLE_SHEET_NAME", "HospitalQALog")
    try:
        sheet = sheet_client.open(sheet_name).sheet1
    except:
        sheet = sheet_client.create(sheet_name).sheet1
        sheet.append_row(["timestamp", "question", "answer"])
else:
    sheet = None

@app.get("/")
def home():
    return {"message": "Hospital AI Agent is ready. Use POST /ask with your question."}

@app.post("/ask")
async def ask_question(request: Request):
    data = await request.json()
    question = data.get("question")
    crew = create_hospital_crew(df)
    result = crew.run({"question": question})
    chart_img = chart_generator.generate_chart(df, x_col='Hospital Name', y_col='Billing Amount')

    timestamp = datetime.now().isoformat()
    with open(LOG_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, question, result])

    if sheet:
        sheet.append_row([timestamp, question, result])

    return {"answer": result, "chart_base64": chart_img}

# 👉 File: gradio_ui.py
... (no changes needed to gradio_ui.py section)
