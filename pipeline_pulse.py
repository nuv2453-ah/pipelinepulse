from dotenv import load_dotenv
import os

load_dotenv()
FIVETRAN_API_KEY = os.getenv("FIVETRAN_API_KEY")
FIVETRAN_API_SECRET = os.getenv("FIVETRAN_API_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

import requests
import base64
from google import genai

# ── Config ────────────────────────────────────────────────────────────────────

# ── Gemini client ─────────────────────────────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)

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
        name      = c.get("schema", c.get("id", "Unknown"))
        service   = c.get("service", "unknown source")
        sync_state = c.get("status", {}).get("sync_state", "unknown")
        last_sync  = c.get("succeeded_at") or c.get("failed_at") or "Never"
        failure_reason = c.get("status", {}).get("tasks", [{}])[0].get("message", "") if sync_state == "failed" else ""

        if sync_state in ("synced", "syncing"):
            healthy.append(name)
            summary.append(f"- {name} ({service}): ✅ healthy, last synced {last_sync}")
        else:
            failed.append(name)
            summary.append(f"- {name} ({service}): ❌ {sync_state}, last sync {last_sync}. {failure_reason}".strip())

    overview = f"{len(healthy)} of {len(connectors)} connectors healthy, {len(failed)} need attention."
    return overview + "\n" + "\n".join(summary)

# ── Gemini ────────────────────────────────────────────────────────────────────
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

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    print("\n🚀 Welcome to PipelinePulse!")
    print("Your AI-powered data pipeline health advisor.")
    print("Type 'quit' to exit.\n")

    print("Fetching your pipeline data from Fivetran...")
    try:
        connector_data = get_fivetran_connectors()
        pipeline_summary = analyze_pipelines(connector_data)
        print("✅ Pipeline data loaded!\n")
    except Exception as e:
        print(f"❌ Could not fetch Fivetran data: {e}")
        return

    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit"):
            print("Goodbye!")
            break
        if not question:
            continue
        try:
            response = ask_pipeline_pulse(question, pipeline_summary)
            print(f"\nPipelinePulse: {response}\n")
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    main()
