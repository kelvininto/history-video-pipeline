import streamlit as st
import json
import re
import os
import tempfile
from moviepy.editor import VideoFileClip, concatenate_videoclips

st.set_page_config(page_title="AI History Studio", layout="wide", initial_sidebar_state="collapsed")

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

st.title("🏛️ Presidential Video Assembler")
st.caption("Prompt Generator & Automated 12-Minute Video Stitcher")

# --- TOP BAR: PRESIDENT SELECTION ---
col_p1, col_p2 = st.columns([1, 2])
with col_p1:
    pres_num = st.selectbox("Select President Episode", range(1, 57), index=4)
with col_p2:
    pres_info = presidents.get(str(pres_num), {"name": f"President #{pres_num}", "prompt_anchor": "", "youth_anchor": ""})
    st.info(f"Subject: **#{pres_num} — {pres_info['name']}**")

# --- SCRIPT PARSER ---
def parse_scenes(text, pres_data):
    pattern = re.compile(r"(?i)(?:^|\n)\s*(?:🎬\s*)?SCENE\s*(\d+)[^\n]*\n?")
    splits = pattern.split(text)
    scenes = []
    if len(splits) > 1:
        for i in range(1, len(splits), 2):
            idx = int(splits[i])
            blk = splits[i+1].strip()
            vis = re.search(r"(?i)VISUAL\s*\n+([^\n]+(?:\n[^\n]+)*?)(?=\n+[A-Z\s]{4,}|\Z)", blk)
            cont = re.search(r"(?i)CONTINUITY\s*\n+([^\n]+(?:\n[^\n]+)*?)(?=\n+[A-Z\s]{4,}|\Z)", blk)
            vis_text = vis.group(1).strip() if vis else ""
            cont_text = cont.group(1).strip() if cont else ""
            
            prompt = (
                f"2D hand-drawn American history documentary animation, bold black outlines, flat muted colors. "
                f"Visual: {vis_text}. Action: {cont_text}. "
                f"Anchor: {pres_data.get('prompt_anchor', '')}. "
                f"16:9, clean lighting, strict 10s duration."
            )
            scenes.append({"index": idx, "visual": vis_text, "prompt": prompt})
    scenes.sort(key=lambda s: s["index"])
    return scenes

# --- SECTION 1: SCRIPT & PROMPT COPIER ---
st.subheader("1. Generate Scene Prompts")
raw_script = st.text_area("Paste Script Plan (Scenes 1–72)", height=150)

if st.button("🚀 Parse & View Prompts", type="primary"):
    if raw_script.strip():
        st.session_state["scenes"] = parse_scenes(raw_script, pres_info)
        st.success(f"Parsed {len(st.session_state['scenes'])} scenes successfully!")

if "scenes" in st.session_state and st.session_state["scenes"]:
    with st.expander("📋 Tap to Expand Prompts for Gemini / Flow", expanded=False):
        for s in st.session_state["scenes"]:
            st.markdown(f"**Scene {s['index']:02d}:** {s['visual'][:40]}...")
            st.code(s["prompt"], language="text")

# --- SECTION 2: BATCH UPLOAD & AUTO-STITCH ---
st.divider()
st.subheader("2. Upload Clips & Stitch Final Video")
st.write("Upload your generated 10-second MP4 clips. You can upload them all at once or in batches.")

uploaded_files = st.file_uploader(
    "Select video files (e.g., Scene_01.mp4, Scene_02.mp4...)",
    type=["mp4", "mov"],
    accept_multiple_files=True
)

if uploaded_files:
    # Sort files naturally by filename so Scene 01 goes before Scene 02
    sorted_files = sorted(uploaded_files, key=lambda f: f.name)
    st.info(f"Loaded {len(sorted_files)} clips ready to merge.")
    
    if st.button("🎬 Stitch Clips into Final Video", type="primary"):
        with st.spinner("Merging clips into a single documentary video... This takes 1-2 minutes."):
            temp_paths = []
            clips = []
            
            try:
                # Save each uploaded clip to temporary cloud storage
                for file in sorted_files:
                    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                    tfile.write(file.read())
                    temp_paths.append(tfile.name)
                    clips.append(VideoFileClip(tfile.name))
                
                # Concatenate all clips in sequence
                final_video = concatenate_videoclips(clips, method="compose")
                
                output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
                
                # Read the combined video file
                with open(output_path, "rb") as f:
                    final_bytes = f.read()
                
                st.success("🎉 Video stitched successfully!")
                st.video(final_bytes)
                
                st.download_button(
                    label=f"⬇️ Download Final Presidential Documentary ({len(sorted_files) * 10}s)",
                    data=final_bytes,
                    file_name=f"President_{pres_num:02d}_Documentary.mp4",
                    mime="video/mp4"
                )
                
            except Exception as e:
                st.error(f"Error during video stitching: {e}")
            
            finally:
                # Clean up memory and temporary files
                for clip in clips:
                    clip.close()
                for path in temp_paths:
                    if os.path.exists(path):
                        os.remove(path)
                        
