import os
from .base_parser import DocumentData, PageData

def parse_excel(file_path: str) -> DocumentData:
    """
    Parses Excel workbooks (.xlsx, .xls) preserving sheet names and tabular content.
    """
    filename = os.path.basename(file_path)
    pages: list[PageData] = []
    full_text_list = []

    try:
        import pandas as pd
        excel_file = pd.ExcelFile(file_path)
        
        for sheet_idx, sheet_name in enumerate(excel_file.sheet_names):
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            df_cleaned = df.dropna(how='all')
            
            table_markdown = df_cleaned.to_markdown(index=False) if not df_cleaned.empty else ""
            sheet_text = f"Sheet: {sheet_name}\n\n{table_markdown}"
            
            full_text_list.append(sheet_text)
            
            pages.append(PageData(
                page_number=sheet_idx + 1,
                text=sheet_text,
                blocks=[{
                    "text": sheet_text,
                    "type": "table",
                    "sheet_name": sheet_name,
                    "rows": len(df_cleaned),
                    "columns": list(df_cleaned.columns)
                }],
                headings=[f"Sheet: {sheet_name}"],
                is_ocr=False
            ))
    except Exception as e:
        full_text_list.append(f"Excel parsing error: {str(e)}")

    combined_text = "\n\n".join(full_text_list)
    return DocumentData(
        filename=filename,
        file_type="xlsx",
        text=combined_text,
        metadata={"parser": "pandas/openpyxl", "sheet_count": len(pages)},
        pages=pages if pages else [PageData(page_number=1, text=combined_text, blocks=[])]
    )
