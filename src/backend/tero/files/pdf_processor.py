import abc
from dataclasses import dataclass
import io
import logging
from typing import Optional, TypeVar, Generic, cast

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult
from azure.core.credentials import AzureKeyCredential
from pydantic import SecretStr
from pypdf import PdfReader, PdfWriter
import pypdfium2 as pdfium
from tabulate import tabulate

from ..core.env import env
from ..files.domain import File
from ..files.file_quota import FileQuota, QuotaExceededError


logger = logging.getLogger(__name__)
T = TypeVar('T', bound='BoundedElement')
PAGES_CHUNK_SIZE = 50


@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_polygon(cls, polygon: list) -> 'BoundingBox | None':
        if not polygon or len(polygon) != 8:
            return None
        
        x_coords = [polygon[i] for i in range(0, 8, 2)]
        y_coords = [polygon[i] for i in range(1, 8, 2)]

        x = min(x_coords)
        y = min(y_coords)
        width = max(x_coords) - x
        height = max(y_coords) - y
        return cls(x=x, y=y, width=width, height=height)

    def contains(self, other: 'BoundingBox') -> bool:
        return (other.y >= self.y and other.y + other.height <= self.y + self.height)


@dataclass
class BoundedElement(Generic[T]):
    content: str
    y: float
    height: float
    bbox: Optional[BoundingBox] = None

    @classmethod
    def create(cls: type[T], content: str, y: float, height: float, bbox: Optional[BoundingBox] = None) -> T:
        return cls(content=content, y=y, height=height, bbox=bbox)


@dataclass
class BoundedParagraph(BoundedElement['BoundedParagraph']):
    @classmethod
    def from_paragraph(cls, paragraph: dict) -> Optional['BoundedParagraph']:
        content = paragraph.get("content", "").strip()
        if not content:
            return None
        
        bounding_regions = paragraph.get("boundingRegions", [])
        if not bounding_regions:
            return cls.create(content=content, y=0.0, height=0.0, bbox=None)
        
        polygon = bounding_regions[0].get("polygon", [])
        bbox = BoundingBox.from_polygon(polygon) if polygon else None
        
        if bbox:
            return cls.create(content=content, y=bbox.y, height=bbox.height, bbox=bbox)
        else:
            return cls.create(content=content, y=0.0, height=0.0, bbox=None)


@dataclass
class BoundedTable(BoundedElement['BoundedTable']):
    @classmethod
    def from_cells(cls, table: dict) -> Optional['BoundedTable']:
        cells = table.get("cells", [])
        if not cells:
            return None
        
        bbox = cls._get_table_bounding_box(table)
        if not bbox:
            return None
        
        grid = cls._create_grid_from_cells(cells)
        content = cls._format_grid_as_markdown(grid)
        
        if not content.strip():
            return None
        
        return cls.create(content=content, y=bbox.y, height=bbox.height, bbox=bbox)

    @staticmethod
    def _get_table_bounding_box(table: dict) -> BoundingBox | None:
        table_regions = table.get("boundingRegions", [])
        if not table_regions:
            return None

        table_polygon = table_regions[0].get("polygon", [])
        if not table_polygon:
            return None
        
        return BoundingBox.from_polygon(table_polygon)

    @staticmethod
    def _create_grid_from_cells(cells: list) -> list:
        if not cells:
            return []

        max_row = max(cell.get("rowIndex", 0) for cell in cells)
        max_col = max(cell.get("columnIndex", 0) for cell in cells)
        grid = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]

        for cell in cells:
            row = cell.get("rowIndex", 0)
            col = cell.get("columnIndex", 0)
            content = BoundedTable._normalize_cell_text(cell.get("content", ""))
            grid[row][col] = content
        return grid

    @staticmethod
    def _normalize_cell_text(text: str) -> str:
        return text.replace(":unselected:", "").replace(":selected:", "").replace("\n", " ").strip()

    @staticmethod
    def _format_grid_as_markdown(grid: list) -> str:
        if not grid:
            return ""
        
        header, *data = grid
        table = tabulate(data, headers=header, tablefmt="pipe")
        return f"\n{table}\n"


def process_pdf_basic(upload_file: File, file_quota: FileQuota) -> str:
    processor = BasicPDFProcessor()
    return processor.extract_content(upload_file, file_quota)


def process_pdf_enhanced(upload_file: File, file_quota: FileQuota) -> str:
    processor = EnhancedPDFProcessor(endpoint=cast(str, env.azure_doc_intelligence_endpoint), key=cast(SecretStr, env.azure_doc_intelligence_key).get_secret_value())
    return processor.extract_content(upload_file, file_quota)


class BasePDFProcessor(abc.ABC):
    
    @abc.abstractmethod
    def extract_content(self, upload_file: File, file_quota: FileQuota) -> str:
        pass

    def _get_total_pages(self, content: bytes):
        pdf = PdfReader(io.BytesIO(content))
        return len(pdf.pages)
        
    def _format_pages_content(self, all_pages_content: dict) -> str:
        return "\n\n".join(f"## Page {page_num}\n{all_pages_content[page_num]}" for page_num in sorted(all_pages_content.keys()))

    def _write_pdf_chunk(self, content: bytes, start_page: int, end_page: int) -> bytes:
        try:
            pdf_reader = PdfReader(io.BytesIO(content))
            pdf_writer = PdfWriter()
            
            for page_num in range(start_page, end_page + 1):
                pdf_writer.add_page(pdf_reader.pages[page_num - 1])
            
            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.warning(f"Failed to write PDF chunk {start_page}-{end_page}: {e}. Using original content.")
            return content


