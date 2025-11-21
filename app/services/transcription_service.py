"""
Transcription service for converting audio/video to text

NOTE: This is a simplified implementation. For production use with Google Cloud Speech-to-Text,
you'll need to:
1. Install google-cloud-speech: pip install google-cloud-speech
2. Set up a service account and download JSON credentials
3. Set GOOGLE_APPLICATION_CREDENTIALS environment variable
4. Install ffmpeg system-wide for audio extraction

For now, this provides a mock implementation that can be replaced with actual transcription.
"""
import os
import logging
import subprocess

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for transcribing audio/video files"""
    
    def __init__(self):
        """Initialize transcription service"""
        self.use_mock = not os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if self.use_mock:
            logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set. Using mock transcription.")
        else:
            try:
                from google.cloud import speech_v1p1beta1 as speech
                self.client = speech.SpeechClient()
                logger.info("Google Cloud Speech-to-Text client initialized")
            except ImportError:
                logger.error("google-cloud-speech not installed. Using mock transcription.")
                self.use_mock = True
            except Exception as e:
                logger.error(f"Failed to initialize Speech client: {e}. Using mock transcription.")
                self.use_mock = True
    
    def transcribe_audio_file(self, audio_file_path, language_code='en-US', 
                              enable_speaker_diarization=True):
        """
        Transcribe an audio file
        
        Args:
            audio_file_path: Path to audio file (local)
            language_code: Language code (e.g., 'en-US', 'es-ES')
            enable_speaker_diarization: Enable speaker identification
        
        Returns:
            Dictionary with transcript and metadata
        """
        if self.use_mock:
            return self._mock_transcribe(audio_file_path)
        
        try:
            from google.cloud import speech_v1p1beta1 as speech
            
            # Read audio file
            with open(audio_file_path, 'rb') as audio_file:
                content = audio_file.read()
            
            audio = speech.RecognitionAudio(content=content)
            
            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                enable_speaker_diarization=enable_speaker_diarization,
                diarization_speaker_count=2 if enable_speaker_diarization else None
            )
            
            # Perform recognition
            logger.info('Starting transcription...')
            operation = self.client.long_running_recognize(
                config=config,
                audio=audio
            )
            
            logger.info('Waiting for transcription to complete...')
            response = operation.result(timeout=3600)  # 1 hour timeout
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    def transcribe_gcs_uri(self, gcs_uri, language_code='en-US', 
                           enable_speaker_diarization=True):
        """
        Transcribe an audio file from Google Cloud Storage
        
        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file)
            language_code: Language code
            enable_speaker_diarization: Enable speaker identification
        
        Returns:
            Dictionary with transcript and metadata
        """
        if self.use_mock:
            return self._mock_transcribe(gcs_uri)
        
        try:
            from google.cloud import speech_v1p1beta1 as speech
            
            audio = speech.RecognitionAudio(uri=gcs_uri)
            
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                enable_speaker_diarization=enable_speaker_diarization,
                diarization_speaker_count=2 if enable_speaker_diarization else None,
                model='video'  # Optimized for video
            )
            
            operation = self.client.long_running_recognize(
                config=config,
                audio=audio
            )
            
            logger.info('Waiting for transcription to complete...')
            response = operation.result(timeout=3600)
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Error transcribing GCS audio: {e}")
            return None
    
    def _parse_response(self, response):
        """Parse Speech-to-Text API response"""
        transcript_segments = []
        full_transcript = []
        
        for result in response.results:
            alternative = result.alternatives[0]
            
            # Get full transcript
            full_transcript.append(alternative.transcript)
            
            # Get word-level details with timestamps
            if hasattr(alternative, 'words'):
                current_speaker = None
                current_segment = {'speaker': 'Unknown', 'text': '', 'start_time': 0, 'end_time': 0}
                
                for word_info in alternative.words:
                    speaker_tag = word_info.speaker_tag if hasattr(word_info, 'speaker_tag') else 0
                    
                    if current_speaker is None:
                        current_speaker = speaker_tag
                        current_segment['speaker'] = f"Speaker {speaker_tag}"
                        current_segment['start_time'] = word_info.start_time.seconds + word_info.start_time.microseconds / 1e6
                    
                    if speaker_tag != current_speaker:
                        # New speaker, save current segment
                        current_segment['end_time'] = word_info.start_time.seconds + word_info.start_time.microseconds / 1e6
                        transcript_segments.append(current_segment.copy())
                        
                        # Start new segment
                        current_speaker = speaker_tag
                        current_segment = {
                            'speaker': f"Speaker {speaker_tag}",
                            'text': word_info.word,
                            'start_time': word_info.start_time.seconds + word_info.start_time.microseconds / 1e6,
                            'end_time': 0
                        }
                    else:
                        current_segment['text'] += ' ' + word_info.word
                        current_segment['end_time'] = word_info.end_time.seconds + word_info.end_time.microseconds / 1e6
                
                # Add last segment
                if current_segment['text']:
                    transcript_segments.append(current_segment)
        
        # Calculate average confidence
        confidence = sum(result.alternatives[0].confidence for result in response.results if result.alternatives) / len(response.results) if response.results else 0.0
        
        return {
            'transcript_text': ' '.join(full_transcript),
            'transcript_segments': transcript_segments,
            'confidence': confidence,
            'language': response.results[0].language_code if response.results else 'en-US'
        }
    
    def _mock_transcribe(self, file_path):
        """
        Mock transcription for development/testing
        
        Args:
            file_path: Path to audio/video file
            
        Returns:
            Mock transcript dictionary
        """
        logger.info(f"Using mock transcription for: {file_path}")
        
        return {
            'transcript_text': (
                "This is a mock transcript. In production, this would be the actual "
                "transcription from Google Cloud Speech-to-Text API. The meeting discussed "
                "project timeline, identified three key action items: 1) Complete the design "
                "mockups by Friday, 2) Schedule follow-up meeting for next week, and "
                "3) Review budget allocation with finance team. The team agreed on the "
                "proposed architecture and decided to move forward with the implementation."
            ),
            'transcript_segments': [
                {
                    'speaker': 'Speaker 1',
                    'text': 'Hello everyone, lets discuss the project timeline.',
                    'start_time': 0.0,
                    'end_time': 3.5
                },
                {
                    'speaker': 'Speaker 2',
                    'text': 'I can complete the design mockups by Friday.',
                    'start_time': 4.0,
                    'end_time': 7.2
                },
                {
                    'speaker': 'Speaker 1',
                    'text': 'Great. Lets schedule a follow-up meeting for next week.',
                    'start_time': 7.8,
                    'end_time': 11.5
                }
            ],
            'confidence': 0.95,
            'language': 'en-US'
        }
    
    @staticmethod
    def extract_audio_from_video(video_path, audio_output_path):
        """
        Extract audio from video file using ffmpeg
        
        Note: Requires ffmpeg to be installed on the system
        
        Args:
            video_path: Path to video file
            audio_output_path: Path for output audio file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if ffmpeg is available
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("ffmpeg not found. Please install ffmpeg.")
                return False
            
            command = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # Linear PCM
                '-ar', '16000',  # Sample rate 16kHz
                '-ac', '1',  # Mono
                '-y',  # Overwrite output file
                audio_output_path
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Audio extracted successfully to {audio_output_path}")
                return True
            else:
                logger.error(f"Error extracting audio: {result.stderr}")
                return False
                
        except FileNotFoundError:
            logger.error("ffmpeg not found in PATH. Please install ffmpeg.")
            return False
        except Exception as e:
            logger.error(f"Error in extract_audio_from_video: {e}")
            return False
