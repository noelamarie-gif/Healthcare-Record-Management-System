
import time
import csv
import statistics
from mongo_adapter import MongoAdapter

#Connect to MongoDB
adapter = MongoAdapter()

#Shared test patient and query parameters
PATIENT_ID = "166840bf-b4f9-b8f0-d1ab-010f8cba3f31"
START_DATE = "2020-01-01"
END_DATE = "2021-01-01"
LAB_CODE = "4548-4"

WARMUPS = 5
REPETITIONS = 30

tests = {
    "Patient history": lambda: adapter.get_patient_history(PATIENT_ID),

    "Lab results by date range": lambda: adapter.get_lab_results(
        PATIENT_ID, START_DATE, END_DATE
    ),

    "Monthly lab aggregation": lambda: adapter.count_lab_results_by_month(
        LAB_CODE
    )
}

results = []

for test_name, operation in tests.items():

#Warm-up runs
    for _ in range(WARMUPS):
        operation()

#Measured runs
    timings = []

    for _ in range(REPETITIONS):
        start = time.perf_counter()
        operation()
        end = time.perf_counter()

        timings.append((end - start) * 1000)

    results.append({
        "Operation": test_name,
        "Repetitions": REPETITIONS,
        "Average_ms": round(statistics.mean(timings), 3),
        "Median_ms": round(statistics.median(timings), 3),
        "Minimum_ms": round(min(timings), 3),
        "Maximum_ms": round(max(timings), 3)
    })

#Display results
print("MONGODB PERFORMANCE BENCHMARK")
print("-" * 75)

for result in results:
    print(result)

#Save results to CSV
with open("mongodb_benchmark_results.csv", "w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print("Results saved to mongodb_benchmark_results.csv")
