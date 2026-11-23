from db import db


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class MongoAdapter:

    def __init__(self):
        self.db = db

    
    def get_patient_history(self, patient_id):

        patient = self.db.patients.find_one(
            {"Id": patient_id},
            {"_id": 0}
        )

        if not patient:
            raise NotFoundError("Patient not found")

        encounters_raw = list(
            self.db.encounters.find(
                {"PATIENT": patient_id},
                {"_id": 0}
            ).sort([("START", 1), ("Id", 1)])
        )

        conditions_raw = list(
            self.db.conditions.find(
                {"PATIENT": patient_id},
                {"_id": 0}
            ).sort([("START", 1), ("Id", 1)])
        )

        labs_raw = list(
            self.db.lab_results.find(
                {"PATIENT": patient_id},
                {"_id": 0}
            ).sort([("DATE", 1), ("Id", 1)])
        )

        encounters = [
            {
                "encounter_id": item.get("Id"),
                "encounter_start_date": item.get("START"),
                "encounter_end_date": item.get("STOP"),
                "encounter_class": item.get("ENCOUNTERCLASS"),
                "encounter_code": item.get("CODE"),
                "encounter_description": item.get("DESCRIPTION")
            }
            for item in encounters_raw
        ]

        conditions = [
            {
                "condition_id": item.get("Id"),
                "condition_start_date": item.get("START"),
                "condition_end_date": item.get("STOP"),
                "encounter_id": item.get("ENCOUNTER"),
                "system": item.get("SYSTEM"),
                "condition_code": item.get("CODE"),
                "condition_description": item.get("DESCRIPTION")
            }
            for item in conditions_raw
        ]

        lab_results = []

        for item in labs_raw:
            value = item.get("VALUE")
            value_type = item.get("TYPE")

            is_numeric = (
                str(value_type).lower() == "numeric"
                and isinstance(value, (int, float))
            )

            lab_results.append({
                "lab_result_id": item.get("Id"),
                "encounter_id": item.get("ENCOUNTER"),
                "lab_result_date": item.get("DATE"),
                "lab_result_category": item.get("CATEGORY"),
                "lab_result_code": item.get("CODE"),
                "lab_result_description": item.get("DESCRIPTION"),
                "lab_result_type": value_type,
                "lab_result_value_num": value if is_numeric else None,
                "lab_result_value_text": (
                    value if value is not None and not is_numeric else None
                ),
                "lab_result_unit": item.get("UNITS")
            })

        return {
            "patient_id": patient.get("Id"),
            "birth_date": patient.get("BIRTHDATE"),
            "death_date": patient.get("DEATHDATE"),
            "first_name": patient.get("FIRST"),
            "last_name": patient.get("LAST"),
            "gender": patient.get("GENDER"),
            "encounters": encounters,
            "conditions": conditions,
            "lab_results": lab_results
        }


    def get_lab_results(self, patient_id, start_date, end_date):

        # Validate date inputs
        from datetime import datetime, timezone

        try:
            start = datetime.strptime(
                start_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)

            end = datetime.strptime(
                end_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)

        except ValueError:
            raise ValidationError(
                "Dates must use YYYY-MM-DD format"
            )

        if start >= end:
            raise ValidationError(
                "Start date must be before end date"
            )

        # Check patient exists
        patient = self.db.patients.find_one(
            {"Id": patient_id}
        )

        if not patient:
            raise NotFoundError(
                f"Patient {patient_id} not found"
            )

        # Retrieve lab results
        results = self.db.lab_results.find({
            "PATIENT": patient_id,
            "DATE": {
                "$gte": start,
                "$lt": end
            }
       }).sort([
    ("DATE", 1),
    ("Id", 1)
])

        
        output = []

        for result in results:
            value = result.get("VALUE")
            value_type = result.get("TYPE")

            is_numeric = (
                str(value_type).lower() == "numeric"
                and isinstance(value, (int, float))
            )

            output.append({
                "lab_result_id": result.get("Id"),
                "encounter_id": result.get("ENCOUNTER"),
                "lab_result_date": result.get("DATE"),
                "lab_result_category": result.get("CATEGORY"),
                "lab_result_code": result.get("CODE"),
                "lab_result_description": result.get("DESCRIPTION"),
                "lab_result_type": value_type,
                "lab_result_value_num": value if is_numeric else None,
                "lab_result_value_text": (
                    value if value is not None and not is_numeric else None
                ),
                "lab_result_unit": result.get("UNITS")
            })

        return output

    
    def count_lab_results_by_month(self, code):
        from datetime import timezone

        pipeline = [
            {
                "$match": {
                    "CODE": code
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateTrunc": {
                            "date": "$DATE",
                            "unit": "month",
                            "timezone": "UTC"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {
                    "_id": 1
                }
            }
        ]

        results = self.db.lab_results.aggregate(pipeline)

        output = []

        for result in results:
            month = result["_id"]

            if month.tzinfo is None:
                month = month.replace(tzinfo=timezone.utc)
            else:
                month = month.astimezone(timezone.utc)

            output.append({
                "month": month.isoformat(),
                "count": result["count"]
            })

        return output


    def add_encounter(self, patient_id, start_time, stop_time,
                    encounter_class, code, description):

        from datetime import datetime, timezone
        from uuid import uuid4

        # Check that the patient exists
        patient = self.db.patients.find_one({"Id": patient_id})

        if not patient:
            raise NotFoundError("Patient not found")

        # Validate and parse dates
        try:
            start = datetime.fromisoformat(
                start_time.replace("Z", "+00:00")
            )

            stop = None
            if stop_time:
                stop = datetime.fromisoformat(
                    stop_time.replace("Z", "+00:00")
                )

            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)

            if stop and stop.tzinfo is None:
                stop = stop.replace(tzinfo=timezone.utc)

            if stop and stop < start:
                raise ValidationError(
                    "Stop time cannot be before start time"
                )

        except ValueError:
            raise ValidationError("Invalid date format")

        # Generate a unique encounter ID
        encounter_id = str(uuid4())

        # Create encounter document
        encounter = {
            "Id": encounter_id,
            "PATIENT": patient_id,
            "START": start,
            "STOP": stop,
            "ENCOUNTERCLASS": encounter_class,
            "CODE": str(code),
            "DESCRIPTION": description
        }

        # Save to MongoDB
        self.db.encounters.insert_one(encounter)

        return encounter_id

    def add_condition(self, patient_id, encounter_id, start_date,
                    stop_date, code_system, code, description):

        from datetime import datetime
        from uuid import uuid4

        # Check if patient exists
        patient = self.db.patients.find_one({"Id": patient_id})
        if not patient:
            raise NotFoundError("Patient not found")

        # Check if encounter belongs to this patient
        encounter = self.db.encounters.find_one({
            "Id": encounter_id,
            "PATIENT": patient_id
        })
        if not encounter:
            raise NotFoundError("Encounter not found for this patient")

        # Validate dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            stop = datetime.strptime(stop_date, "%Y-%m-%d") if stop_date else None
        except ValueError:
            raise ValidationError("Dates must use YYYY-MM-DD format")

        if stop and stop < start:
            raise ValidationError("Stop date cannot be before start date")

        condition_id = "con-" + str(uuid4())

        condition = {
            "Id": condition_id,
            "START": start,
            "STOP": stop,
            "PATIENT": patient_id,
            "ENCOUNTER": encounter_id,
            "SYSTEM": code_system,
            "CODE": str(code),
            "DESCRIPTION": description
        }

        self.db.conditions.insert_one(condition)

        return condition_id

    def add_lab_result(
        self, patient_id, encounter_id, recorded_at,
        category, code, description, value, units, value_type
    ):
        from datetime import datetime, timezone
        from uuid import uuid4

        # Check that the patient exists
        patient = self.db.patients.find_one({"Id": patient_id})
        if not patient:
            raise NotFoundError("Patient not found")

        # Check that the encounter belongs to this patient
        encounter = self.db.encounters.find_one({
            "Id": encounter_id,
            "PATIENT": patient_id
        })
        if not encounter:
            raise NotFoundError("Encounter not found for this patient")

        # Validate the result type
        if value_type not in ("numeric", "text"):
            raise ValidationError("Value type must be numeric or text")

        # Validate the value
        if value is None:
            raise ValidationError("Lab result value is required")

        if value_type == "numeric":
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValidationError("Numeric result must contain a number")

        elif value_type == "text":
            value = str(value)

        # Parse the date
        try:
            result_date = datetime.fromisoformat(
                recorded_at.replace("Z", "+00:00")
            )
            if result_date.tzinfo is None:
                result_date = result_date.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            raise ValidationError("Invalid lab result date")

        # Create the MongoDB document
        lab_result_id = "lab-" + str(uuid4())

        lab_result = {
            "Id": lab_result_id,
            "DATE": result_date,
            "PATIENT": patient_id,
            "ENCOUNTER": encounter_id,
            "CATEGORY": category,
            "CODE": str(code),
            "DESCRIPTION": description,
            "VALUE": value,
            "UNITS": units,
            "TYPE": value_type
        }

        self.db.lab_results.insert_one(lab_result)

        return lab_result_id

