"""Execution script for text chunking and paragraph splitting demonstration."""

from chunker import chunk_text, split_paragraphs

document = """
Employees receive 25 days of annual leave per year.
Employees must request leave at least 5 working days
in advance. Managers approve requests through the HR
system. Sick leave requires a medical certificate after
three consecutive days.
"""

chunks = chunk_text(
    document,
    source="employee_handbook.txt",
    max_words=20,
    overlap=5,
)

for chunk in chunks:
    print(f"\n--- Chunk {chunk.chunk_index} ---")
    print(chunk.text)


print("------=====h=====-------")
print("------=====h=====-------")
print("------=====h=====-------")


text = """
Refund Policy

Customers can request a refund within 30 days.

Shipping Policy

Shipping usually takes 3–5 business days.
"""

paragraphs = split_paragraphs(text)

for paragraph in paragraphs:
    print("---")
    print(paragraph)
