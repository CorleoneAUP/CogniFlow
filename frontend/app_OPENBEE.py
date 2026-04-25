import streamlit as st
import requests
import json
import time

st.set_page_config(page_title="OPENBEE Ingestion", page_icon="🐝", layout="wide")

# --- STYLE ---
st.markdown("""
    <style>
    .log-container {
        background-color: #0d1117; color: #c9d1d9; padding: 15px; border-radius: 8px;
        font-family: 'Consolas', monospace; height: 400px; overflow-y: auto; border: 1px solid #30363d;
    }
    .log-entry { margin-bottom: 5px; font-size: 0.9rem; border-left: 3px solid #30363d; padding-left: 10px; }
    .log-proc { color: #d29922; border-left-color: #d29922; font-weight: bold; }
    .log-ok { color: #3fb950; border-left-color: #3fb950; }
    .log-warn { color: #f85149; border-left-color: #f85149; }
    </style>
""", unsafe_allow_html=True)

st.title("🐝 OPENBEE : Pilotage Multimodal")

# --- CONFIG ---
if "backend_url" not in st.session_state:
    st.session_state.backend_url = "https://roamer-grouped-muskiness.ngrok-free.dev"

with st.sidebar:
    st.header("⚙️ Paramètres")
    st.session_state.backend_url = st.text_input("URL Backend Ngrok", value=st.session_state.backend_url)
    if st.button("🔌 Vérifier Connexion"):
        try:
            r = requests.get(f"{st.session_state.backend_url}/health", timeout=15)
            st.success("Backend Connecté !")
        except Exception as e:
            st.error(f"Erreur : {e}")

tabs = st.tabs(["📤 Ingestion", "📋 Logs Temps Réel", "📊 Résultats"])

# --- ONGLET 1 : INGESTION ---
with tabs[0]:
    uploaded_files = st.file_uploader("Documents (PDF, Audio, Images)", accept_multiple_files=True)
    if uploaded_files and st.button("🚀 Lancer l'Ingestion", type="primary", use_container_width=True):
        files_payload = []
        meta_payload = []
        for f in uploaded_files:
            name_lower = f.name.lower()
            if f.type == "application/pdf":
                ftype = "pdf"
            elif "audio" in f.type:
                ftype = "audio"
            elif name_lower.endswith((".txt", ".md", ".csv")):
                ftype = "text"
            elif name_lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                ftype = "image"
            else:
                ftype = "text"  # fallback sécurisé
            files_payload.append(("files", (f.name, f.read(), f.type)))
            meta_payload.append({"id": f.name, "type": ftype})
        
        try:
            with st.spinner("Envoi en cours..."):
                resp = requests.post(
                    f"{st.session_state.backend_url}/ingest", 
                    files=files_payload, 
                    data={"metadata": json.dumps(meta_payload)},
                    timeout=30
                )
                st.session_state.task_id = resp.json()["task_id"]
                st.session_state.status = "processing"
                st.success("Tâche envoyée !")
                st.rerun()
        except Exception as e:
            st.error(f"Erreur d'envoi : {e}")

# --- ONGLET 2 : LOGS ---
with tabs[1]:
    if "task_id" in st.session_state:
        st.subheader(f"Suivi : {st.session_state.task_id}")
        
        try:
            # Timeout plus long pour le polling car le backend est sollicité
            r = requests.get(f"{st.session_state.backend_url}/status/{st.session_state.task_id}", timeout=10)
            data = r.json()
            st.session_state.status = data.get("status", "unknown")
            
            # Affichage des logs
            log_html = '<div class="log-container">'
            for l in data.get("logs", []):
                cls = f"log-{l['level']}"
                log_html += f'<div class="log-entry {cls}">[{l["ts"]}] {l["msg"]}</div>'
            log_html += '</div>'
            st.markdown(log_html, unsafe_allow_html=True)
            
            if st.session_state.status in ["processing", "queued"]:
                time.sleep(2)
                st.rerun()
            elif st.session_state.status == "completed":
                st.balloons()
                st.success("Analyse terminée !")
                st.session_state.result = data.get("result")
        except Exception as e:
            st.warning(f"Reconnexion au flux de logs... ({e})")
            time.sleep(3)
            st.rerun()
    else:
        st.info("Aucun traitement en cours.")

