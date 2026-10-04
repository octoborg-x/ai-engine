A good ingestion pipeline looks like:

             PDF
              │
             DOCX
              │
             TXT
              │
           Web page
              │
              ▼
           PARSER
              │
              ▼
          RAW TEXT
              │
              ▼
          CLEANING
              │
              ▼
       STRUCTURAL SPLIT
              │
              ▼
           CHUNKING
              │
              ▼
           METADATA
              │
              ▼
        EMBEDDING  ← tomorrow
              │
              ▼
        VECTOR STORE ← later