class BasicPDFProcessor(BasePDFProcessor):

    def extract_content(self, upload_file: File, file_quota: FileQuota) -> str:
        content = upload_file.content
        total_pages = self._get_total_pages(content)
        all_pages_content = {}
        
        for start_page in range(1, total_pages + 1, PAGES_CHUNK_SIZE):
            end_page = min(start_page + PAGES_CHUNK_SIZE - 1, total_pages)
            
            if file_quota.has_reached_quota_limit():
                raise QuotaExceededError(f"Quota exceeded when analyzing pdf {upload_file.id} {upload_file.name}")
                
            current_content = self._format_pages_content(all_pages_content)
            if file_quota.has_reached_token_limit(current_content):
                logger.warning(f"Token limit reached when analyzing pdf {upload_file.id} {upload_file.name}. Stopping analysis at page {start_page-1}")
                break
            
            pdf_chunk = self._write_pdf_chunk(content, start_page, end_page)
            pages_content = self._process_with_pypdfium2(pdf_chunk, start_page)
            all_pages_content.update(pages_content)
            
        return self._format_pages_content(all_pages_content)

    def _process_with_pypdfium2(self, pdf_chunk: bytes, start_page_offset: int = 0) -> dict:
        pages_content = {}
        with pdfium.PdfDocument(pdf_chunk) as pdf:
            for relative_page_number, page in enumerate(pdf, start=1):
                actual_page_number = relative_page_number + start_page_offset - 1
                textpage = page.get_textpage()
                content = self._clean_pypdfium2_content(textpage.get_text_bounded())
                pages_content[actual_page_number] = content
        return pages_content

    def _clean_pypdfium2_content(self, content: str) -> str:
        return content.replace("\r", "").strip()


class EnhancedPDFProcessor(BasePDFProcessor):
    
    def __init__(self, endpoint: str, key: str):
        self.client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    
    def extract_content(self, upload_file: File, file_quota: FileQuota) -> str:
        content = upload_file.content
        total_pages = self._get_total_pages(content)
        all_pages_content = {}
        analyzed_pages = 0
        
        for start_page in range(1, total_pages + 1, PAGES_CHUNK_SIZE):
            end_page = min(start_page + PAGES_CHUNK_SIZE - 1, total_pages)
            
            if file_quota.has_reached_quota_limit():
                raise QuotaExceededError(f"Quota exceeded when analyzing pdf {upload_file.id} {upload_file.name}")
                
            current_content = self._format_pages_content(all_pages_content)
            if file_quota.has_reached_token_limit(current_content):
                logger.warning(f"Token limit reached when analyzing pdf {upload_file.id} {upload_file.name}. Stopping analysis at page {start_page-1}")
                break
            
            pdf_chunk = self._write_pdf_chunk(content, start_page, end_page)   
            chunk_pages = end_page - start_page + 1
            
            layout = self._analyze_layout(pdf_chunk)
            pages_content = self._extract_pages_content(layout, start_page)
            self._update_with_pdf_parsing_usage(file_quota, chunk_pages)
            
            all_pages_content.update(pages_content)       
            analyzed_pages += chunk_pages
            
        return self._format_pages_content(all_pages_content)

    def _analyze_layout(self, content: bytes) -> AnalyzeResult:
        request = AnalyzeDocumentRequest(bytes_source=content)
        # https://tech-depth-and-breadth.medium.com/azure-ai-document-intelligence-for-rag-use-cases-4e242b0ba7de
        poller = self.client.begin_analyze_document("prebuilt-layout", request)
        return poller.result()
    
    def _extract_pages_content(self, result: AnalyzeResult, start_page_offset: int = 0) -> dict:
        pages_content = {}
        for page in result.get("pages", []):
            relative_page_number = page.get("pageNumber", 1)
            actual_page_number = relative_page_number + start_page_offset - 1
            tables = self._get_page_elements(result, "tables", relative_page_number)
            paragraphs = self._get_page_elements(result, "paragraphs", relative_page_number)
            elements = self._create_page_elements(paragraphs, tables)
            pages_content[actual_page_number] = self._combine_elements_content(elements)
        return pages_content
    
    def _update_with_pdf_parsing_usage(self, file_quota: FileQuota, analyzed_pages: int):
        # https://azure.microsoft.com/en-us/pricing/details/ai-document-intelligence/
        file_quota.pdf_parsing_usage.increment(new_quantity=analyzed_pages, cost_per_1k_units=env.azure_doc_intelligence_cost_per_1k_pages_usd)
    
    def _get_page_elements(self, result: AnalyzeResult, element_type: str, page_number: int) -> list:
        return [element for element in result.get(element_type, []) if element.get("boundingRegions", [{}])[0].get("pageNumber", -1) == page_number]

    def _create_page_elements(self, paragraphs: list, tables: list) -> list[BoundedElement]:
        elements: list[BoundedElement] = []
        
        paragraph_elements = []
        for paragraph in paragraphs:
            paragraph_element = BoundedParagraph.from_paragraph(paragraph)
            if paragraph_element:
                paragraph_elements.append(paragraph_element)

        table_elements = []
        for table in tables:
            table_element = BoundedTable.from_cells(table)
            if table_element:
                table_elements.append(table_element)

        for paragraph_element in paragraph_elements:
            if paragraph_element.bbox and not any(table_element.bbox and table_element.bbox.contains(paragraph_element.bbox) for table_element in table_elements):
                elements.append(paragraph_element)
            elif not paragraph_element.bbox:
                elements.append(paragraph_element)

        elements.extend(table_elements)
        return elements
    
    def _combine_elements_content(self, elements: list[BoundedElement]) -> str:
        elements.sort(key=lambda x: x.y)
        return "\n".join(element.content for element in elements)
