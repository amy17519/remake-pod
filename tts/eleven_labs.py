"""
ElevenLabs Text-to-Speech Script

This script converts text from an SRT file to speech using the ElevenLabs API.
Each speaker's lines are converted using a different voice.

Prerequisites:
    - ElevenLabs API key set as ELEVENLABS_API_KEY environment variable
    - Required packages: elevenlabs, pydub

Usage:
    python eleven_labs.py --input INPUT_SRT --voices "Voice1" "Voice2" "Voice3" [--output OUTPUT_PATH]

Arguments:
    --input, -i     SRT file to convert to speech (required)
    --voices, -v    List of voices to use for each speaker in order (required)
    --output, -o    Output audio file path (default: output.mp3)

Example:
    python eleven_labs.py --input input.srt --voices "Voice1" "Voice2" "Voice3" --output output.mp3
"""

import argparse
import os
import logging
import pydub
import re
from elevenlabs.client import ElevenLabs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%m/%d/%Y %H:%M:%S'
)
logger = logging.getLogger(__name__)

elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")


def parse_srt(srt_file):
    """Parse SRT file and extract speaker lines."""
    speaker_lines = []
    with open(srt_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Extract speaker lines using regex
    pattern = r'Speaker (\d+): (.*?)(?=\n\n|\Z)'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        speaker_num = int(match.group(1))
        text = match.group(2).strip()
        speaker_lines.append((speaker_num, text))
        
    return speaker_lines

def generate_speech(input_file, voices, output):
    """Generate speech from SRT file using ElevenLabs API with multiple voices."""
    try:
        # Parse SRT and get speaker lines first
        speaker_lines = parse_srt(input_file)
        
        # Initialize ElevenLabs services for each voice
        voice_services = []
        for voice in voices:
            service = ElevenLabs(api_key=elevenlabs_api_key)
            voice_services.append(service)

        # Create empty audio mix
        final_mix = pydub.AudioSegment.empty()
        
        # Generate audio for each speaker line
        for speaker_num, text in speaker_lines:
            if speaker_num >= len(voices):
                logger.warning(f"No voice assigned for Speaker {speaker_num}, skipping line")
                continue
                
            logger.info(f"Generating speech for Speaker {speaker_num}: {text[:30]}...")
            audio = voice_services[speaker_num].generate(text=text, voice=voices[speaker_num], model="eleven_multilingual_v2")
            
            # Save audio to temp file
            with open("temp.mp3", "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            
            # Add to final mix
            audio_segment = pydub.AudioSegment.from_mp3("temp.mp3")
            final_mix += audio_segment

        # Export final audio
        final_mix.export(output, format="mp3")
        logger.info(f"Audio saved to {output}")

    except FileNotFoundError:
        logger.error(f"Input file not found: {input_file}")
        exit(1)
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        exit(1)

def main():
    parser = argparse.ArgumentParser(description='Convert SRT file to speech using ElevenLabs with multiple voices')
    parser.add_argument('-i', '--input', help='SRT file to convert to speech', type=str, required=True)
    parser.add_argument('-v', '--voices', help='Voices to use for each speaker in order', type=str, nargs='+', required=True)
    parser.add_argument('-o', '--output', help='Output audio file path', type=str, default='output.mp3')
    args = parser.parse_args()

    if not os.getenv("ELEVENLABS_API_KEY"):
        logger.error("ELEVENLABS_API_KEY environment variable not set")
        exit(1)

    generate_speech(args.input, args.voices, args.output)

if __name__ == "__main__":
    main()