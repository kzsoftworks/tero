from .common import *

from tero.threads.api import THREADS_PATH, AUDIO_FORMAT
from tero.threads.domain import ThreadTranscriptionResult


THREAD_ID = 21
TRANSCRIPT_PATH = f"{THREADS_PATH}/{THREAD_ID}/transcriptions"
EXPECTED_TRANSCRIPTION = "¿podrías conseguirme los reportes que están en la página 5 de mi pdf, por favor?"


async def test_transcription_endpoint(client: AsyncClient):
    content = await find_asset_bytes("audio.webm")
    files = {
        "file": ("audio.webm", content, AUDIO_FORMAT)
    }
    resp = await client.post(TRANSCRIPT_PATH, files=files)

    resp.raise_for_status()
    result = ThreadTranscriptionResult(**resp.json())
    assert result.transcription.lower().strip() == EXPECTED_TRANSCRIPTION.lower().strip()


async def test_transcription_invalid_file(client: AsyncClient):
    files = {
        "file": ("test.txt", b"This is not an audio file", "text/plain")
    }
    resp = await client.post(TRANSCRIPT_PATH, files=files)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
