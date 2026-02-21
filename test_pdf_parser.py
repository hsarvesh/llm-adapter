import os
from parsers.document_parser import DocumentParser

def test_pdf_parsing():
    filename = "sample.pdf"
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return

    print(f"Testing PDF parsing for: {filename}")
    
    with open(filename, "rb") as f:
        file_bytes = f.read()
    
    parser = DocumentParser()
    try:
        content = parser.parse(file_bytes, filename)
        print("\n--- Extracted Content ---")
        print(content)
        print("--------------------------")
        print("\nSuccess! The PDF parser successfully extracted text.")
    except Exception as e:
        print(f"\nFailed to parse PDF: {str(e)}")

if __name__ == "__main__":
    test_pdf_parsing()
