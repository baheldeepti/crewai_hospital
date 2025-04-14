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
import gradio as gr
import requests
import pandas as pd
import os
from reportlab.pdfgen import canvas
from datetime import datetime

API_URL = "http://localhost:8000/ask"
LOG_FILE = "qa_log.csv"

# Ask and log response
def ask_ai(question):
    response = requests.post(API_URL, json={"question": question}).json()
    return response.get("answer"), response.get("chart_base64")

# View logs
def view_logs():
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=["timestamp", "question", "answer"])
    return pd.read_csv(LOG_FILE)

# Export to Excel
def export_excel():
    df = view_logs()
    file_path = f"qa_logs_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    df.to_excel(file_path, index=False)
    return file_path

# Export to PDF
def export_pdf():
    df = view_logs()
    file_path = f"qa_logs_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    c = canvas.Canvas(file_path)
    c.drawString(100, 800, "Hospital Q&A Logs")
    y = 780
    for index, row in df.iterrows():
        c.drawString(50, y, f"{row['timestamp'][:19]} - Q: {row['question']} | A: {row['answer'][:60]}...")
        y -= 20
        if y < 50:
            c.showPage()
            y = 800
    c.save()
    return file_path

qa_tab = gr.Interface(
    fn=ask_ai,
    inputs=gr.Textbox(label="Ask your hospital data question"),
    outputs=[
        gr.Textbox(label="Answer"),
        gr.Image(label="Chart (if available)", type="pil")
    ],
    title="🏥 Hospital AI Assistant",
    description="Ask questions about hospital performance, billing, admissions, and more!"
)

log_tab = gr.Interface(
    fn=view_logs,
    inputs=[],
    outputs=gr.Dataframe(label="Conversation Logs", interactive=True),
    title="📜 View Logs",
    description="See all your previous questions and answers."
)

export_excel_btn = gr.Button("📤 Export Logs to Excel")
export_pdf_btn = gr.Button("🧾 Export Logs to PDF")

with gr.Blocks() as full_ui:
    with gr.Tab("Chat Assistant"):
        qa_tab.render()
    with gr.Tab("View Logs"):
        log_tab.render()
        export_excel_btn.click(fn=export_excel, inputs=[], outputs=[gr.File(label="Download Excel")])
        export_pdf_btn.click(fn=export_pdf, inputs=[], outputs=[gr.File(label="Download PDF")])

if __name__ == "__main__":
    full_ui.launch()
