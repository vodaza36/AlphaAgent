#!/usr/bin/env python3
"""Fix date formats in downloaded CSV files."""

from pathlib import Path
import pandas as pd
from tqdm import tqdm

SOURCE_DIR = Path(__file__).parent / "temp_us_data" / "source"

def fix_csv_date(csv_file: Path):
    """Fix date format in a single CSV file."""
    try:
        df = pd.read_csv(csv_file)

        if "date" in df.columns:
            # Convert to datetime then format as YYYY-MM-DD only
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

            # Save back to file
            df.to_csv(csv_file, index=False)
            return True
    except Exception as e:
        print(f"Error fixing {csv_file.name}: {e}")
        return False

def main():
    csv_files = list(SOURCE_DIR.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files to fix")

    fixed = 0
    for csv_file in tqdm(csv_files, desc="Fixing CSV dates"):
        if fix_csv_date(csv_file):
            fixed += 1

    print(f"Fixed {fixed}/{len(csv_files)} CSV files")

if __name__ == "__main__":
    main()
