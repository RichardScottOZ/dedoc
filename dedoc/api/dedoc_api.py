import dataclasses
import importlib
import json
import os
import tempfile
from typing import Optional

from fastapi import Depends, FastAPI, File, Request, Response, UploadFile
from fastapi.responses import ORJSONResponse, UJSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse

import dedoc.version
from dedoc.api.api_args import QueryParameters
from dedoc.api.api_utils import json2collapsed_tree, json2html, json2tree, json2txt
from dedoc.api.process_handler import ProcessHandler
from dedoc.api.schema.parsed_document import ParsedDocument
from dedoc.common.exceptions.dedoc_error import DedocError
from dedoc.common.exceptions.missing_file_error import MissingFileError
from dedoc.config import get_config
from dedoc.utils.utils import save_upload_file

config = get_config()
logger = config["logger"]
PORT = config["api_port"]
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
static_files_dirs = config.get("static_files_dirs")

app = FastAPI()
app.mount("/web", StaticFiles(directory=config.get("static_path", static_path)), name="web")
module_api_args = importlib.import_module(config["import_path_init_api_args"])
process_handler = ProcessHandler(logger=logger)


@app.get("/")
def get_info() -> Response:
    """
    Root URL "/" is need start with simple Flask before rest-plus. API otherwise you will get 404 Error.
    It is bug of rest-plus lib.
    """
    return FileResponse(os.path.join(static_path, "index.html"))


@app.get("/static_file")
def get_static_file(request: Request) -> Response:
    path = _get_static_file_path(request)
    return FileResponse(path)


@app.get("/version")
def get_version() -> Response:
    return PlainTextResponse(dedoc.version.__version__)


def _get_static_file_path(request: Request) -> str:
    file = request.query_params.get("fname")
    directory_name = request.query_params.get("directory")
    directory = static_files_dirs[directory_name] if directory_name is not None and directory_name in static_files_dirs else static_path
    return os.path.abspath(os.path.join(directory, file))


@app.post("/upload", response_model=ParsedDocument)
async def upload(request: Request, file: UploadFile = File(...), query_params: QueryParameters = Depends()) -> Response:
    parameters = dataclasses.asdict(query_params)
    if not file or file.filename == "":
        raise MissingFileError("Error: Missing content in request_post file parameter", version=dedoc.version.__version__)

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = save_upload_file(file, tmpdir)
        document_tree = await process_handler.handle(request=request, parameters=parameters, file_path=file_path, tmpdir=tmpdir)

    if document_tree is None:
        return JSONResponse(status_code=499, content={})

    return_format = str(parameters.get("return_format", "json")).lower()
    if return_format == "html":
        html_content = json2html(
            text="",
            paragraph=document_tree.content.structure,
            tables=document_tree.content.tables,
            attachments=document_tree.attachments,
            tabs=0
        )
        return HTMLResponse(content=html_content)

    if return_format == "plain_text":
        txt_content = json2txt(paragraph=document_tree.content.structure)
        return PlainTextResponse(content=txt_content)

    if return_format == "tree":
        html_content = json2tree(paragraph=document_tree.content.structure)
        return HTMLResponse(content=html_content)

    if return_format == "ujson":
        return UJSONResponse(content=document_tree.model_dump())

    if return_format == "collapsed_tree":
        html_content = json2collapsed_tree(paragraph=document_tree.content.structure)
        return HTMLResponse(content=html_content)

    if return_format == "pretty_json":
        return PlainTextResponse(content=json.dumps(document_tree.model_dump(), ensure_ascii=False, indent=2))

    logger.info(f"Send result. File {file.filename} with parameters {parameters}")
    return ORJSONResponse(content=document_tree.model_dump())


@app.get("/upload_example")
async def upload_example(request: Request, file_name: str, return_format: Optional[str] = None) -> Response:
    file_path = os.path.join(static_path, "examples", file_name)
    parameters = {} if return_format is None else {"return_format": return_format}
    with tempfile.TemporaryDirectory() as tmpdir:
        document_tree = await process_handler.handle(request=request, parameters=parameters, file_path=file_path, tmpdir=tmpdir)

    if return_format == "html":
        html_page = json2html(
            text="",
            paragraph=document_tree.content.structure,
            tables=document_tree.content.tables,
            attachments=document_tree.attachments,
            tabs=0
        )
        return HTMLResponse(content=html_page)
    return ORJSONResponse(content=document_tree.model_dump(), status_code=200)


@app.exception_handler(DedocError)
async def exception_handler(request: Request, exc: DedocError) -> Response:
    result = {"message": exc.msg}
    if exc.filename:
        result["file_name"] = exc.filename
    if exc.version:
        result["dedoc_version"] = exc.version
    if exc.metadata:
        result["metadata"] = exc.metadata
    return JSONResponse(status_code=exc.code, content=result)


def get_api() -> FastAPI:
    return app


def run_api(app: FastAPI) -> None:
    import uvicorn
    uvicorn.run(app=app, host="0.0.0.0", port=int(PORT))
