#!/usr/bin/env python3
"""
build_pdf.py — Project ORION Buyer Presentation PDF Package Generator
EPIC-029 Phase 0.6: Buyer Visual Presentation Package

Compiles 7 HTML print templates into publication-quality A4 PDF documents using Playwright (native Edge/Chromium):
1. Project-ORION-Executive-Brief.pdf
2. Project-ORION-Technical-Architecture.pdf
3. Project-ORION-Acquisition-IP-Scope.pdf
4. Project-ORION-Buyer-FAQ.pdf
5. Project-ORION-Demo-Operator-Sheet.pdf
6. Project-ORION-Data-Room-Guide.pdf
7. Project-ORION-Claim-Control-Matrix.pdf
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path(__file__).parent.parent / "pdf"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PDF_MAPPINGS = [
    ("executive-one-pager.html", "Project-ORION-Executive-Brief.pdf"),
    ("architecture-sheet.html", "Project-ORION-Technical-Architecture.pdf"),
    ("acquisition-ip-scope.html", "Project-ORION-Acquisition-IP-Scope.pdf"),
    ("buyer-faq.html", "Project-ORION-Buyer-FAQ.pdf"),
    ("demo-runbook.html", "Project-ORION-Demo-Operator-Sheet.pdf"),
    ("data-room-guide.html", "Project-ORION-Data-Room-Guide.pdf"),
    ("claim-control-matrix.html", "Project-ORION-Claim-Control-Matrix.pdf"),
]


import sys

def compile_pdfs(target: str | None = None):
    targets = [m for m in PDF_MAPPINGS if target is None or target in m]
    if not targets:
        print(f"[ERROR] Target '{target}' not found in PDF_MAPPINGS.")
        return

    print(f"Compiling {len(targets)} PDF document(s) from HTML templates...")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()

        for template_name, pdf_name in targets:
            template_path = TEMPLATES_DIR / template_name
            pdf_path = OUTPUT_DIR / pdf_name

            if not template_path.exists():
                print(f"  [ERROR] Template not found: {template_path}")
                continue

            file_url = template_path.resolve().as_uri()
            page.goto(file_url, wait_until="networkidle")

            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}
            )
            print(f"  [OK] Generated {pdf_name} ({pdf_path.stat().st_size} bytes)")

        browser.close()

    print(f"Compilation finished.")


if __name__ == "__main__":
    target_arg = sys.argv[1] if len(sys.argv) > 1 else None
    compile_pdfs(target_arg)
