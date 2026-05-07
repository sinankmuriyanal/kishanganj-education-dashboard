import pandas as pd
import os

EXPORTS_DIR = "exports"
ENROLMENT_PATH = "udise_output_kishangarh/enrolment.parquet"
MASTER_PATH = "udise_output_kishangarh/master_schools.parquet"

PANCHAYATS = [
    "Bagalbari", "Barijan", "Bualdah", "Deramari",
    "Majgama", "Tegharia", "Kamalpur"
]

# Load all 7 panchayat school lists
frames = []
for p in PANCHAYATS:
    fpath = os.path.join(EXPORTS_DIR, f"panchayat_{p}.csv")
    df = pd.read_csv(fpath, usecols=["schoolId", "schoolName", "lgdvillpanchayatName"])
    frames.append(df)

schools_df = pd.concat(frames, ignore_index=True).drop_duplicates("schoolId")
school_ids = set(schools_df["schoolId"].tolist())

# Load enrolment, keep only latest year (yearId 11 = 2024-25), total rows (flag=1 or category aggregation)
enrol = pd.read_parquet(ENROLMENT_PATH)

# flag=1 typically means the total/all-students row; filter for it
# Let's check what flag values exist for a sample school
enrol_filtered = enrol[
    (enrol["schoolId"].isin(school_ids)) &
    (enrol["yearId"] == 11)
]

# flag=1, itemId 1-4 = General, SC, ST, OBC — mutually exclusive, sum = total enrollment
combined = (
    enrol_filtered[
        (enrol_filtered["flag"] == 1) &
        (enrol_filtered["itemId"].isin([1.0, 2.0, 3.0, 4.0]))
    ]
    .groupby("schoolId")[["c6B", "c6G", "c7B", "c7G", "c8B", "c8G"]]
    .sum()
    .reset_index()
)

# Merge with school info
result = schools_df.merge(combined, on="schoolId", how="left")

# Fill NaN with 0
for col in ["c6B", "c6G", "c7B", "c7G", "c8B", "c8G"]:
    result[col] = result[col].fillna(0).astype(int)

# Compute totals
result["c6T"] = result["c6B"] + result["c6G"]
result["c7T"] = result["c7B"] + result["c7G"]
result["c8T"] = result["c8B"] + result["c8G"]

# Rename and reorder columns
result = result.rename(columns={
    "schoolName": "School Name",
    "lgdvillpanchayatName": "Panchayat",
    "c6B": "Class 6 Boys",
    "c6G": "Class 6 Girls",
    "c6T": "Class 6 Total",
    "c7B": "Class 7 Boys",
    "c7G": "Class 7 Girls",
    "c7T": "Class 7 Total",
    "c8B": "Class 8 Boys",
    "c8G": "Class 8 Girls",
    "c8T": "Class 8 Total",
})

output_cols = [
    "School Name", "Panchayat",
    "Class 6 Boys", "Class 6 Girls", "Class 6 Total",
    "Class 7 Boys", "Class 7 Girls", "Class 7 Total",
    "Class 8 Boys", "Class 8 Girls", "Class 8 Total",
]

result = result[output_cols].sort_values(["Panchayat", "School Name"])

out_path = os.path.join(EXPORTS_DIR, "class6_7_8_school_wise.csv")
result.to_csv(out_path, index=False)
print(f"Saved {len(result)} rows to {out_path}")
print(result.to_string(index=False))
