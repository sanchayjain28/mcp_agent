"""
Script to import CSV compensation data into SQLite database.
"""
import csv
import re
from db_helper import db
from logger import logger


def clean_value(value):
    """Clean and normalize CSV values."""
    if value is None:
        return None
    value = str(value).strip()
    if value == '' or value == 'None':
        return None
    return value.lower()  


def parse_number(value):
    """Parse a number from string, handling currency and spaces."""
    if not value:
        return None
    # Remove $, spaces, and commas
    cleaned = re.sub(r'[\$,\s]', '', str(value))
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_integer(value):
    """Parse an integer from string."""
    if not value:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def import_csv_to_database(csv_file_path: str):
    """
    Import CSV file into the compensation_data table.
    
    Args:
        csv_file_path: Path to the CSV file
    """
    logger.info(f"Starting CSV import from {csv_file_path}")
    
    records_imported = 0
    records_skipped = 0
    errors = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            # Use csv.reader with proper quoting to handle multi-line fields
            reader = csv.reader(f, quotechar='"', skipinitialspace=True)
            rows = list(reader)
            
            # Find header row (should be row index 2, 0-indexed)
            header_row_idx = None
            for i, row in enumerate(rows):
                if len(row) > 10 and any('S. No.' in str(cell) for cell in row):
                    header_row_idx = i
                    break
            
            if header_row_idx is None:
                raise ValueError("Could not find header row in CSV")
            
            headers = rows[header_row_idx]
            logger.info(f"Found header row at index {header_row_idx}")
            logger.info(f"Total columns: {len(headers)}")
            
            # Process data rows (start from header_row_idx + 1)
            for row_idx, row in enumerate(rows[header_row_idx + 1:], start=header_row_idx + 1):
                try:
                    # Skip empty rows
                    if not row or all(not cell.strip() for cell in row):
                        continue
                    
                    # Check if this row has enough columns
                    if len(row) < 10:
                        continue
                    
                    combined_field = clean_value(row[0]) if len(row) > 0 else None
                    serial_no = parse_integer(row[1]) if len(row) > 1 else None
                    adjustment = clean_value(row[2]) if len(row) > 2 else None
                    num_rows = parse_integer(row[3]) if len(row) > 3 else None
                    category_counter = parse_integer(row[4]) if len(row) > 4 else None
                    category = clean_value(row[5]) if len(row) > 5 else None
                    area = clean_value(row[6]) if len(row) > 6 else None
                    tower = clean_value(row[7]) if len(row) > 7 else None
                    tower_short_code = clean_value(row[8]) if len(row) > 8 else None
                    sub_tower = clean_value(row[9]) if len(row) > 9 else None
                    sub_tower_short_code = clean_value(row[10]) if len(row) > 10 else None
                    location = clean_value(row[11]) if len(row) > 11 else None
                    role = clean_value(row[12]) if len(row) > 12 else None
                    role_short_code = clean_value(row[13]) if len(row) > 13 else None
                    experience = clean_value(row[14]) if len(row) > 14 else None
                    ipp_25th = clean_value(row[15]) if len(row) > 15 else None
                    ipp_median = clean_value(row[16]) if len(row) > 16 else None
                    ipp_75th = clean_value(row[17]) if len(row) > 17 else None
                    global_si_25th = clean_value(row[18]) if len(row) > 18 else None
                    global_si_median = clean_value(row[19]) if len(row) > 19 else None
                    global_si_75th = clean_value(row[20]) if len(row) > 20 else None
                    min_exp = parse_integer(row[21]) if len(row) > 21 else None
                    max_exp = parse_integer(row[22]) if len(row) > 22 else None
                    median_exp = parse_integer(row[23]) if len(row) > 23 else None
                    level = clean_value(row[24]) if len(row) > 24 else None
                    role_description = clean_value(row[25]) if len(row) > 25 else None
                    
                    # Build record
                    record = {
                        'combined_field': combined_field,
                        'serial_no': serial_no,
                        'adjustment': adjustment,
                        'num_rows': num_rows,
                        'category_counter': category_counter,
                        'category': category,
                        'area': area,
                        'tower': tower,
                        'tower_short_code': tower_short_code,
                        'sub_tower': sub_tower,
                        'sub_tower_short_code': sub_tower_short_code,
                        'location': location,
                        'role': role,
                        'role_short_code': role_short_code,
                        'experience': experience,
                        'ipp_25th': ipp_25th,
                        'ipp_median': ipp_median,
                        'ipp_75th': ipp_75th,
                        'global_si_25th': global_si_25th,
                        'global_si_median': global_si_median,
                        'global_si_75th': global_si_75th,
                        'min_exp': min_exp,
                        'max_exp': max_exp,
                        'median_exp': median_exp,
                        'level': level,
                        'role_description': role_description,
                    }
                    
                    try:
                        db.insert_compensation_record(record)
                        records_imported += 1
                        if records_imported % 100 == 0:
                            logger.info(f"Imported {records_imported} records...")
                    except Exception as e:
                        errors.append(f"Row {row_idx}: {str(e)}")
                        records_skipped += 1
                
                except Exception as e:
                    errors.append(f"Row {row_idx}: {str(e)}")
                    records_skipped += 1
                    continue
        
        logger.info(f"Import completed!")
        logger.info(f"Records imported: {records_imported}")
        logger.info(f"Records skipped: {records_skipped}")
        if errors:
            logger.warning(f"Errors encountered: {len(errors)}")
            if len(errors) <= 10:
                for error in errors:
                    logger.warning(f"  {error}")
            else:
                for error in errors[:10]:
                    logger.warning(f"  {error}")
                logger.warning(f"  ... and {len(errors) - 10} more errors")
    
    except Exception as e:
        logger.error(f"Failed to import CSV: {str(e)}")
        raise


if __name__ == "__main__":
    import sys
    import os
    from pathlib import Path
    
    # Default CSV file path (in parent directory)
    default_csv = Path(__file__).parent.parent / "HEX Cloud Format_latest (1) - Cloud Format_ITO.csv"
    csv_file = str(default_csv)
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        print(f"Usage: python import_csv.py [path_to_csv_file]")
        print(f"Default location: {default_csv}")
        sys.exit(1)
    
    print(f"Importing data from: {csv_file}")
    import_csv_to_database(csv_file)
    print("Import completed successfully!")

