import asyncio
import logging
from typing import Optional

import chardet

from ..files.domain import File, FileProcessor
from ..files.file_processor import BaseFileProcessor, PlainTextFileProcessor, XlsxFileProcessor, XlsFileProcessor, BasicPdfFileProcessor, EnhancedPdfFileProcessor, ImageFileProcessor
from ..files.file_quota import FileQuota


logger = logging.getLogger(__name__)


class UnsupportedFileError(Exception):
    def __init__(self, file_name: str):
        super().__init__(f"Unsupported file type: {file_name}")


def add_encoding_to_content_type(content_type: Optional[str], content: bytes) -> str:
    # add the encoding to the content type so later on it can be used (for exammple in tools file processing) and is avaible to frontend for proper file visualization
    if content_type and content_type.startswith('text/') and not 'charset=' in content_type:
        detected = chardet.detect(content)
        encoding = detected['encoding'] if detected and detected['encoding'] else 'utf-8'
        content_type = f"{content_type}; charset={encoding.lower()}"
    return content_type or "application/octet-stream"


def find_file_processor(file: File) -> BaseFileProcessor:
    processors = [
        PlainTextFileProcessor(),
        XlsxFileProcessor(),
        XlsFileProcessor(),
        ImageFileProcessor(),
        BasicPdfFileProcessor() if file.file_processor == FileProcessor.BASIC else EnhancedPdfFileProcessor()
    ]
    found = next((processor for processor in processors if processor.supports(file)), None)
    if found is None:
        raise UnsupportedFileError(file.name)
    return found


async def extract_file_text(file: File, file_quota: FileQuota) -> str:
    processor = find_file_processor(file)
    return await asyncio.to_thread(processor.extract_text, file, file_quota)
