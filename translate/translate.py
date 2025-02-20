import openai
import logging
import os   
from datetime import datetime
logger = logging.getLogger(__name__)

# Configure OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"

def translate_srt(srt_file: str, from_lang: str, to_lang: str) -> str:
    """
    Translate text using OpenAI's API
    
    Args:
        srt_file (str): Path to SRT file to translate
        from_lang (str): Source language code
        to_lang (str): Target language code
        
    Returns:
        str: Translated text
    """
    with open(srt_file, 'r', encoding='utf-8') as f:
        text = f.read()

    try:
        logger.info("Translating text with OpenAI")
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model= OPENAI_MODEL,
            messages=[
                {"role": "system", "content": f"You are a translator. Translate the following text from {from_lang} to {to_lang}. Maintain the original meaning and tone."},
                {"role": "user", "content": text}
            ]
        )
        translated_text = response.choices[0].message.content
        
        # Generate new filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = os.path.basename(srt_file)
        filename_without_ext = os.path.splitext(original_filename)[0]
        new_filename = f"{filename_without_ext}_{from_lang}_to_{to_lang}_{timestamp}.srt"
        new_filepath = os.path.join(os.path.dirname(srt_file), new_filename)
        
        # Save translated text
        logger.info(f"Saving translated file to {new_filepath}")
        with open(new_filepath, 'w', encoding='utf-8') as f:
            f.write(translated_text)
            
        return new_filepath

    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise 