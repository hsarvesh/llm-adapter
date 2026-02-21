import fitz

def create_test_pdf(filename):
    doc = fitz.open()
    page = doc.new_page()
    text = "This is a test PDF file for the LLM Adapter.\n\nIt contains some text to verify that the PDF parser is working correctly.\n\nKey Points:\n1. Multi-format support.\n2. LLM integration.\n3. Telemetry and metrics."
    page.insert_text((50, 50), text)
    doc.save(filename)
    doc.close()
    print(f"Created {filename}")

if __name__ == "__main__":
    create_test_pdf("sample.pdf")
