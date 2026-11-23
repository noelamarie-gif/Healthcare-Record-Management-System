
from mongo_adapter import MongoAdapter

adapter = MongoAdapter()
db = adapter.db

def ensure_index(collection, keys, name, unique=False):
    existing = collection.index_information()

    for index_name, details in existing.items():
        if details.get("key") == keys:
            if details.get("unique", False) == unique:
                print(f"Already exists: {index_name}")
                return
            else:
                collection.drop_index(index_name)
                print(f"Replaced: {index_name}")

    collection.create_index(
        keys,
        unique=unique,
        name=name
    )
    print(f"Created: {name}")


ensure_index(
    db.lab_results,
    [("PATIENT", 1), ("DATE", 1)],
    "idx_lab_patient_date"
)

ensure_index(
    db.lab_results,
    [("CODE", 1), ("DATE", 1)],
    "idx_lab_code_date"
)

ensure_index(
    db.encounters,
    [("PATIENT", 1), ("START", 1)],
    "idx_encounter_patient_start"
)

ensure_index(
    db.conditions,
    [("PATIENT", 1), ("START", 1)],
    "idx_condition_patient_start"
)

ensure_index(
    db.patients,
    [("Id", 1)],
    "idx_patient_id",
    unique=True
)

print("Index setup completed.")
