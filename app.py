from flask import Flask, request, render_template, flash
import os
import logging
from datetime import datetime
from stt.rev import transcribe_to_files
from translate.translate import translate_srt
from tts.eleven_labs import generate_speech

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24) # Required for flashing messages

# Map UI language codes to Rev.ai codes
rev_ai_lang_map = {
    'en': 'en',  # English
    'zh': 'cmn'   # Mandarin Chinese
}


@app.route('/', methods=['GET', 'POST'])
def translate_audio():
    if request.method == 'POST':
        temp_dir = "temp"
        temp_files = []  # Keep track of temporary files
        
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
            temp_original = os.path.join(temp_dir, f"{os.path.splitext(original_filename)[0]}_temp{file_ext}")
            audio_file.save(temp_original)
            temp_files.append(temp_original)
            
            # Transcribe with Rev.ai
            logger.info("Transcribing audio with Rev.ai")
            transcript_files = transcribe_to_files(temp_original, save_dir = "./results", language = rev_ai_lang_map.get(from_lang, 'en'), output_format="both", fix_transcript=True)
            # transcript_files = retrieve_transcription("BOyLYQMK8aqa9Uve", save_dir = "./results", output_format="both", fix_transcript=True)
            
            # Translate srt using OpenAI
            logger.info("Starting translation")
            translated_srt_path = translate_srt(transcript_files[0], from_lang, to_lang)
            
            # Generate audio from translated text using ElevenLabs
            logger.info("Converting translation to speech using ElevenLabs")
            flash("Generating audio from translation...", "info")
            
            # Create timestamp and format output filename for translated audio mp3
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = os.path.splitext(os.path.basename(original_filename))[0]
            output_filename = f"{original_name}_{timestamp}_translated.mp3"
            output_path = os.path.join("results", output_filename)
            
            # Generate speech using ElevenLabs with multiple default voices
            generate_speech(
                input_file=translated_srt_path,  # Use the SRT file
                voices=["Roger", "Aria", "Jessica"],  # Default voices
                output=output_path
            )
            
            flash(f"Translation complete! Audio saved as {output_filename}", "success")
            
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
            
            return render_template('upload.html')
            
        except Exception as e:
            logger.error(f"Error during translation: {str(e)}")
            flash(f"An error occurred during translation: {str(e)}", "error")
            return render_template('upload.html')
    
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
