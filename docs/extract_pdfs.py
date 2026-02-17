import pymupdf
import sys, os

for fname in ["Tạo Ảnh Reference Hoàn Chỉnh Cho VEO3.pdf", "Kịch Bản Chữ Sang Kịch Bản Video.pdf"]:
    path = os.path.join(os.path.dirname(__file__), fname)
    doc = pymupdf.open(path)
    out_name = fname.replace('.pdf', '.txt')
    out_path = os.path.join(os.path.dirname(__file__), out_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        for page in doc:
            f.write(page.get_text())
            f.write('\n--- PAGE BREAK ---\n')
    print(f"Extracted {len(doc)} pages to {out_name}")
