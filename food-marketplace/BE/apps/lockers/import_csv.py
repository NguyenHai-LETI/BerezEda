import csv
import io

from sqlmodel import Session, col, select

from apps.core.constants import MAX_LOCKER_COLUMN
from apps.lockers.crud import create_locker_unit, get_locker_location_by_id
from apps.lockers.models.unit import LockerUnit
from apps.lockers.schemas import LockerUnitImportResponse, LockerUnitRead


def import_locker_units_from_csv(
    db: Session, location_id: str, csv_content: str
) -> LockerUnitImportResponse:
    """
    Import locker units from CSV file.

    Expected CSV format:
    - Column 1: unit_number -> maps to unit_number
    - Column 2: temperature -> maps to temperature
    - Column 3: topic_name -> maps to topic_name
    - Column 4: full_unit_number -> maps to full_unit_number
    - Column 5: column_index -> physical column of the locker cabinet (1-MAX_LOCKER_COLUMN, optional)

    Args:
        db: Database session
        location_id: ID of the locker location to assign units to
        csv_content: CSV file content as string

    Returns:
        LockerUnitImportResponse with import results
    """
    errors = []
    imported_units = []
    skipped_count = 0

    # Verify location exists
    location = get_locker_location_by_id(db, location_id)
    if not location:
        return LockerUnitImportResponse(
            success=False,
            imported_count=0,
            skipped_count=0,
            errors=[f"Location with ID {location_id} not found"],
            imported_units=[],
        )

    try:
        # Parse CSV content
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)

        # Skip header row if exists (first row with unit_number, temperature, topic_name)
        data_rows = rows[1:] if len(rows) > 1 else []

        # ---- Pass 1: Parse all rows ----
        parsed_rows = []
        parse_errors = []
        parse_skipped = 0
        column_index_values = set()

        for row_index, row in enumerate(data_rows, start=2):
            if len(row) < 3:
                parse_errors.append(
                    f"Row {row_index}: Not enough columns (expected at least 3: unit_number, temperature, topic_name)"
                )
                parse_skipped += 1
                continue

            unit_number = row[0].strip()
            temperature = row[1].strip() if row[1].strip() else None
            topic_name = row[2].strip() if row[2].strip() else None
            full_unit_number = (
                row[3].strip() if len(row) > 3 and row[3].strip() else None
            )
            column_index_raw = row[4].strip() if len(row) > 4 and row[4].strip() else None
            column_index = None

            if column_index_raw is not None:
                try:
                    column_index = int(column_index_raw)
                    if not (1 <= column_index <= MAX_LOCKER_COLUMN):
                        parse_errors.append(
                            f"Row {row_index}: column_index must be between 1 and {MAX_LOCKER_COLUMN}"
                        )
                        parse_skipped += 1
                        continue
                except ValueError:
                    parse_errors.append(
                        f"Row {row_index}: column_index must be an integer, got '{column_index_raw}'"
                    )
                    parse_skipped += 1
                    continue

            if not unit_number:
                parse_errors.append(f"Row {row_index}: Empty unit_number")
                parse_skipped += 1
                continue

            # Use full_unit_number from CSV if provided, otherwise generate it
            if not full_unit_number:
                if location.code:
                    padded_unit = unit_number.zfill(3)
                    full_unit_number = f"{location.code}{padded_unit}"
                else:
                    full_unit_number = unit_number

            if column_index is not None:
                column_index_values.add(column_index)

            parsed_rows.append(
                {
                    "row_index": row_index,
                    "unit_number": unit_number,
                    "temperature": temperature,
                    "topic_name": topic_name,
                    "full_unit_number": full_unit_number,
                    "column_index": column_index,
                }
            )

        # If any parse errors, abort early
        if parse_errors:
            return LockerUnitImportResponse(
                success=False,
                imported_count=0,
                skipped_count=parse_skipped,
                errors=parse_errors,
                imported_units=[],
            )

        # ---- Validate sequential column_index ----
        if column_index_values:
            max_col = max(column_index_values)
            expected = set(range(1, max_col + 1))
            if column_index_values != expected:
                missing = sorted(expected - column_index_values)
                return LockerUnitImportResponse(
                    success=False,
                    imported_count=0,
                    skipped_count=0,
                    errors=[
                        f"column_index values must be sequential starting from 1 (e.g. 1,2,3,...). "
                        f"Missing column_index values: {missing}"
                    ],
                    imported_units=[],
                )

        # ---- Pass 2: Create units ----
        for parsed in parsed_rows:
            row_index = parsed["row_index"]
            unit_number = parsed["unit_number"]

            try:
                # Check if unit_number already exists for this location
                existing_unit_statement = select(LockerUnit).where(
                    col(LockerUnit.location_id) == location_id,
                    col(LockerUnit.unit_number) == unit_number,
                )
                existing_unit = db.exec(existing_unit_statement).first()

                if existing_unit:
                    errors.append(
                        f"Row {row_index}: Unit number '{unit_number}' already exists in this location"
                    )
                    skipped_count += 1
                    continue

                new_unit = LockerUnit(
                    location_id=location_id,
                    unit_number=unit_number,
                    full_unit_number=parsed["full_unit_number"],
                    temperature=parsed["temperature"],
                    topic_name=parsed["topic_name"],
                    column_index=parsed["column_index"],
                    status="AVAILABLE",
                    size="medium",
                    is_active=True,
                )

                created_unit = create_locker_unit(db, new_unit)
                imported_units.append(
                    LockerUnitRead.model_validate(created_unit, from_attributes=True)
                )

            except Exception as e:
                errors.append(f"Row {row_index}: Error processing row - {str(e)}")
                skipped_count += 1
                continue

    except Exception as e:
        return LockerUnitImportResponse(
            success=False,
            imported_count=0,
            skipped_count=0,
            errors=[f"Failed to parse CSV file: {str(e)}"],
            imported_units=[],
        )

    # Determine success based on whether any units were imported
    success = len(imported_units) > 0

    return LockerUnitImportResponse(
        success=success,
        imported_count=len(imported_units),
        skipped_count=skipped_count,
        errors=errors,
        imported_units=imported_units,
    )
