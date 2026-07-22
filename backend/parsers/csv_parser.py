import os
from .base_parser import DocumentData, PageData

def parse_csv(file_path: str) -> DocumentData:
    """
    Parses CSV files preserving tabular header structure.
    """
    filename = os.path.basename(file_path)
    try:
        import pandas as pd
        df = pd.read_csv(file_path)
        df_cleaned = df.dropna(how='all')
        table_markdown = df_cleaned.to_markdown(index=False) if not df_cleaned.empty else ""
        content = f"CSV File: {filename}\n\n{table_markdown}"
        rows_count = len(df_cleaned)
        cols = list(df_cleaned.columns)
    except Exception:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        rows_count = len(content.splitlines())
        cols = []

    page = PageData(
        page_number=1,
        text=content,
        blocks=[{"text": content, "type": "table", "rows": rows_count, "columns": cols}],
        headings=[filename],
        is_ocr=False
    )

    return DocumentData(
        filename=filename,
        file_type="csv",
        text=content,
        metadata={"parser": "pandas/csv", "rows": rows_count},
        pages=[page]
    )