# --- ONGLET 3 : RÉSULTATS ---
with tabs[2]:
    if "result" in st.session_state and st.session_state.result:
        res = st.session_state.result
        workflow = res.get("workflow", {})

        if workflow.get("parse_error"):
            st.warning("⚠️ Le JSON n'a pas pu être parsé. Voici la réponse brute du modèle :")
            st.text(workflow.get("raw", ""))
        else:
            # Résumé rapide
            n_actors = len(workflow.get("actors", []))
            n_nodes  = len(workflow.get("nodes", []))
            n_edges  = len(workflow.get("edges", []))
            c1, c2, c3 = st.columns(3)
            c1.metric("👥 Acteurs", n_actors)
            c2.metric("🔲 Nœuds",  n_nodes)
            c3.metric("➡️ Edges",  n_edges)

            st.divider()

            # JSON BPMN complet
            st.subheader("🐝 JSON Workflow BPMN")
            st.json(workflow)

            # Téléchargement JSON
            st.download_button(
                label="⬇️ Télécharger le JSON Workflow",
                data=json.dumps(workflow, ensure_ascii=False, indent=2),
                file_name="workflow_bpmn.json",
                mime="application/json"
            )

            st.divider()

            # ─── BOUTONS DE GÉNÉRATION ──────────────────────────────────────
            st.subheader("🚀 Actions")
            col_btn1, col_btn2 = st.columns(2)

            # ── Bouton 1 : Diagrammes via Cerebras ──────────────────────────
            with col_btn1:
                if st.button("🔲 Générer les Diagrammes (Cerebras)", use_container_width=True, type="primary"):
                    try:
                        from generate_workflow_cerebras import main as cerebras_main
                        with st.spinner("⚙️ Génération des diagrammes en cours (Cerebras)..."):
                            agent_result = cerebras_main(workflow)
                        st.success("✅ Diagrammes générés !")

                        # Téléchargements
                        if agent_result.html_content:
                            st.download_button(
                                "⬇️ Télécharger le Diagramme HTML",
                                data=agent_result.html_content,
                                file_name="workflow.html",
                                mime="text/html"
                            )
                        if agent_result.mermaid_def:
                            st.download_button(
                                "⬇️ Télécharger Mermaid (.mmd)",
                                data=agent_result.mermaid_def,
                                file_name="workflow.mmd",
                                mime="text/plain"
                            )
                        if agent_result.graphviz_def:
                            st.download_button(
                                "⬇️ Télécharger Graphviz (.dot)",
                                data=agent_result.graphviz_def,
                                file_name="workflow.dot",
                                mime="text/plain"
                            )
                        if agent_result.summary:
                            with st.expander("📋 Résumé de l'agent Cerebras"):
                                st.markdown(agent_result.summary)
                    except ImportError:
                        st.error("❌ Module 'cerebras' non installé. Lance : pip install cerebras-cloud-sdk")
                    except EnvironmentError as e:
                        st.error(f"❌ {e}\nDéfinis la variable : CEREBRAS_API_KEY=ta_cle")
                    except Exception as e:
                        st.error(f"❌ Erreur : {e}")

            # ── Bouton 2 : Création automatique dans OpenBEE ─────────────────
            with col_btn2:
                if st.button("🌐 Créer le Workflow dans OpenBEE", use_container_width=True):
                    try:
                        from generate_workflow_openbee import main as openbee_main
                        with st.spinner("🤖 L'agent navigue dans OpenBEE... (peut prendre 2-5 min)"):
                            result_text = openbee_main(workflow)
                        st.success("✅ Workflow créé dans OpenBEE !")
                        with st.expander("📋 Résultat de l'agent"):
                            st.text(result_text)
                    except ImportError:
                        st.error("❌ Module 'browser_use' non installé. Lance : pip install browser-use")
                    except Exception as e:
                        st.error(f"❌ Erreur : {e}")

        st.divider()

        # Données brutes dans un expander
        with st.expander("📄 Données Brutes Extraites (OCR / Transcriptions)", expanded=False):
            st.markdown(res.get("context", ""))
    else:
        st.info("Les résultats s'afficheront ici après une ingestion.")
