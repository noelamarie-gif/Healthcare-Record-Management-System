import csv
import sys
from datetime import datetime, date, timezone
from pathlib import Path

from db import db


BASE_DIR = Path(__file__).resolve().parent
CONDITIONS_CSV = BASE_DIR / "conditions.csv"
LAB_RESULTS_CSV = BASE_DIR / "lab_results.csv"


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Cannot find {path.name}. Put it in the same folder as this script."
        )
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def clean(value):
    if value is None:
        return None
    value = value.strip()
    return value if value != "" else None


def same_code(csv_value, mongo_value):
    csv_value = clean(csv_value)
    if csv_value is None:
        return mongo_value is None
    if mongo_value is None:
        return False
    return str(csv_value).strip() == str(mongo_value).strip()


def same_date(csv_value, mongo_value, date_only=False):
    csv_value = clean(csv_value)
    if csv_value is None:
        return mongo_value is None

    if not isinstance(mongo_value, datetime):
        return False

    if date_only:
        return mongo_value.date().isoformat() == csv_value[:10]

    expected = datetime.fromisoformat(csv_value.replace("Z", "+00:00"))
    if expected.tzinfo is None:
        expected = expected.replace(tzinfo=timezone.utc)

    actual = mongo_value
    if actual.tzinfo is None:
        actual = actual.replace(tzinfo=timezone.utc)
    else:
        actual = actual.astimezone(timezone.utc)

    return actual == expected.astimezone(timezone.utc)


def same_value(csv_value, mongo_value, value_type):
    csv_value = clean(csv_value)
    if csv_value is None:
        return mongo_value is None

    if value_type and value_type.strip().lower() == "numeric":
        try:
            return float(csv_value) == float(mongo_value)
        except (TypeError, ValueError):
            return False

    return str(csv_value) == str(mongo_value)


def verify_condition(csv_row, document):
    checks = {
        "START": same_date(csv_row["START"], document.get("START"), date_only=True),
        "STOP": same_date(csv_row["STOP"], document.get("STOP"), date_only=True),
        "PATIENT": clean(csv_row["PATIENT"]) == document.get("PATIENT"),
        "ENCOUNTER": clean(csv_row["ENCOUNTER"]) == document.get("ENCOUNTER"),
        "SYSTEM": clean(csv_row["SYSTEM"]) == document.get("SYSTEM"),
        "CODE": same_code(csv_row["CODE"], document.get("CODE")),
        "DESCRIPTION": clean(csv_row["DESCRIPTION"]) == document.get("DESCRIPTION"),
    }
    return [field for field, matched in checks.items() if not matched]


def verify_lab(csv_row, document):
    checks = {
        "DATE": same_date(csv_row["DATE"], document.get("DATE")),
        "PATIENT": clean(csv_row["PATIENT"]) == document.get("PATIENT"),
        "ENCOUNTER": clean(csv_row["ENCOUNTER"]) == document.get("ENCOUNTER"),
        "CATEGORY": clean(csv_row["CATEGORY"]) == document.get("CATEGORY"),
        "CODE": clean(csv_row["CODE"]) == str(document.get("CODE")),
        "DESCRIPTION": clean(csv_row["DESCRIPTION"]) == document.get("DESCRIPTION"),
        "VALUE": same_value(csv_row["VALUE"], document.get("VALUE"), csv_row["TYPE"]),
        "UNITS": clean(csv_row["UNITS"]) == document.get("UNITS"),
        "TYPE": clean(csv_row["TYPE"]) == document.get("TYPE"),
    }
    return [field for field, matched in checks.items() if not matched]


def prepare_updates(collection, rows, prefix, verifier):
    # Existing imported rows have no Id. Test records already have an Id and are excluded.
    documents = list(
        collection.find({"Id": {"$exists": False}}).sort("_id", 1)
    )

    if len(documents) != len(rows):
        raise RuntimeError(
            f"{collection.name}: CSV has {len(rows)} rows but MongoDB has "
            f"{len(documents)} documents without Id. No changes have been made."
        )

    updates = []
    errors = []

    for position, (csv_row, document) in enumerate(zip(rows, documents), start=1):
        mismatched_fields = verifier(csv_row, document)
        if mismatched_fields:
            errors.append((position, str(document["_id"]), mismatched_fields))
            if len(errors) >= 10:
                break
        else:
            updates.append({
                "document_id": document["_id"],
                "shared_id": f"{prefix}-{position}",
            })

    if errors:
        print(f"\n{collection.name}: verification FAILED.")
        for position, object_id, fields in errors:
            print(
                f"  CSV row {position}, Mongo _id {object_id}: "
                f"mismatch in {', '.join(fields)}"
            )
        raise RuntimeError(
            f"{collection.name}: found mismatches. No changes have been made."
        )

    print(
        f"{collection.name}: all {len(rows)} CSV rows match MongoDB "
        f"in _id order."
    )
    print(f"  Planned IDs: {prefix}-1 through {prefix}-{len(rows)}")
    return updates


def apply_updates(collection, updates):
    from pymongo import UpdateOne

    operations = [
        UpdateOne(
            {"_id": item["document_id"], "Id": {"$exists": False}},
            {"$set": {"Id": item["shared_id"]}},
        )
        for item in updates
    ]

    if not operations:
        return 0

    result = collection.bulk_write(operations, ordered=True)
    return result.modified_count


def main():
    apply_mode = "--apply" in sys.argv

    conditions_rows = read_csv(CONDITIONS_CSV)
    lab_rows = read_csv(LAB_RESULTS_CSV)

    print("Connected to HealthcareDB.")
    print(f"Conditions CSV rows: {len(conditions_rows)}")
    print(f"Lab results CSV rows: {len(lab_rows)}")

    condition_updates = prepare_updates(
        db.conditions, conditions_rows, "con", verify_condition
    )
    lab_updates = prepare_updates(
        db.lab_results, lab_rows, "lab", verify_lab
    )

    if not apply_mode:
        print("\nDRY RUN PASSED. MongoDB has NOT been changed.")
        print("If these results look correct, run:")
        print("    python assign_shared_ids.py --apply")
        return

    print("\nApplying shared IDs...")
    condition_count = apply_updates(db.conditions, condition_updates)
    lab_count = apply_updates(db.lab_results, lab_updates)

    print("ID assignment completed.")
    print(f"Condition IDs added: {condition_count}")
    print(f"Lab result IDs added: {lab_count}")
    print("MongoDB _id values have not been changed.")


if __name__ == "__main__":
    main()
