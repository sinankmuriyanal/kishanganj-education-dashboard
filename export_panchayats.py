import pandas as pd
import os

os.makedirs('exports', exist_ok=True)

# User label → LGD official panchayat name
PANCHAYATS = {
    'Bagalbari':         'Bagalbari',
    'Barijan':           'Barizan Pothimari Zagir',  # LGD official name
    'Bualdah':           'Bualdah',
    'Deramari':          'Deramari',
    'Majgama':           'Mazgama',                  # LGD official spelling
    'Tegharia':          'Tegharia',
    'Kamalpur':          'Kamalpur',
}

YEAR_MAP = {9: '2022-23', 10: '2023-24', 11: '2024-25'}
SAMPLE_RATE = 0.298

# ---------- Load data ----------
masters = pd.read_parquet('udise_output_kishangarh/master_schools.parquet')
enrol   = pd.read_parquet('udise_output_kishangarh/enrolment.parquet')

# master_schools has one record per school (yearId=13); use as directory
schools_7p = masters[masters['lgdvillpanchayatName'].isin(PANCHAYATS.values())].copy()

# ============================================================
# PART 1 — One CSV per panchayat (all schools, key columns)
# ============================================================
SCHOOL_COLS = [
    'schoolId', 'udiseschCode', 'schoolName',
    'blockName', 'lgdvillpanchayatName', 'villageName',
    'schCatDesc', 'schTypeDesc', 'schMgmtDescSt',
    'classFrm', 'classTo', 'schLocRuralUrban', 'address',
]

print("=" * 60)
print("PART 1 — Panchayat school lists")
print("=" * 60)

for user_label, lgd_name in PANCHAYATS.items():
    subset = schools_7p[schools_7p['lgdvillpanchayatName'] == lgd_name][SCHOOL_COLS].copy()
    subset = subset.sort_values('schoolName').reset_index(drop=True)
    out_path = f'exports/panchayat_{user_label}.csv'
    subset.to_csv(out_path, index=False)
    print(f"  {user_label:12s} ({lgd_name}): {len(subset):3d} schools -> {out_path}")

# ============================================================
# PART 2 — Middle schools with class 6-8 enrollment + sample
# ============================================================
print()
print("=" * 60)
print("PART 2 — Middle school survey sample")
print("=" * 60)

# Schools with full class 6-8 coverage
middle_mask = (schools_7p['classFrm'] <= 6) & (schools_7p['classTo'] >= 8)
middle_schools = schools_7p[middle_mask].copy()
middle_ids = set(middle_schools['schoolId'])

print(f"\n  Middle schools (classFrm≤6 and classTo≥8): {len(middle_schools)}")
for user_label, lgd_name in PANCHAYATS.items():
    n = middle_schools[middle_schools['lgdvillpanchayatName'] == lgd_name].shape[0]
    print(f"    {user_label:12s}: {n}")

# Enrollment: flag=1 rows only (GENERAL+SC+ST+OBC — mutually exclusive, sum = total)
enrol_flag1 = enrol[enrol['flag'] == 1].copy()
enrol_mid   = enrol_flag1[enrol_flag1['schoolId'].isin(middle_ids)]

CLASS_COLS = ['c6B','c6G','c7B','c7G','c8B','c8G']

# Aggregate by school + year (sum across the 4 social categories)
agg = (
    enrol_mid
    .groupby(['schoolId', 'yearId'])[CLASS_COLS]
    .sum()
    .reset_index()
)
agg['boys_6_8']  = agg[['c6B','c7B','c8B']].sum(axis=1)
agg['girls_6_8'] = agg[['c6G','c7G','c8G']].sum(axis=1)
agg['total_6_8'] = agg['boys_6_8'] + agg['girls_6_8']
agg['year_label'] = agg['yearId'].map(YEAR_MAP)

# Join school metadata
META_COLS = ['schoolId','schoolName','lgdvillpanchayatName','blockName',
             'classFrm','classTo','schCatDesc','schTypeDesc','schMgmtDescSt','address']
agg = agg.merge(middle_schools[META_COLS], on='schoolId', how='left')

# --- Build wide table (one row per school, columns per year) ---
VALUE_COLS = ['c6B','c6G','c7B','c7G','c8B','c8G','boys_6_8','girls_6_8','total_6_8']
wide = agg.pivot_table(
    index=['schoolId','schoolName','lgdvillpanchayatName','blockName',
           'classFrm','classTo','schCatDesc','schTypeDesc','schMgmtDescSt','address'],
    columns='year_label',
    values=VALUE_COLS,
    aggfunc='sum',
).reset_index()

# Flatten MultiIndex columns: "c6B_2022-23" style
wide.columns = [
    f"{col[0]}_{col[1]}" if col[1] else col[0]
    for col in wide.columns
]

# --- 29.8% proportional sample based on 2024-25 enrollment ---
latest_col = 'total_6_8_2024-25'
if latest_col not in wide.columns:
    # Fallback to most recent year available
    avail = [c for c in wide.columns if c.startswith('total_6_8_')]
    latest_col = sorted(avail)[-1]
    print(f"  Warning: 2024-25 not found, using {latest_col} for sample calculation")

# Fill missing enrollment (schools with no data for the year) with 0
wide[latest_col] = wide[latest_col].fillna(0)

total_students = wide[latest_col].sum()
total_sample   = round(total_students * SAMPLE_RATE)

wide['sample_n'] = (wide[latest_col] / total_students * total_sample).round().fillna(0).astype(int)
# Ensure every school with enrolled students gets at least 1
wide.loc[(wide[latest_col] > 0) & (wide['sample_n'] == 0), 'sample_n'] = 1

# Sort: panchayat → school name
wide = wide.sort_values(['lgdvillpanchayatName','schoolName']).reset_index(drop=True)

out_path = 'exports/middle_school_survey_sample.csv'
wide.to_csv(out_path, index=False)

print(f"\n  Total students (classes 6-8, {latest_col.split('_')[-1]}): {int(total_students)}")
print(f"  29.8% sample target: {total_sample}")
print(f"  Actual allocated:    {wide['sample_n'].sum()}")
print(f"\n  Sample by panchayat:")
for user_label, lgd_name in PANCHAYATS.items():
    sub = wide[wide['lgdvillpanchayatName'] == lgd_name]
    students = int(sub[latest_col].sum())
    sample   = int(sub['sample_n'].sum())
    print(f"    {user_label:12s}: {students:4d} students -> {sample:3d} sampled")
print(f"\n  → {out_path}")

print("\nDone. All files written to exports/")
