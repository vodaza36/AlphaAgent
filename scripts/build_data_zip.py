#!/usr/bin/env python3
"""
Build data/us_data.zip from existing Qlib data directory.

This script packages the Qlib binary data into a ZIP file for distribution.
It only includes SP500 symbols + benchmark indices and strips unused fields.

Usage:
    python scripts/build_data_zip.py [--source-dir PATH]
"""

import argparse
import zipfile
from pathlib import Path
from loguru import logger


def get_sp500_symbols(instruments_file: Path) -> set:
    """Extract SP500 symbols from instruments file (normalized to lowercase)."""
    symbols = set()
    if instruments_file.exists():
        with open(instruments_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if parts:
                    # Normalize to lowercase to match feature directory names
                    symbols.add(parts[0].lower())
    return symbols


def should_include_file(file_path: Path, sp500_symbols: set, features_dir: Path) -> bool:
    """
    Determine if a file should be included in the ZIP.

    Excludes:
    - Unused fields (change.day.bin, dividends.day.bin, factor.day.bin, splits.day.bin)
    - Symbols not in SP500 or benchmark indices
    - ZIP files (backups)
    """
    # Exclude ZIP files (backups)
    if file_path.suffix == '.zip':
        return False

    # Check if file is under features directory
    try:
        rel_path = file_path.relative_to(features_dir)
    except ValueError:
        # Not under features directory - include all metadata files
        return True

    # Get symbol directory
    if not rel_path.parts:
        return True

    symbol_dir = rel_path.parts[0]

    # Exclude if symbol not in SP500 list
    if symbol_dir not in sp500_symbols:
        logger.debug(f"Excluding {symbol_dir} (not in SP500)")
        return False

    # Exclude unused fields
    excluded_fields = ['change.day.bin', 'dividends.day.bin', 'factor.day.bin', 'splits.day.bin']
    if file_path.name in excluded_fields:
        logger.debug(f"Excluding {file_path.name} (unused field)")
        return False

    return True


def build_zip(source_dir: Path, output_zip: Path) -> None:
    """
    Package Qlib data directory into a ZIP file.

    Args:
        source_dir: Path to Qlib data directory (e.g., ~/.qlib/qlib_data/us_data/)
        output_zip: Path to output ZIP file (e.g., data/us_data.zip)
    """
    logger.info("=" * 60)
    logger.info("Building Data ZIP")
    logger.info("=" * 60)
    logger.info(f"Source: {source_dir}")
    logger.info(f"Output: {output_zip}")

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    # Get SP500 symbols from instruments file
    instruments_file = source_dir / "instruments" / "sp500.txt"
    sp500_symbols = get_sp500_symbols(instruments_file)
    logger.info(f"Found {len(sp500_symbols)} symbols in instruments file")

    # Add benchmark indices
    benchmark_indices = {'^GSPC', '^NDX', '^DJI'}
    sp500_symbols.update(benchmark_indices)

    features_dir = source_dir / "features"

    # Create output directory
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    # Remove old ZIP if exists
    if output_zip.exists():
        logger.info(f"Removing existing ZIP: {output_zip}")
        output_zip.unlink()

    # Create ZIP file
    logger.info("Creating ZIP file...")
    file_count = 0
    total_size = 0

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for file_path in source_dir.rglob('*'):
            if file_path.is_file():
                # Check if file should be included
                if not should_include_file(file_path, sp500_symbols, features_dir):
                    continue

                # Add to ZIP
                arcname = file_path.relative_to(source_dir)
                zipf.write(file_path, arcname)
                file_count += 1
                total_size += file_path.stat().st_size

                if file_count % 1000 == 0:
                    logger.info(f"Packed {file_count} files...")

    zip_size = output_zip.stat().st_size
    logger.info("=" * 60)
    logger.info(f"ZIP created successfully!")
    logger.info(f"Files included: {file_count}")
    logger.info(f"Original size: {total_size / (1024**2):.1f} MB")
    logger.info(f"Compressed size: {zip_size / (1024**2):.1f} MB")
    logger.info(f"Compression ratio: {(1 - zip_size/total_size) * 100:.1f}%")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Build data/us_data.zip from Qlib data directory'
    )
    parser.add_argument(
        '--source-dir',
        type=Path,
        default=Path.home() / ".qlib" / "qlib_data" / "us_data",
        help='Source Qlib data directory (default: ~/.qlib/qlib_data/us_data/)'
    )
    args = parser.parse_args()

    # Determine output ZIP path (always in project root / data / us_data.zip)
    project_root = Path(__file__).parent.parent
    output_zip = project_root / "data" / "us_data.zip"

    try:
        build_zip(args.source_dir.expanduser().resolve(), output_zip)
    except Exception as e:
        logger.error(f"Failed to build ZIP: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
