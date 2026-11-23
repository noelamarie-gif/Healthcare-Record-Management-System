from mongo_adapter import MongoAdapter

adapter = MongoAdapter()

patient_id = "166840bf-b4f9-b8f0-d1ab-010f8cba3f31"

history = adapter.get_patient_history(patient_id)

encounter_id = history["encounters"][0]["encounter_id"]

print("ENCOUNTER VERIFICATION")
print("Encounters:", len(history["encounters"]))

for encounter in history["encounters"]:
    if encounter["encounter_description"] == "Test encounter created by MongoDB adapter":
        print("New encounter found!")
        print(encounter)

print("CONDITION INSERT TEST")

condition_id = adapter.add_condition(
    patient_id,
    encounter_id,
    "2020-01-15",
    "2020-01-15",
    "TEST-SYSTEM",
    "TEST-CONDITION-001",
    "Test condition created by MongoDB adapter"
)

print("New condition created successfully!")
print("Condition ID:", condition_id)

history = adapter.get_patient_history(patient_id)

for condition in history["conditions"]:
    if condition.get("Id") == condition_id:
        print("New condition found in patient history!")
        print(condition)

print("LAB RESULT INSERT TEST")

lab_result_id = adapter.add_lab_result(
    patient_id,
    encounter_id,
    "2020-01-15T10:30:00Z",
    "laboratory",
    "4548-4",
    "Test Hemoglobin A1c",
    6.2,
    "%",
    "numeric"
)

print("Lab result created successfully!")
print("Lab result ID:", lab_result_id)

history = adapter.get_patient_history(patient_id)
print("FULL PATIENT HISTORY VERIFICATION")
print("History keys:", list(history.keys()))
print("Encounters:", len(history.get("encounters", [])))
print("Conditions:", len(history.get("conditions", [])))
print("Lab results:", len(history.get("lab_results", [])))

print("PATIENT DETAILS")
print({
    key: history.get(key)
    for key in [
        "patient_id", "birth_date", "death_date",
        "first_name", "last_name", "gender"
    ]
})
print("LAB RESULT HISTORY VERIFICATION")
print("Total lab results:", len(history["lab_results"]))

for result in history["lab_results"]:
    if result.get("Id") == lab_result_id:
        print("New lab result found!")
        print(result)

results = adapter.get_lab_results(
    patient_id,
    "2020-01-15",
    "2020-01-16"
)

print("DATE RANGE TEST")
print("Results returned:", len(results))
print("Unique lab result IDs:", len(set(
    str(r.get("lab_result_id")) for r in results
)))

for result in results[:5]:
    print(result)

print("DATABASE:", adapter.db.name)
print("MATCHING RECORDS:", adapter.db.lab_results.count_documents({"CODE": "4548-4"}))

monthly_counts = adapter.count_lab_results_by_month("4548-4")

print("MONTHLY LAB RESULT COUNTS")
print("Number of months:", len(monthly_counts))

for item in monthly_counts:
    print(item)

print("FULL DATABASE VALIDATION")

print("Patients:", adapter.db.patients.count_documents({}))
print("Encounters:", adapter.db.encounters.count_documents({}))
print("Conditions:", adapter.db.conditions.count_documents({}))
print("Lab results:", adapter.db.lab_results.count_documents({}))

print("INDEXES")

for collection_name in ["patients", "encounters", "conditions", "lab_results"]:
    collection = adapter.db[collection_name]
    print(collection_name, list(collection.list_indexes()))

print("CREATING COMPOUND INDEXES")

adapter.db.encounters.create_index(
    [("PATIENT", 1), ("START", 1)],
    name="idx_encounter_patient_start"
)

adapter.db.lab_results.create_index(
    [("PATIENT", 1), ("DATE", 1)],
    name="idx_lab_patient_date"
)

adapter.db.lab_results.create_index(
    [("CODE", 1), ("DATE", 1)],
    name="idx_lab_code_date"
)

print("Compound indexes created successfully.")

print("VERIFYING COMPOUND INDEXES")

print("Encounters:")
for index in adapter.db.encounters.list_indexes():
    print(index["name"], index["key"])

print("Lab results:")
for index in adapter.db.lab_results.list_indexes():
    print(index["name"], index["key"])