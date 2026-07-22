import pandas as pd
import os

os.makedirs('exports', exist_ok=True)

MASTER_PATH = 'udise_output_kishangarh/master_schools.parquet'
ENROLMENT_PATH = 'udise_output_kishangarh/enrolment.parquet'

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
lgd_to_label = {v: k for k, v in PANCHAYATS.items()}

YEAR_MAP = {10: '2023-24', 11: '2024-25'}
LATEST_YEAR = '2024-25'

# NOTE: UDISE+ has no board-exam pass/fail data. "Passout" here is a proxy
# (Class 10 enrollment for the year) and "Dropout" is a same-year shrinkage
# proxy (Class 9 vs Class 10 headcount at the same school, same year) —
# NOT a true cohort (it compares two different batches of students, not the
# same students a year apart).
#
# True cross-year cohort tracking (Class 9 in year N vs Class 10 in year N+1)
# was attempted first but is not usable: 2022-23 (yearId=9) district-wide uses
# flag values 2/3 instead of the flag=1 category-total convention, and even
# 2023-24 (yearId=10) flag=1 rows exist for only 17 of these 121 schools, with
# ZERO overlap against the 104 schools that have 2024-25 flag=1 rows. So no
# school in these 7 panchayats has both years of category-total data needed
# for a same-school cohort comparison.
#
# 2023-24 figures are still reported for reference, but a school with 0 there
# may mean "no data reported that year", not "zero enrolled" — see the
# "2023-24 Data Reported" flag column.

# ---------- Load data ----------
masters = pd.read_parquet(MASTER_PATH)
enrol = pd.read_parquet(ENROLMENT_PATH)

schools_7p = masters[masters['lgdvillpanchayatName'].isin(PANCHAYATS.values())].copy()
schools_7p['panchayat'] = schools_7p['lgdvillpanchayatName'].map(lgd_to_label)
school_ids = set(schools_7p['schoolId'])

# ---------- Enrolment: Class 9 & 10, flag=1 (category totals) ----------
CLASS_COLS = ['c9B', 'c9G', 'c10B', 'c10G']

enrol_flag1 = enrol[
    (enrol['flag'] == 1) &
    (enrol['itemId'].isin([1.0, 2.0, 3.0, 4.0])) &
    (enrol['schoolId'].isin(school_ids))
]

agg = (
    enrol_flag1
    .groupby(['schoolId', 'yearId'])[CLASS_COLS]
    .sum()
    .reset_index()
)
agg['c9T'] = agg['c9B'] + agg['c9G']
agg['c10T'] = agg['c10B'] + agg['c10G']
agg['year_label'] = agg['yearId'].map(YEAR_MAP)

VALUE_COLS = ['c9B', 'c9G', 'c9T', 'c10B', 'c10G', 'c10T']

# Which schools actually reported flag=1 data each year (vs. genuinely 0)
reported_2023_24 = set(agg.loc[agg['year_label'] == '2023-24', 'schoolId'])
reported_2024_25 = set(agg.loc[agg['year_label'] == '2024-25', 'schoolId'])


def add_same_year_dropout(df):
    """Class 9 vs Class 10 headcount at the same school, in the latest well-covered year."""
    for suffix, c9key, c10key in [('Boys', 'c9B', 'c10B'), ('Girls', 'c9G', 'c10G'), ('Total', 'c9T', 'c10T')]:
        col = f"Dropout {suffix} (Cl.9 -> Cl.10, {LATEST_YEAR})"
        df[col] = df[f"{c9key}_{LATEST_YEAR}"] - df[f"{c10key}_{LATEST_YEAR}"]
    rate_col = f"Dropout Rate % (Cl.9 -> Cl.10, {LATEST_YEAR})"
    base = df[f"c9T_{LATEST_YEAR}"]
    df[rate_col] = (df[f"Dropout Total (Cl.9 -> Cl.10, {LATEST_YEAR})"] / base.replace(0, pd.NA) * 100).round(1)
    return df


DROPOUT_COLS = [
    f"Dropout Boys (Cl.9 -> Cl.10, {LATEST_YEAR})",
    f"Dropout Girls (Cl.9 -> Cl.10, {LATEST_YEAR})",
    f"Dropout Total (Cl.9 -> Cl.10, {LATEST_YEAR})",
    f"Dropout Rate % (Cl.9 -> Cl.10, {LATEST_YEAR})",
]

RENAME_MAP = {
    'schoolName': 'School Name',
    'panchayat': 'Panchayat',
    'blockName': 'Block',
    'schMgmtDescSt': 'Management',
    'classFrm': 'Class From',
    'classTo': 'Class To',
}
for year_label in YEAR_MAP.values():
    RENAME_MAP.update({
        f'c9B_{year_label}': f'Class 9 Boys {year_label}',
        f'c9G_{year_label}': f'Class 9 Girls {year_label}',
        f'c9T_{year_label}': f'Class 9 Total {year_label}',
        f'c10B_{year_label}': f'Class 10 Boys {year_label}',
        f'c10G_{year_label}': f'Class 10 Girls {year_label}',
        f'c10T_{year_label}': f'Class 10 Total {year_label}',
    })

# ============================================================
# SCHOOL-WISE
# ============================================================
META_COLS = ['schoolId', 'schoolName', 'panchayat', 'blockName', 'classFrm', 'classTo', 'schMgmtDescSt']

