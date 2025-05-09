import json
import os
import time

import requests
from requests import ReadTimeout

from tests.api_tests.abstract_api_test import AbstractTestApiDocReader


class TestApi(AbstractTestApiDocReader):

    def __get_version(self) -> str:
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "VERSION"))
        with open(path) as file:
            version = file.read().strip()
            return version

    def test_cancellation(self) -> None:
        file_name = "article.pdf"
        start_time = time.time()
        with open(self._get_abs_path(os.path.join("pdf_with_text_layer", file_name)), "rb") as file:
            files = {"file": (file_name, file)}
            parameters = dict(pdf_with_text_layer=False)
            try:
                requests.post(f"http://{self._get_host()}:{self._get_port()}/upload", files=files, data=parameters, timeout=1)
            except ReadTimeout:
                pass

        file_name = "example.txt"
        with open(self._get_abs_path(os.path.join("txt", file_name)), "rb") as file:
            files = {"file": (file_name, file)}
            r = requests.post(f"http://{self._get_host()}:{self._get_port()}/upload", files=files, data={}, timeout=60)

        end_time = time.time()
        self.assertLess(end_time - start_time, 60)
        self.assertEqual(200, r.status_code)

    def test_bin_file(self) -> None:
        file_name = "file.bin"
        result = self._send_request(file_name, expected_code=415)
        result = json.loads(result)
        self.assertIn("dedoc_version", result)
        self.assertEqual(file_name, result["file_name"])
        self.assertIn("metadata", result)

    def test_send_wo_file(self) -> None:
        self._send_request_wo_file(expected_code=422)

    def test_version(self) -> None:
        version = self.__get_version()
        r = requests.get(f"http://{self._get_host()}:{self._get_port()}/version")
        self.assertEqual(version, r.text.strip())

    def test_version_parsed_file(self) -> None:
        version = self.__get_version()
        result = self._send_request("csvs/books.csv")
        self.assertEqual(version, result["version"].strip())

    def test_text(self) -> None:
        file_name = "example.txt"
        result = self._send_request(os.path.join("txt", file_name), data=dict(structure_type="tree"))
        content = result["content"]["structure"]
        self.assertEqual(content["subparagraphs"][0]["text"].strip(), "Пример документа")
        self.assertEqual(content["subparagraphs"][1]["subparagraphs"][0]["text"].strip(), "1. Элемент нумерованного списка")
        self.assertEqual(content["subparagraphs"][1]["subparagraphs"][0]["metadata"]["paragraph_type"], "list_item")
        self._check_metainfo(result["metadata"], "text/plain", file_name)
