import csv


def validate_patient(patient_id, age, blood_pressure):
    errors = []

    if not patient_id:
        errors.append("Patient ID is missing")

    if age < 0 or age > 120:
        errors.append("Invalid age")

    if blood_pressure < 40 or blood_pressure > 250:
        errors.append("Invalid blood pressure")

    return errors


if __name__ == "__main__":
    with open("patients.csv", newline="") as file:
        reader = csv.DictReader(file)

        print("CSV columns:", reader.fieldnames)

        for row in reader:
            errors = validate_patient(
                row["patient_id"],
                int(row["age"]),
                int(row["blood_pressure"])
            )

            if errors:
                print(f"{row['patient_id']}: {errors}")
            else:
                print(f"{row['patient_id']}: Valid")
