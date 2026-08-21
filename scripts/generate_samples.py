"""Generate binary sample documents (PDF / DOCX / TXT) for upload testing.

The markdown samples are the canonical, human-readable corpus. This script
produces equivalent binary files so the PDF and DOCX ingestion paths can be
exercised directly. Re-run any time with:

    backend/.venv/bin/python scripts/generate_samples.py
"""

from __future__ import annotations

import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(HERE, "samples")


REMOTE_WORK = """Northwind Analytics - Remote Work Policy (extract)

Employees are permitted to work remotely up to 2 days per week.
Any arrangement beyond 2 days per week requires written approval
from both the direct manager and the department head.

All remote work requires manager approval. Core hours of
availability are 10:00 to 15:00 regardless of location.
"""

INCIDENT = """Northwind Analytics - Incident Response Policy (extract)

Security incidents must be reported within 1 hour of discovery to
the Incident Response Team. Delayed reporting without a valid
reason is a policy violation.

Severity levels: Low, Medium, High, Critical.
"""

HANDBOOK_TXT = """Northwind Analytics - Employee Handbook (plain text extract)

Employees receive 20 paid vacation days per year.
Standard working hours are 9:00 to 17:00, Monday through Friday.
The company is closed for the last week of December each year.
"""


def make_pdf(path: str, text: str) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 60), text, fontsize=11)
    doc.save(path)
    doc.close()


def make_docx(path: str, text: str) -> None:
    from docx import Document

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(path)


def main() -> None:
    os.makedirs(SAMPLES, exist_ok=True)
    make_pdf(os.path.join(SAMPLES, "incident-response-policy.pdf"), INCIDENT)
    make_docx(os.path.join(SAMPLES, "employee-handbook.docx"), HANDBOOK_TXT)
    with open(os.path.join(SAMPLES, "handbook-extract.txt"), "w", encoding="utf-8") as f:
        f.write(HANDBOOK_TXT)
    print("Sample documents written to", SAMPLES)


if __name__ == "__main__":
    main()
