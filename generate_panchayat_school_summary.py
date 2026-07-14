import pandas as pd
import os

os.makedirs('exports', exist_ok=True)

# User label -> LGD official panchayat name (kept in sync with export_panchayats.py)
PANCHAYATS = {
    'Bagalbari':         'Bagalbari',
    'Barijan':           'Barizan Pothimari Zagir',
    'Bualdah':           'Bualdah',
    'Deramari':          'Deramari',
    'Majgama':           'Mazgama',
    'Tegharia':          'Tegharia',
    'Kamalpur':          'Kamalpur',
}

GOVT_MGMT = {
    'Department of Education',
    'Government Aided',
    'Social Welfare Dept.',
    'Recognised/Aided Sanskrit School',
}

masters = pd.read_parquet('udise_output_kishangarh/master_schools.parquet')
schools_7p = masters[masters['lgdvillpanchayatName'].isin(PANCHAYATS.values())].copy()

schools_7p['management'] = schools_7p['schMgmtDescSt'].apply(
    lambda m: 'Govt' if m in GOVT_MGMT else 'Private'
)
schools_7p['is_primary'] = (schools_7p['classFrm'] <= 1) & (schools_7p['classTo'] >= 5)
schools_7p['is_secondary'] = (schools_7p['classFrm'] <= 9) & (schools_7p['classTo'] >= 10)
schools_7p['is_high_school'] = (schools_7p['classFrm'] <= 9) & (schools_7p['classTo'] >= 12)
schools_7p['is_higher_secondary'] = (schools_7p['classFrm'] <= 11) & (schools_7p['classTo'] >= 12)

LEVEL_COLS = ['is_primary', 'is_secondary', 'is_high_school', 'is_higher_secondary']

lgd_to_label = {v: k for k, v in PANCHAYATS.items()}
schools_7p['panchayat'] = schools_7p['lgdvillpanchayatName'].map(lgd_to_label)

summary = (
    schools_7p
    .groupby(['panchayat', 'management'])
    .agg(
        total_schools=('schoolId', 'count'),
        primary=('is_primary', 'sum'),
        secondary=('is_secondary', 'sum'),
        high_school=('is_high_school', 'sum'),
        higher_secondary=('is_higher_secondary', 'sum'),
    )
    .reset_index()
)

# Ensure both Govt and Private rows exist for every panchayat, even if 0
full_index = pd.MultiIndex.from_product(
    [PANCHAYATS.keys(), ['Govt', 'Private']], names=['panchayat', 'management']
)
summary = (
    summary.set_index(['panchayat', 'management'])
    .reindex(full_index, fill_value=0)
    .reset_index()
)

summary = summary.sort_values(['panchayat', 'management']).reset_index(drop=True)

out_path = 'exports/panchayat_school_level_summary.csv'
summary.to_csv(out_path, index=False)

print(summary.to_string(index=False))

total_row = summary[['total_schools', 'primary', 'secondary', 'high_school', 'higher_secondary']].sum()
print()
print(f"Total schools: {int(total_row['total_schools'])}")
print(f"  Govt:    {int(summary[summary['management'] == 'Govt']['total_schools'].sum())}")
print(f"  Private: {int(summary[summary['management'] == 'Private']['total_schools'].sum())}")
print(f"\n-> {out_path}")
