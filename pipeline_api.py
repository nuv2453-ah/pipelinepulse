import requests
import base64
from flask import Flask, request, jsonify
from google import genai

# ── Config ────────────────────────────────────────────────────────────────────
FIVETRAN_API_KEY    = "lVaG9INThhDVc9nu"
FIVETRAN_API_SECRET = "PD6XnXlTIqXBRUKlOF7ufkXZc0dakbAN"
GEMINI_API_KEY      = "AIzaSyBBpEzHB7HCzTlUyCj1xJPo31pCrI9NwIE"  # ← paste your PipelinePulse key

# ── Gemini client ─────────────────────────────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)

# ── Fivetran ──────────────────────────────────────────────────────────────────
def get_fivetran_connectors():
    credentials = base64.b64encode(
        f"{FIVETRAN_API_KEY}:{FIVETRAN_API_SECRET}".encode()
    ).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json"
    }
    response = requests.get(
        "https://api.fivetran.com/v1/connectors",
        headers=headers
    )
    return response.json()

def analyze_pipelines(connector_data):
    connectors = connector_data.get("data", {}).get("items", [])
    if not connectors:
        return "No connectors found in your Fivetran account."

    healthy, failed, summary = [], [], []
    for c in connectors:
        name       = c.get("schema", c.get("id", "Unknown"))
        service    = c.get("service", "unknown source")
        sync_state = c.get("status", {}).get("sync_state", "unknown")
        last_sync  = c.get("succeeded_at") or c.get("failed_at") or "Never"

        if sync_state in ("synced", "syncing"):
            healthy.append(name)
            summary.append(f"- {name} ({service}): healthy, last synced {last_sync}")
        else:
            failed.append(name)
            summary.append(f"- {name} ({service}): {sync_state}, last sync {last_sync}")

    overview = f"{len(healthy)} of {len(connectors)} connectors healthy, {len(failed)} need attention."
    return overview + "\n" + "\n".join(summary)

def ask_pipeline_pulse(question, pipeline_summary):
    prompt = f"""
You are PipelinePulse, a friendly AI data pipeline health advisor for non-technical business users.

Here is the current status of the user's Fivetran data pipelines:
{pipeline_summary}

User question: {question}

Answer in plain English with no technical jargon. Be concise, friendly, and actionable.
If pipelines have failed, explain what that means for the business and suggest next steps.
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "PipelinePulse API is running!"})

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "What is the status of all my pipelines?")

    try:
        connector_data   = get_fivetran_connectors()
        pipeline_summary = analyze_pipelines(connector_data)
        answer           = ask_pipeline_pulse(question, pipeline_summary)
        return jsonify({"answer": answer, "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

@app.route("/status", methods=["GET"])
def status():
    try:
        connector_data   = get_fivetran_connectors()
        pipeline_summary = analyze_pipelines(connector_data)
        return jsonify({"summary": pipeline_summary, "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