wide = agg.pivot_table(index='schoolId', columns='year_label', values=VALUE_COLS, aggfunc='sum').reset_index()
wide.columns = [f"{c[0]}_{c[1]}" if c[1] else c[0] for c in wide.columns]

school_result = schools_7p[META_COLS].merge(wide, on='schoolId', how='left')

for year_label in YEAR_MAP.values():
    for base in VALUE_COLS:
        col = f"{base}_{year_label}"
        if col not in school_result.columns:
            school_result[col] = 0
        school_result[col] = school_result[col].fillna(0).astype(int)

school_result['2023-24 Data Reported'] = school_result['schoolId'].isin(reported_2023_24)
school_result['2024-25 Data Reported'] = school_result['schoolId'].isin(reported_2024_25)
school_result = add_same_year_dropout(school_result)
school_result[f'SSLC Passout Proxy (Class 10 Total, {LATEST_YEAR})'] = school_result[f'c10T_{LATEST_YEAR}']

school_result = school_result.rename(columns=RENAME_MAP)

output_cols = ['School Name', 'Panchayat', 'Block', 'Management', 'Class From', 'Class To']
for year_label in YEAR_MAP.values():
    output_cols += [
        f'Class 9 Boys {year_label}', f'Class 9 Girls {year_label}', f'Class 9 Total {year_label}',
        f'Class 10 Boys {year_label}', f'Class 10 Girls {year_label}', f'Class 10 Total {year_label}',
    ]
output_cols += ['2023-24 Data Reported', '2024-25 Data Reported']
output_cols += DROPOUT_COLS
output_cols.append(f'SSLC Passout Proxy (Class 10 Total, {LATEST_YEAR})')

school_result = school_result[output_cols].sort_values(['Panchayat', 'School Name']).reset_index(drop=True)

school_out = 'exports/sslc_school_wise.csv'
school_result.to_csv(school_out, index=False)
print(f"Saved {len(school_result)} rows to {school_out}")

# ============================================================
# PANCHAYAT-WISE
# ============================================================
panchayat_agg = agg.merge(schools_7p[['schoolId', 'panchayat']], on='schoolId', how='left')
p_grouped = panchayat_agg.groupby(['panchayat', 'year_label'])[VALUE_COLS].sum().reset_index()

p_wide = p_grouped.pivot_table(index='panchayat', columns='year_label', values=VALUE_COLS, aggfunc='sum').reset_index()
p_wide.columns = [f"{c[0]}_{c[1]}" if c[1] else c[0] for c in p_wide.columns]

# Ensure every target panchayat appears, even with all-zero enrolment
p_wide = p_wide.set_index('panchayat').reindex(PANCHAYATS.keys()).reset_index()
for year_label in YEAR_MAP.values():
    for base in VALUE_COLS:
        col = f"{base}_{year_label}"
        if col not in p_wide.columns:
            p_wide[col] = 0
        p_wide[col] = p_wide[col].fillna(0).astype(int)

# Count of schools per panchayat that actually reported flag=1 data, per year
schools_reporting_2023_24 = (
    schools_7p[schools_7p['schoolId'].isin(reported_2023_24)]
    .groupby('panchayat')['schoolId'].count()
    .reindex(PANCHAYATS.keys(), fill_value=0)
)
schools_reporting_2024_25 = (
    schools_7p[schools_7p['schoolId'].isin(reported_2024_25)]
    .groupby('panchayat')['schoolId'].count()
    .reindex(PANCHAYATS.keys(), fill_value=0)
)
total_schools_per_panchayat = schools_7p.groupby('panchayat')['schoolId'].count().reindex(PANCHAYATS.keys(), fill_value=0)

p_wide = p_wide.set_index('panchayat')
p_wide['Schools Reporting 2023-24 Data'] = schools_reporting_2023_24
p_wide['Schools Reporting 2024-25 Data'] = schools_reporting_2024_25
p_wide['Total Schools'] = total_schools_per_panchayat
p_wide = p_wide.reset_index()

p_wide = add_same_year_dropout(p_wide)
p_wide[f'SSLC Passout Proxy (Class 10 Total, {LATEST_YEAR})'] = p_wide[f'c10T_{LATEST_YEAR}']

p_wide = p_wide.rename(columns=RENAME_MAP).rename(columns={'panchayat': 'Panchayat'})

p_output_cols = ['Panchayat']
for year_label in YEAR_MAP.values():
    p_output_cols += [
        f'Class 9 Boys {year_label}', f'Class 9 Girls {year_label}', f'Class 9 Total {year_label}',
        f'Class 10 Boys {year_label}', f'Class 10 Girls {year_label}', f'Class 10 Total {year_label}',
    ]
p_output_cols += ['Schools Reporting 2023-24 Data', 'Schools Reporting 2024-25 Data', 'Total Schools']
p_output_cols += DROPOUT_COLS
p_output_cols.append(f'SSLC Passout Proxy (Class 10 Total, {LATEST_YEAR})')

p_wide = p_wide[p_output_cols].sort_values('Panchayat').reset_index(drop=True)

panchayat_out = 'exports/sslc_panchayat_wise.csv'
p_wide.to_csv(panchayat_out, index=False)
print(f"Saved {len(p_wide)} rows to {panchayat_out}")

print("\nSchool-wise sample:")
print(school_result.head(5).to_string(index=False))
print("\nPanchayat-wise:")
print(p_wide.to_string(index=False))
