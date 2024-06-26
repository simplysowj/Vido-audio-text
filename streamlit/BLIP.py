import streamlit as st
import cv2
import easyocr
import os
import torch
from moviepy.editor import VideoFileClip
import speech_recognition as sr
import mysql.connector
import requests

# Initialize OCR Reader
reader = easyocr.Reader(['en'])

def extract_audio_from_video(video_path, output_audio_path):
    video_clip = VideoFileClip(video_path)
    audio_clip = video_clip.audio
    audio_clip.write_audiofile(output_audio_path)
    video_clip.close()
    audio_clip.close()

def transcribe_audio_to_text(audio_path):
    recognizer = sr.Recognizer()
    audio_file = sr.AudioFile(audio_path)
    
    with audio_file as source:
        audio_data = recognizer.record(source)
    
    try:
        # Using Google Web Speech API
        text = recognizer.recognize_google(audio_data)
        return text
    except sr.UnknownValueError:
        return "Google Speech Recognition could not understand the audio"
    except sr.RequestError as e:
        return f"Could not request results from Google Speech Recognition service; {e}"

def extract_text_from_frames(video_path, interval=30):
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    success, image = cap.read()
    text_data = []

    while success:
        if frame_count % interval == 0:
            result = reader.readtext(image)
            frame_text = " ".join([res[1] for res in result])
            text_data.append(frame_text)
        success, image = cap.read()
        frame_count += 1

    cap.release()
    return " ".join(text_data)

def insert_caption_data(text, summary):
    try:
        # Connect to MySQL database
        connection = mysql.connector.connect(
            host="localhost",
            port="3306",
            user="root",
            password="new_password",
            database="caption_database"  # Name of your database
        )

        # Create a cursor object to execute SQL queries
        cursor = connection.cursor()

        # SQL query to insert data into the "caption" table
        sql_insert_query = "INSERT INTO caption (text, summary) VALUES (%s, %s)"
        data = (text, summary)

        # Execute the SQL query
        cursor.execute(sql_insert_query, data)

        # Commit the transaction
        connection.commit()

        # Close cursor and connection
        cursor.close()
        connection.close()

        st.success("Data inserted successfully into the 'caption' table!")
    except mysql.connector.Error as error:
        st.error(f"Error inserting data into 'caption' table: {error}")

def download_video_from_url(url, save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return save_path
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading video: {e}")
        return None

def main():
    st.set_page_config(
        page_title="Video/Audio-to-Text",
        page_icon="🎥",
        initial_sidebar_state="collapsed",
        menu_items={'About': "# Video and Audio to Text Conversion App"}
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("Developed by [Your Name]")
    st.sidebar.markdown("Contact: [your-email@example.com](mailto:your-email@example.com)")
    st.sidebar.markdown("GitHub: [Repo](https://github.com/yourusername/yourrepo)")

    st.markdown(
        """
        <style>
        .container {
            max-width: 800px;
        }
        .title {
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .description {
            margin-bottom: 30px;
        }
        .instructions {
            margin-bottom: 20px;
            padding: 10px;
            background-color: #f5f5f5;
            border-radius: 5px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='title'>Video/Audio to Text</div>", unsafe_allow_html=True)
    st.markdown("<div class='description'>Upload a video or audio file to extract and store text.</div>", unsafe_allow_html=True)

    file_type = st.radio("Select File Type:", ("Video", "Audio"))

    file_source = st.radio("Select File Source:", ("Upload File", "URL"))

    file_path = None
    if file_source == "Upload File":
        uploaded_file = st.file_uploader("Upload a file", type=["mp4", "avi", "wav", "mp3"])
        if uploaded_file is not None:
            # Ensure the 'uploads' directory exists
            uploads_dir = "uploads"
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            file_path = os.path.join(uploads_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
    else:
        url = st.text_input("Enter the URL of the file:")
        if url:
            # Ensure the 'downloads' directory exists
            downloads_dir = "downloads"
            if not os.path.exists(downloads_dir):
                os.makedirs(downloads_dir)
            
            file_path = os.path.join(downloads_dir, os.path.basename(url))
            file_path = download_video_from_url(url, file_path)

    if file_path is not None:
        if file_type == "Video":
            st.video(file_path)
            with st.spinner("Extracting text from video..."):
                extracted_text = extract_text_from_frames(file_path)
                # Extract audio from video and transcribe it to text
                audio_path = file_path.replace('.mp4', '.wav')  # Assuming the video is in .mp4 format
                extract_audio_from_video(file_path, audio_path)
                audio_text = transcribe_audio_to_text(audio_path)
                extracted_text = audio_text
        else:
            st.audio(file_path)
            with st.spinner("Extracting text from audio..."):
                extracted_text = transcribe_audio_to_text(file_path)

        st.subheader("Extracted Text:")
        st.write(extracted_text)

        if st.button("Save to Database"):
            insert_caption_data(extracted_text, extracted_text)

if __name__ == "__main__":
    main()
