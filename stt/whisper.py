import whisper
import logging

logger = logging.getLogger(__name__)

def transcribe_audio(audio_path, source_language):
    """
    Transcribe audio file using Whisper model.
    
    Args:
        audio_path (str): Path to the audio file
        source_language (str): Language code of the source audio
        
    Returns:
        dict: Whisper transcription result containing 'text' and 'segments'
    """
    try:
        logger.info("Loading Whisper model")
        model = whisper.load_model("small", device="cpu")
        
        logger.info("Transcribing audio with Whisper")
        result = model.transcribe(
            audio_path, 
            language=source_language, 
            fp16=False
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        raise 