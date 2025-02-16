from rev_ai import apiclient
import os
from datetime import datetime
import time
import logging
import argparse

rev_access_token = os.getenv("REVAI_ACCESS_TOKEN")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%m/%d/%Y %H:%M:%S'
)
logger = logging.getLogger(__name__)

"""
Rev.ai Audio Transcription Script

This script transcribes audio files to SRT and/or TXT format using the Rev.ai API.

Prerequisites:
    - Rev.ai API token set as REVAI_ACCESS_TOKEN environment variable
    - Required packages: rev_ai

Installation:
    pip install --upgrade rev_ai

Usage:
    python rev.py <audio_file> [--language LANG_CODE] [--format FORMAT]

Arguments:
    audio_file          Path to the audio file to transcribe
    --language, -l      Language code for transcription (default: cmn)
                       Common codes: en (English), cmn (Mandarin). 
                       See https://docs.rev.ai/api/asynchronous/reference/#operation/SubmitTranscriptionJob!ct=application/json&path=language&t=request
    --format, -f        Output format: srt, txt, or both (default: both)

Example:
    python rev.py recording.mp3 --language eng --format both

Output:
    Creates SRT and/or TXT files in the same directory as input file with timestamp
"""

def create_srt_from_transcript(transcript):
    # Split into lines and filter empty lines
    lines = [line.strip() for line in transcript.split('\n') if line.strip()]
    
    srt_entries = []
    counter = 1
    
    for line in lines:
        # Split each line into components
        parts = line.split('    ')
        if len(parts) != 3:
            continue
            
        speaker, timestamp, text = parts
        
        # Convert timestamp
        time_parts = timestamp.strip().split(':')
        if len(time_parts) != 3:
            continue
            
        hours, minutes, seconds = time_parts
        start_time = f"{hours}:{minutes}:{seconds},000"
        
        # Calculate end time (using next timestamp or +5 seconds for last entry)
        end_time = f"{hours}:{minutes}:{float(seconds)+5:.3f}".replace('.', ',')
        
        # Format SRT entry
        srt_entry = f"{counter}\n{start_time} --> {end_time}\n{speaker}: {text}\n"
        srt_entries.append(srt_entry)
        counter += 1
    
    return "\n".join(srt_entries)


def transcribe_to_files(file_path, language="cmn", output_format="srt"):
    """
    Transcribe an audio file to SRT and/or TXT format using Rev.ai API.
    
    Args:
        file_path (str): Path to the local audio file
        language (str): Language code for transcription (e.g. "eng", "cmn")
        output_format (str): Output format - "srt", "txt", or "both"
        
    Returns:
        str or tuple: Path(s) to the generated file(s)
    """
    # Create Rev.ai client
    logger.info("Initializing Rev.ai client")
    client = apiclient.RevAiAPIClient(rev_access_token)
    
    # Submit transcription job
    logger.info(f"Submitting transcription job for {file_path}")
    job = client.submit_job_local_file(
        file_path,
        language=language
    )
    
    # Wait for job to complete
    logger.info(f"Waiting for job {job.id} to complete")
    job_details = client.get_job_details(job.id)
    while job_details.status == "in_progress":
        job_details = client.get_job_details(job.id)
        logger.debug(f"Job status: {job_details.status}")
        time.sleep(30)  # Wait 30 seconds before checking again
        
    # Get transcript once complete
    if job_details.status == "transcribed":
        logger.info("Job completed successfully, retrieving transcript")
        transcript_text = client.get_transcript_text(job.id)
    else:
        logger.error(f"Transcription failed with status: {job_details.status}")
        raise Exception(f"Transcription failed with status: {job_details.status}")
    
    filename = os.path.splitext(os.path.basename(file_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_paths = []
    
    if output_format in ["srt", "both"]:
        # Convert transcript to SRT format with speaker labels
        logger.info("Converting transcript to SRT format")
        captions = create_srt_from_transcript(transcript_text)
        
        # Save SRT file
        srt_path = os.path.join(os.path.dirname(file_path), f"{filename}_{timestamp}.srt")
        os.makedirs(os.path.dirname(srt_path), exist_ok=True)
        
        logger.info(f"Saving SRT file to {srt_path}")
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(captions)
        output_paths.append(srt_path)
        
    if output_format in ["txt", "both"]:
        # Save raw transcript as TXT
        txt_path = os.path.join(os.path.dirname(file_path), f"{filename}_{timestamp}.txt")
        os.makedirs(os.path.dirname(txt_path), exist_ok=True)
        
        logger.info(f"Saving TXT file to {txt_path}")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(transcript_text)
        output_paths.append(txt_path)
    
    logger.info("File(s) have been created successfully")
    return output_paths[0] if len(output_paths) == 1 else tuple(output_paths)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transcribe audio file to SRT/TXT using Rev.ai')
    parser.add_argument('file', help='Path to the audio file to transcribe')
    parser.add_argument('--language', '-l', default='cmn', help='Language code for transcription (default: cmn)')
    parser.add_argument('--format', '-f', default='both', choices=['srt', 'txt', 'both'], 
                       help='Output format: srt, txt, or both (default: both)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        logger.error(f"File {args.file} does not exist")
        exit(1)
        
    if not rev_access_token:
        logger.error("REVAI_ACCESS_TOKEN environment variable not set")
        exit(1)
        
    try:
        output_paths = transcribe_to_files(args.file, args.language, args.format)
        if isinstance(output_paths, tuple):
            logger.info(f"Transcription complete! Files saved to: {' and '.join(output_paths)}")
        else:
            logger.info(f"Transcription complete! File saved to: {output_paths}")
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        exit(1)