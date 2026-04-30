# Kishanganj Education Dashboard

## Project Purpose
Streamlit dashboard for NGOs operating in the education sector of Kishanganj district, Bihar. Built on UDISE+ data (2022-23 to 2024-25) covering 2,026 operational schools across all blocks.

## Stack
- Python 3.x + Streamlit
- Pandas + Plotly for data and charts
- No database — reads parquet files directly

## Data Sources (`udise_output_kishangarh/`)
| File | Rows | Content |
|---|---|---|
| `master_schools.parquet` | 2,026 | School identity, block, management type, location |
| `counts.parquet` | ~6,078 | Total enrollment + teacher counts per school-year |
| `enrolment.parquet` | 80,382 | Class × gender × category enrollment (SC, ST, OBC, General, CWSN, Muslim) |
| `facility.parquet` | 5,528 | Infrastructure: toilets, electricity, water, internet, classrooms |
| `profile.parquet` | 5,529 | Admin profile: medium of instruction, SMC, textbooks, inspections |
| `reportcard.parquet` | 5,529 | Composite: teachers, grants, programs, welfare schemes |

## Year Mapping
- yearId 9 → 2022-23
- yearId 10 → 2023-24
- yearId 11 → 2024-25

## Dashboard Sections (Policy-Driven)

### 1. District Overview (Executive Summary)
KPIs: total schools, total enrollment, GPI, PTR, % schools with electricity, % with toilets for girls

### 2. Enrollment & Access
- Year-wise total enrollment trend (boys vs girls)
- Class-wise funnel (dropout proxy: Class 1 → 5 → 8 → 10 → 12)
- Block-wise enrollment heatmap
- Gender Parity Index by block and year

### 3. Dropout Risk Analysis
- Enrollment funnel by class — cohort shrinkage = dropout signal
- Primary-to-upper-primary transition rate
- Upper-primary-to-secondary transition rate
- CWSN enrollment trend
- Muslim community enrollment (minority area context)

### 4. Teacher Analysis
- Pupil-Teacher Ratio by block
- % regular vs contracted teachers
- % female teachers (proxy for girls' school safety)
- Teacher qualification levels
- Schools with <3 teachers (single-teacher school risk)

### 5. Infrastructure Gaps
- Electricity, internet, drinking water availability
- Functional girls' toilet availability
- Classroom adequacy (enrolled students vs classrooms)
- Digital infrastructure (ICT lab, projector, computers)
- Correlation: infrastructure score vs enrollment

### 6. Governance & Accountability
- SMC (School Management Committee) formation rates
- Inspection frequency by block
- Free textbook delivery rates
- Uniform and transport provision

### 7. Block-wise Comparison
- Composite vulnerability index per block
- School density per 1000 children (est.)

## Running
```bash
pip install streamlit pandas plotly pyarrow
streamlit run dashboard.py
```

## Changelog
- 2026-04-25: Initial dashboard created from UDISE+ extraction; covers 2022-25 data

- [2026-04-25] update: OneDrive/Desktop/claude/UDISE/udise_output_kishangarh/counts.csv,OneDrive/Desktop/claude/UDISE/udise_output_kishangarh/counts.parquet,OneDrive/Desktop/claude/UDISE/udise_output_kishangarh/enrolment.csv,OneDrive/Desktop/claude/UDISE/udise_output_kishangarh/enrolment.parquet,OneDrive/Desktop/claude/UDISE/udise_output_kishangarh/facility.csv
- [2026-04-25] add Kishanganj education dashboard with 8-page Streamlit app and UDISE+ data (2022-25)
- [2026-04-26] fix three runtime errors on Streamlit Cloud: dead lambda block_infra, remove matplotlib background_gradient, switch trendline to lowess + add statsmodels
- [2026-04-26] fix mgmtShort KeyError from redundant facility merge; replace radio nav with option_menu icons; replace multiselect with checkbox+Select All filters
- [2026-04-30] update: .claude/settings.local.json
- [2026-04-30] docs(changelog): sync 2026-04-30