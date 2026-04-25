"""
generate_workflow_openbee.py
Automatise la création du workflow dans OpenBEE Portal
via un agent browser-use + Groq (Llama4 Scout).
"""
import asyncio
from browser_use import Agent, Browser
from browser_use.llm import ChatGroq

# ── Configuration OpenBEE ─────────────────────────────────────────────────────
OPENBEE_URL   = "https://myetch.openbeedemo.com"
USERNAME      = "Corleone"
PASSWORD      = "Openbee1234!"
WORKFLOW_NAME = "Generated Workflow"

LLM = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
)


# ── Build task prompt ─────────────────────────────────────────────────────────
def build_task(workflow: dict) -> str:
    nodes  = workflow["nodes"]
    edges  = workflow["edges"]
    actors = list(dict.fromkeys(n["actor"] for n in nodes))

    node_lines = "\n".join(
        f"  - ID={n['id']}  shape={n['shape']}  actor=\"{n['actor']}\"  label=\"{n['text']}\""
        for n in nodes
    )
    edge_lines = "\n".join(
        f"  - {e['from']} → {e['to']}" + (f"  [label: {e['label']}]" if e["label"] else "")
        for e in edges
    )
    actor_lines = "\n".join(f"  - {a}" for a in actors)

    return f"""
You are automating the creation of a workflow inside the OpenBee Portal application.

## Step 1 — Log in
Go to: {OPENBEE_URL}
Username: {USERNAME}
Password: {PASSWORD}

Wait for the application to fully load (the loading spinner disappears and the main navigation is visible).

## Step 2 — Navigate to the workflow designer
Find the "Workflow" or "Workflows" section in the administration menu and open it.
Then create a new workflow named: "{WORKFLOW_NAME}"

## Step 3 — Create swimlanes / actor lanes
The workflow has {len(actors)} actors. Create one swimlane for each:
{actor_lines}

## Step 4 — Add nodes
Add each node below to the canvas. Place each node in the swimlane that matches its actor.
Use the correct shape:
  - Rectangle = task or activity
  - Diamond   = decision or gateway
  - Oval      = start or end event

{node_lines}

## Step 5 — Draw connections
Connect the nodes with arrows exactly as listed. Where a label is shown (OUI / NON),
set that label on the arrow after drawing it.

{edge_lines}

## Step 6 — Save
Save or publish the workflow. Confirm it is saved successfully.

## Important rules
- Wait for the UI to respond after each action before moving on.
- Handle any dialog or popup that appears before continuing.
- Do NOT skip any node or connection.
- If placing nodes requires drag-and-drop, drag the correct shape onto the canvas.
- After placing each node, set its label and assign it to the correct actor lane.
"""


# ── Run ───────────────────────────────────────────────────────────────────────
async def _run_async(workflow: dict) -> str:
    task    = build_task(workflow)
    browser = Browser()
    agent   = Agent(
        task=task,
        llm=LLM,
        browser=browser,
        max_actions_per_step=5,
        max_failures=3,
    )
    result = await agent.run(max_steps=120)
    return str(result)


def main(workflow: dict) -> str:
    """
    Synchronous entry point callable from Streamlit.
    Lance l'agent dans un thread dédié avec son propre event loop
    pour éviter le conflit Windows asyncio + Streamlit.
    """
    import threading
    import sys

    result_box: list[str] = []
    error_box:  list[Exception] = []

    def run_in_thread():
        # Sur Windows, forcer ProactorEventLoop pour subprocess support
        if sys.platform == "win32":
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            outcome = loop.run_until_complete(_run_async(workflow))
            result_box.append(str(outcome))
        except Exception as exc:
            error_box.append(exc)
        finally:
            loop.close()

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    thread.join(timeout=600)  # 10 min max

    if not thread.is_alive() and error_box:
        raise error_box[0]
    if thread.is_alive():
        return "⏳ Timeout : l'agent a dépassé 10 minutes."
    return result_box[0] if result_box else "✅ Agent terminé (pas de résultat textuel)."


if __name__ == "__main__":
    import json, pathlib
    sample = json.loads(pathlib.Path("workflow_bpmn.json").read_text())
    print(main(sample))
