from werkzeug.datastructures import FileStorage

from dedoc.manager.dedoc_manager import DedocThreadedManager

manager = DedocThreadedManager()

filename = "example.docx"
with open(filename, 'rb') as fp:
    file = FileStorage(fp, filename=filename)

    parsed_document = manager.parse_file(file, parameters={"document_type": "example"})

    print(parsed_document)
    print(parsed_document.to_dict(old_version=True))
