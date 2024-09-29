
def convert_pdf2md(filename, page_range = None, backend="nougat"):

    if backend == "mupdf":
        import pymupdf
        with pymupdf.open(fname) as doc:
            raw = '\n'.join([page.get_text() for page in doc])
    elif backend == "pdfminer":
        from pdfminer.high_level import extract_text
        raw = extract_text(filename)
    elif backend == "nougat":
        from .pdf_to_md_nougat import parse_pdf
        raw, meta = parse_pdf(filename, page_range)

    return raw
