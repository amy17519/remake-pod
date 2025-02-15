from flask import Flask, request, render_template, flash
import whisper
from datetime import timedelta, datetime
from pydub import AudioSegment
import os
from gtts import gTTS
import openai
import logging
import warnings
from pyannote.audio import Pipeline
            

warnings.filterwarnings("ignore", category=FutureWarning, module="whisper")
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24) # Required for flashing messages

# Configure OpenAI API key
# openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = "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"


def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (hh:mm:ss,ms)"""
    td = timedelta(seconds=seconds)
    return f"{td.seconds // 3600:02}:{(td.seconds // 60) % 60:02}:{td.seconds % 60:02},{int(td.microseconds / 1000):03}"

def save_srt(segments, output_file="output.srt"):
    """Save Whisper segments as an SRT file"""
    with open(output_file, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start_time = format_timestamp(segment["start"])
            end_time = format_timestamp(segment["end"])
            text = segment["text"].strip()

            f.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")

@app.route('/', methods=['GET', 'POST'])
def translate_audio():
    if request.method == 'POST':
        temp_dir = "temp"
        temp_files = []  # Keep track of temporary files
        downloads_dir = os.path.expanduser("~/Downloads")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Get the uploaded file and language selections
            logger.info("Processing new audio translation request")
            audio_file = request.files['audio']
            from_lang = request.form['from_lang']
            to_lang = request.form['to_lang']
            
            if not audio_file:
                flash("No audio file uploaded", "error")
                return render_template('upload.html')
            
            flash("Starting translation process...", "info")
            
            # Create temp directory if it doesn't exist
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            # Save uploaded file temporarily with original extension
            logger.info("Saving uploaded file")
            original_filename = audio_file.filename
            file_ext = os.path.splitext(original_filename)[1].lower()
            temp_original = os.path.join(temp_dir, f"temp_input{file_ext}")
            audio_file.save(temp_original)
            temp_files.append(temp_original)
            
            # Convert audio to mp3 if needed
            logger.info("Converting audio format if needed")
            temp_path = os.path.join(temp_dir, "temp_audio.mp3")
            if file_ext in ['.m4a', '.wav', '.ogg', '.aac']:
                flash("Converting audio format...", "info")
                audio = AudioSegment.from_file(temp_original)
                audio.export(temp_path, format="mp3")
            else:
                os.rename(temp_original, temp_path)
            temp_files.append(temp_path)

            # Load Whisper model and transcribe
            logger.info("Transcribing audio with Whisper")
            flash("Transcribing audio...", "info")
            model = whisper.load_model("small", device="cpu")  # Changed to use device parameter
            
            # Initialize pyannote diarization pipeline
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token="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"
            )
            
            # Perform diarization
            diarization = pipeline(temp_path)
            
            # Transcribe with Whisper
            result = model.transcribe(temp_path, language=from_lang, fp16=False)
            
            # Combine transcription with speaker IDs
            segments = []
            for segment, track in diarization.itertracks(yield_label=True):
                # Find matching transcription segments
                matching_segments = []
                for trans_segment in result["segments"]:
                    trans_start = trans_segment["start"]
                    trans_end = trans_segment["end"]
                    # Check for overlap
                    if (trans_start >= segment.start and trans_start < segment.end) or \
                       (trans_end > segment.start and trans_end <= segment.end):
                        matching_segments.append(trans_segment["text"])
                
                if matching_segments:
                    segments.append(f"Speaker {track}: {' '.join(matching_segments)}")
            
            text = "\n".join(segments)
            
            # Translate text using OpenAI
            logger.info("Translating text with OpenAI")
            flash("Translating content...", "info")
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You are a translator. Translate the following text from {from_lang} to {to_lang}. Maintain the original meaning and tone."},
                    {"role": "user", "content": text}
                ]
            )
            translated_text = response.choices[0].message.content
            
            # Convert translated text to speech
            logger.info("Converting translation to speech")
            flash("Generating audio from translation...", "info")
            output_filename = f"translated_audio_{timestamp}.mp3"
            output_path = os.path.join(downloads_dir, output_filename)
            tts = gTTS(text=translated_text, lang=to_lang)
            tts.save(output_path)
            
            # Save transcript as SRT
            logger.info("Saving transcript")
            srt_filename = f"transcript_{timestamp}.srt"
            srt_path = os.path.join(downloads_dir, srt_filename)
            save_srt(result["segments"], srt_path)
            
            # Clean up temporary files
            logger.info("Cleaning up temporary files")
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    logger.error(f"Error removing temporary file {temp_file}: {str(e)}")
            
            try:
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                logger.error(f"Error removing temp directory: {str(e)}")
            
            flash(f"Translation complete! Files saved to Downloads folder as {output_filename} and {srt_filename}", "success")
            return render_template('upload.html')
            
        except Exception as e:
            logger.error(f"Error during translation: {str(e)}")
            flash(f"An error occurred during translation: {str(e)}", "error")
            return render_template('upload.html')
    
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
