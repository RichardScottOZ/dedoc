import os
from typing import Optional

from PyPDF2 import PdfFileReader
from PyPDF2.utils import PdfReadError

from dedoc.extensions import recognized_extensions, recognized_mimes
from dedoc.metadata_extractors.abstract_metadata_extractor import AbstractMetadataExtractor
from dedoc.metadata_extractors.concrete_metadata_extractors.base_metadata_extractor import BaseMetadataExtractor
from dedoc.utils.utils import convert_datetime


class PdfMetadataExtractor(AbstractMetadataExtractor):
    """
    This class is used to extract metadata from pdf documents.
    It expands metadata retrieved by :class:`~dedoc.metadata_extractors.BaseMetadataExtractor`.

    In addition to them, the following fields can be added to the metadata other fields:
        - producer;
        - creator;
        - author;
        - title;
        - subject;
        - keywords;
        - creation date;
        - modification date.
    """

    def __init__(self, *, config: Optional[dict] = None) -> None:
        super().__init__(config=config, recognized_extensions=recognized_extensions.pdf_like_format, recognized_mimes=recognized_mimes.pdf_like_format)
        self.base_extractor = BaseMetadataExtractor(config=config)
        self.keys = {
            "/Producer": "producer",
            "/Creator": "creator",
            "/Author": "author",
            "/Title": "title",
            "/Subject": "subject",
            "/Keywords": "keywords"
        }

        self.keys_date = {
            "/CreationDate": "creation_date",
            "/ModDate": "modification_date",
        }

    def extract(self,
                file_path: str,
                converted_filename: Optional[str] = None,
                original_filename: Optional[str] = None,
                parameters: Optional[dict] = None) -> dict:
        """
        Add the predefined list of metadata for the pdf documents.
        Look to the :meth:`~dedoc.metadata_extractors.AbstractMetadataExtractor.extract` documentation to get the information about parameters.
        """
        file_dir, file_name, converted_filename, original_filename = self._get_names(file_path, converted_filename, original_filename)
        base_fields = self.base_extractor.extract(
            file_path=file_path, converted_filename=converted_filename, original_filename=original_filename, parameters=parameters
        )
        pdf_fields = self._get_pdf_info(os.path.join(file_dir, converted_filename))
        result = {**base_fields, **pdf_fields}
        return result

    def _get_pdf_info(self, path: str) -> dict:
        try:
            with open(path, "rb") as file:
                document = PdfFileReader(file)
                document_info = document.getDocumentInfo() if document.getDocumentInfo() is not None else {}
                result = self.__prettify_metadata(document_info)
            return result
        except PdfReadError:
            return {"broken_pdf": True}
        except Exception as e:
            self.logger.warning(f"exception while extract pdf metadata: {path} {e}")
            if self.config.get("debug_mode", False):
                raise e
            return {"broken_pdf": True}

    def __prettify_metadata(self, document_info: dict) -> dict:
        result = {}
        for key, value in document_info.items():
            if isinstance(value, str) and len(value) > 0:
                if key in self.keys:
                    result[self.keys[key]] = value
                elif key in self.keys_date:
                    try:
                        date = convert_datetime(value)
                    except:  # noqa
                        date = None
                    if date is not None:
                        result[self.keys_date[key]] = date
        return result
