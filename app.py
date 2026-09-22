import streamlit as st
import json
import re

st.set_page_config(page_title="AI Presidential Studio", layout="wide", initial_sidebar_state="collapsed")

# --- LOAD CHARACTER BIBLE ---
@st.cache_data
def load_bible():
    try:
        with open("character_bible.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"GLOBAL_RECURRING": {}, "PRESIDENTS": {}}

bible_data = load_bible()
global_recurring = bible_data.get("GLOBAL_RECURRING", {})
presidents = bible_data.get("PRESIDENTS", {})

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Global Settings")
    global_aspect_ratio = st.selectbox("Aspect Ratio", ["16:9 (Landscape)", "9:16 (Shorts)", "1:1 (Square)"], index=0)
    global_duration = st.selectbox("Default Scene Duration", [10, 5], index=0)
    global_negative = st.text_area(
        "Negative Prompt",
        "3d render, photorealistic, modern items, distorted face, extra limbs, bad anatomy, low resolution, subtitles, watermarks"
    )

# --- TOP BAR: PRESIDENT SELECTION ---
st.title("🏛️ Presidential Video Studio")
st.caption("10-Second Scene Controller & Parameter Engine")

col_p1, col_p2 = st.columns([1, 2])
with col_p1:
    pres_num = st.selectbox("Select President Episode", range(1, 57), index=4)  # Defaults to #5 (Monroe)
with col_p2:
    pres_info = presidents.get(str(pres_num), {"name": f"President #{pres_num}", "prompt_anchor": "", "youth_anchor": ""})
    st.info(f"Active Subject: **President #{pres_num} — {pres_info['name']}**")

# --- MATCHING LOGIC ---
def match_entities(text, pres_data):
    anchors = []
    for key, data in global_recurring.items():
        for alias in data.get("aliases", []):
            if re.search(r"\b" + re.escape(alias) + r"\b", text, re.IGNORECASE):
                anchors.append(f"[{key}]: {data['prompt_anchor']}")
                break

    text_lower = text.lower()
    if any(k in text_lower for k in ["youth", "young", "18-year-old", "teenager", "student"]):
        if pres_data.get("youth_anchor"):
            anchors.append(f"[{pres_data['name'].upper()}_YOUTH]: {pres_data['youth_anchor']}")
        else:
            anchors.append(f"[{pres_data['name'].upper()}]: {pres_data.get('prompt_anchor', '')}")
    else:
        for alias in pres_data.get("aliases", [pres_data.get("name", "")]):
            if re.search(r"\b" + re.escape(alias) + r"\b", text, re.IGNORECASE):
                anchors.append(f"[{pres_data['name'].upper()}]: {pres_data.get('prompt_anchor', '')}")
                break

    return anchors

# --- SCRIPT PARSER ---
def parse_scenes(text, pres_data):
    scene_pattern = re.compile(r"(?i)(?:^|\n)\s*(?:🎬\s*)?SCENE\s*(\d+)[^\n]*\n?")
    splits = scene_pattern.split(text)
    scenes = []

    if len(splits) > 1:
        for i in range(1, len(splits), 2):
            num = int(splits[i])
            block = splits[i+1].strip()

            narr = re.search(r"(?i)NARRATION\s*\n+([^\n]+(?:\n[^\n]+)*?)(?=\n+[A-Z\s]{4,}|\Z)", block)
            vis = re.search(r"(?i)VISUAL\s*\n+([^\n]+(?:\n[^\n]+)*?)(?=\n+[A-Z\s]{4,}|\Z)", block)
            cont = re.search(r"(?i)CONTINUITY\s*\n+([^\n]+(?:\n[^\n]+)*?)(?=\n+[A-Z\s]{4,}|\Z)", block)

            narr_text = narr.group(1).replace('“', '').replace('”', '').strip() if narr else ""
            vis_text = vis.group(1).strip() if vis else ""
            cont_text = cont.group(1).strip() if cont else ""

            detected = match_entities(f"{vis_text} {narr_text}", pres_data)

            scenes.append({
                "index": num,
                "narration": narr_text,
                "visual": vis_text,
                "continuity": cont_text,
                "characters": detected
            })

    scenes.sort(key=lambda s: s["index"])
    return scenes

# --- SCRIPT INPUT ---
st.subheader("1. Paste Scene Plan (Scenes 1 - 72)")
raw_script = st.text_area(
    "Paste Script",
    placeholder="🎬 SCENE 01 — 00:00–00:10\n\nNARRATION\n“...”\n\nVISUAL\n...\n\nCONTINUITY\n...",
    height=180
)

if st.button("🚀 Parse Scenes", type="primary"):
    if raw_script.strip():
        st.session_state["scenes"] = parse_scenes(raw_script, pres_info)
        total_sec = len(st.session_state["scenes"]) * global_duration
        st.success(f"Parsed {len(st.session_state['scenes'])} scenes! Total Runtime: {total_sec}s ({total_sec / 60:.1f} mins)")
    else:
        st.warning("Please paste your script text first.")

# --- SCENE CARDS ---
if "scenes" in st.session_state and st.session_state["scenes"]:
    st.subheader(f"2. Scene Deck ({len(st.session_state['scenes'])} Scenes)")

    for s in st.session_state["scenes"]:
        idx = s["index"]
        with st.expander(f"🎬 Scene {idx:02d} — {s['visual'][:45]}...", expanded=(idx <= 5)):
            st.markdown(f"**🎙️ Narration:** {s['narration']}")
            if s['continuity']:
                st.caption(f"**Continuity Target:** {s['continuity']}")

            col1, col2 = st.columns(2)
            with col1:
                camera_move = st.selectbox(
                    "Camera Motion",
                    ["Tracking Low", "Slow Zoom In", "Slow Pan Left", "Slow Pan Right", "Static Composition"],
                    key=f"cam_{idx}"
                )
                seed_val = st.number_input("Character Seed", value=42890 + (pres_num * 100) + idx, key=f"seed_{idx}")

            with col2:
                scene_duration = st.selectbox("Duration (Sec)", [10, 5], index=0 if global_duration == 10 else 1, key=f"dur_{idx}")
                lip_sync = st.checkbox("Lip-Sync Voice", value=False, key=f"lip_{idx}")

            prompt_parts = [
                "2D hand-drawn American history documentary, bold outlines, flat muted colors, clean illustrated shapes.",
                f"Visual: {s['visual'].rstrip('.')}.",
            ]
            if s['continuity']:
                prompt_parts.append(f"Action: {s['continuity'].rstrip('.')}.")
            if s['characters']:
                prompt_parts.append(f"Character References: {' | '.join(s['characters'])}.")
            prompt_parts.append(f"Motion: {camera_move}. Duration: {scene_duration}s. Aspect Ratio: {global_aspect_ratio.split()[0]}.")

            compiled_prompt = " ".join(prompt_parts)
            st.text_area("Final Injected AI Prompt", value=compiled_prompt, height=100, key=f"prompt_{idx}")

            btn_col1, btn_col2 = st.columns([1, 2])
            with btn_col1:
                if st.button(f"Generate Scene {idx:02d}", key=f"gen_{idx}", type="primary"):
                    st.info(f"Submitting Scene {idx:02d} | Seed: {seed_val} | Duration: {scene_duration}s")
            with btn_col2:
                st.caption("Status: Ready to trigger")
                            
