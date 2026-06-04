from __future__ import annotations

from pathlib import Path

import pandas as pd

from prepare_phase1_templates import DATA_DIR, ROOT, TEMPLATES


OUTPUT_DIR = ROOT / "model_outputs"


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    rows = []
    for filename, required_columns in TEMPLATES.items():
        path = DATA_DIR / filename
        exists = path.exists()
        row_count = 0
        missing_columns = required_columns
        status = "MISSING_FILE"
        if exists:
            df = pd.read_csv(path)
            row_count = len(df)
            missing_columns = [c for c in required_columns if c not in df.columns]
            if missing_columns:
                status = "INVALID_SCHEMA"
            elif row_count == 0:
                status = "EMPTY_TEMPLATE"
            else:
                status = "READY_FOR_INGESTION"
        rows.append(
            {
                "dataset": filename,
                "exists": exists,
                "row_count": row_count,
                "required_columns": ",".join(required_columns),
                "missing_columns": ",".join(missing_columns),
                "status": status,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_DIR / "phase1_ingestion_status.csv", index=False, encoding="utf-8-sig")
    print(f"Wrote Phase 1 ingestion status to {OUTPUT_DIR / 'phase1_ingestion_status.csv'}")


if __name__ == "__main__":
    main()
