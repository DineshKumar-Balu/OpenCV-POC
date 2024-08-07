import cv2
import pytesseract
import re
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import platform
import subprocess 
import sys
sys.path.append("tessey")
from streamlit_player import st_player
import webview

# Set Tesseract path for Linux (Streamlit Cloud runs on Linux)


pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

def convert_to_h264(input_video_path, output_video_path):
    command = [
        'ffmpeg', '-y',
        '-i', './assets/out.mp4',
        '-c:v', 'libx264',
        './assets/out_h264.mp4'
    ]

    # Execute the command
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def get_time_from_frame(img):
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(img, config=custom_config)
    # st.write(text)
    pattern = re.compile(r'\d{2}:\d{2}:\d{2}')
    res = pattern.search(text)
    if res:
        return res.group(0)
    return None

def get_initial_time(video_path):
    vid = cv2.VideoCapture(video_path)
    total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
    vid.set(cv2.CAP_PROP_POS_FRAMES, total_frames - total_frames+ 1)
    is_success, img = vid.read()
    vid.release()
    if is_success:
        return get_time_from_frame(img)
    return None

def get_video_end_time(video_path):
    vid = cv2.VideoCapture(video_path)
    total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
    vid.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 2)
    is_success, img = vid.read()
    vid.release()
    if is_success:
        return get_time_from_frame(img)
    return None

def get_video_start_time_from_csv(df, search_term):
    # Filter based on search_term in Name, Company Name, Email, or Phone columns
    filtered_rows = df[
        df['Name'].str.contains(search_term, na=False, case=False) |
        df['Company Name'].str.contains(search_term, na=False, case=False) |
        df['Email'].str.contains(search_term, na=False, case=False) |
        df['Phone'].str.contains(search_term, na=False, case=False)
    ]

    if not filtered_rows.empty:
        # Get the first matching row
        start_time = filtered_rows.iloc[0]['DATE AND TIME'].strftime('%H:%M:%S')
        return start_time
    else:
        return None

def suggest_values(search_term, df, columns):
    suggestions = set()
    for column in columns:
        matches = df[df[column].str.contains(search_term, na=False, case=False)][column].tolist()
        suggestions.update(matches)
    return list(suggestions)

def main():
    st.set_page_config(page_title="Video Player", page_icon="📹", layout="centered")

    uploaded_file = st.file_uploader("Upload a video file (MP4, AVI, MOV)", type=["mp4", "avi", "mov"])
    uploaded_csv = "./csvsheetdb1.csv"  

    if uploaded_file:
        os.makedirs("./assets", exist_ok=True)
        # st.write(os.listdir("./"))
        # st.write(os.listdir("./assets"))
        video_path = "./assets/out.mp4"
        h264_video_path = "./assets/out_h264.mp4"
        
        with open(video_path, 'wb') as vid:
            vid.write(uploaded_file.read())

        # Convert video to H.264 format
        convert_to_h264(video_path, h264_video_path)


        initial_time = get_initial_time(h264_video_path)
        end_time = get_video_end_time(h264_video_path)

        # st.write(initial_time)
        # st.write(end_time)
        if initial_time and end_time:
            c1,c2 = st.columns(2)
            with c1:
                st.write("Initial Time from Video:", initial_time)
            with c2:
                st.write("End Time from Video:", end_time)

            st.write()
            c3 = st.columns(1)
            # Manual time adjustment inputs
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Start Time**")
                start_time_input = st.text_input("", initial_time, key="start_time")
            with col2:
                st.write("**Jump Time**")
                jump_time_input = st.text_input("", "00:00:00", key="jump_time")

            if uploaded_csv:
                df = pd.read_csv(uploaded_csv)
                
                # Convert "DATE AND TIME" column to datetime format
                df['DATE AND TIME'] = pd.to_datetime(df['DATE AND TIME'], format='%m-%d-%Y %H:%M')

                search_term = st.text_input("Enter Name, Company Name, Email, or Phone Number to start video from their timestamp:", key="search_term")

                if search_term:
                    suggestions = suggest_values(search_term, df, ['Name', 'Company Name', 'Email', 'Phone'])
                    if suggestions:
                        filtered_suggestions = [s for s in suggestions if s.lower().startswith(search_term.lower())]
                        if filtered_suggestions:
                            suggestion = st.selectbox('Suggestions:', filtered_suggestions)
                            if suggestion:
                                search_term = suggestion

                    start_time_from_csv = get_video_start_time_from_csv(df, search_term)
                    if start_time_from_csv:
                        st.write(f"**Start Time from CSV for '{search_term}':**", start_time_from_csv)
                        start_time_input = start_time_from_csv
                    else:
                        st.warning(f"No matching entry found in CSV for '{search_term}'.")

            # Calculate start time and jump time in seconds
            initial_time_dt = datetime.strptime(initial_time, '%H:%M:%S')
            start_time_dt = datetime.strptime(start_time_input, '%H:%M:%S')
            jump_time_dt = datetime.strptime(jump_time_input, '%H:%M:%S') if jump_time_input else None

            # Adjust start time with the offset
            if jump_time_dt and jump_time_dt >= initial_time_dt:
                jump_seconds = (jump_time_dt - initial_time_dt).total_seconds()
            else:
                jump_seconds = 0

            start_seconds = (start_time_dt - initial_time_dt).total_seconds()

            # Display video with specified start time
            st.video(h264_video_path, start_time=start_seconds + jump_seconds, format='video/mp4', autoplay=True)
            # video_html = f"""
            # <video controls width="640" height="360">
            #     <source src="./assets/out.mp4#t={0+jump_seconds}" type="video/mp4">
            #     Your browser does not support the video tag.
            # </video>
            # """
            # st.write(video_html,unsafe_allow_html = True)

        else:
            st.warning("Could not extract initial or end time from video.")

    else:
        st.write("Upload a video file to start.")

if __name__ == "__main__":
    main()
