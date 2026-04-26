import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path
from streamlit_option_menu import option_menu

st.set_page_config(
    page_title="Kishanganj Education Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = Path(__file__).parent / "udise_output_kishangarh"

YEAR_MAP = {9: "2022-23", 10: "2023-24", 11: "2024-25"}
BLOCKS = ["KOCHADHAMAN", "BAHADURGANJ", "KISHANGANJ", "TERHA GACHH", "POTHIA", "THAKURGANJ", "DIGHAL BANK"]

ELEC_MAP = {1: "Yes", 2: "No", 3: "Partial"}
YN_MAP = {1: "Yes", 2: "No", 9: "NA"}

MGMT_SHORT = {
    "Department of Education": "Govt (DoE)",
    "Madrasa Private Unaided (Recognized) ": "Madrasa Private",
    "Private Unaided (Recognized) ": "Private",
    "Unrecognized": "Unrecognized",
    "Madarsa Unrecognized": "Madrasa Unrecog.",
    "Other State Govt. Managed": "Other Govt.",
    "Madrasa Aided (Recognized)": "Madrasa Aided",
    "Social Welfare Department": "Social Welfare",
}

@st.cache_data
def load_data():
    master = pd.read_parquet(DATA_DIR / "master_schools.parquet")
    counts = pd.read_parquet(DATA_DIR / "counts.parquet")
    enrolment = pd.read_parquet(DATA_DIR / "enrolment.parquet")
    facility = pd.read_parquet(DATA_DIR / "facility.parquet")
    profile = pd.read_parquet(DATA_DIR / "profile.parquet")
    reportcard = pd.read_parquet(DATA_DIR / "reportcard.parquet")

    for df in [counts, enrolment, facility, profile, reportcard]:
        df["yearLabel"] = df["yearId"].map(YEAR_MAP)

    master["mgmtShort"] = master["schMgmtDesc"].map(MGMT_SHORT).fillna(master["schMgmtDesc"])
    master["isGovt"] = master["schMgmtDesc"].str.contains("Department of Education|Other State", na=False)
    master["isMadrasa"] = master["schMgmtDesc"].str.contains("Madrasa|Madarsa", na=False)

    # counts already has blockName/blockId/schoolName — only bring in master-only columns
    counts = counts.merge(
        master[["schoolId", "schMgmtDesc", "mgmtShort", "isGovt", "isMadrasa",
                "schLocRuralUrban", "classFrm", "classTo"]],
        on="schoolId", how="left"
    )

    # facility/profile/reportcard already have blockName — only bring in management flags
    facility = facility.merge(
        master[["schoolId", "isGovt", "isMadrasa", "mgmtShort"]],
        on="schoolId", how="left"
    )

    profile = profile.merge(
        master[["schoolId", "isGovt", "isMadrasa", "mgmtShort"]],
        on="schoolId", how="left"
    )

    reportcard = reportcard.merge(
        master[["schoolId", "isGovt", "isMadrasa", "mgmtShort"]],
        on="schoolId", how="left"
    )

    total_enrol = enrolment[enrolment["categoryLabel"].isin(["", None]) | enrolment["categoryLabel"].isna()]
    if total_enrol.empty:
        total_enrol = enrolment[enrolment["category"] == "0"]

    return master, counts, enrolment, facility, profile, reportcard, total_enrol

master, counts, enrolment, facility, profile, reportcard, total_enrol = load_data()

CLASS_COLS_B = [f"c{i}B" for i in range(1, 13)]
CLASS_COLS_G = [f"c{i}G" for i in range(1, 13)]
CLASS_LABELS = [f"Class {i}" for i in range(1, 13)]


def color_metric(val, good_threshold, warn_threshold, higher_is_better=True):
    if higher_is_better:
        if val >= good_threshold:
            return "green"
        elif val >= warn_threshold:
            return "orange"
        return "red"
    else:
        if val <= good_threshold:
            return "green"
        elif val <= warn_threshold:
            return "orange"
        return "red"


st.sidebar.markdown(
    """
    <div style='text-align:center; padding: 12px 0 4px 0;'>
        <span style='font-size:1.5rem;'>📚</span><br>
        <span style='font-weight:700; font-size:1rem; color:#1f77b4;'>Kishanganj Education</span><br>
        <span style='font-size:0.75rem; color:#6c757d;'>UDISE+ · Bihar · 2022–2025</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    page = option_menu(
        menu_title=None,
        options=[
            "District Overview",
            "Enrollment & Access",
            "Dropout Risk Analysis",
            "Teacher Analysis",
            "Infrastructure Gaps",
            "Governance & Accountability",
            "Block-wise Comparison",
            "Correlation Explorer",
        ],
        icons=[
            "house-fill",
            "people-fill",
            "graph-down-arrow",
            "person-badge-fill",
            "building-fill",
            "shield-fill-check",
            "map-fill",
            "diagram-3-fill",
        ],
        default_index=0,
        styles={
            "container": {"padding": "4px 0", "background-color": "transparent"},
            "icon": {"font-size": "13px"},
            "nav-link": {
                "font-size": "12.5px",
                "text-align": "left",
                "padding": "6px 12px",
                "border-radius": "6px",
            },
            "nav-link-selected": {
                "background-color": "#1f77b4",
                "font-weight": "600",
            },
        },
    )

st.sidebar.divider()

# ── Year filter ──────────────────────────────────────────────────────────────
with st.sidebar.expander("Academic Years", expanded=True):
    all_years = st.checkbox("Select All", value=True, key="all_years")
    year_checks = {y: st.checkbox(y, value=True, key=f"yr_{y}") for y in YEAR_MAP.values()}
    selected_years = list(YEAR_MAP.values()) if all_years else [y for y, v in year_checks.items() if v]
    if not selected_years:
        selected_years = list(YEAR_MAP.values())

# ── Block filter ─────────────────────────────────────────────────────────────
with st.sidebar.expander("Blocks", expanded=True):
    all_blocks = st.checkbox("Select All", value=True, key="all_blocks")
    block_checks = {b: st.checkbox(b.title(), value=True, key=f"blk_{b}") for b in BLOCKS}
    selected_blocks = BLOCKS if all_blocks else [b for b, v in block_checks.items() if v]
    if not selected_blocks:
        selected_blocks = BLOCKS

year_ids = [k for k, v in YEAR_MAP.items() if v in selected_years]

f_counts = counts[counts["yearId"].isin(year_ids) & counts["blockName"].isin(selected_blocks)]
f_facility = facility[facility["yearId"].isin(year_ids) & facility["blockName"].isin(selected_blocks)]
f_profile = profile[profile["yearId"].isin(year_ids) & profile["blockName"].isin(selected_blocks)]
f_rc = reportcard[reportcard["yearId"].isin(year_ids) & reportcard["blockName"].isin(selected_blocks)]
f_enrol = enrolment[enrolment["yearId"].isin(year_ids) & enrolment["schoolId"].isin(
    master[master["blockName"].isin(selected_blocks)]["schoolId"]
)]

latest_year_id = max(year_ids) if year_ids else 11
latest_counts = counts[(counts["yearId"] == latest_year_id) & counts["blockName"].isin(selected_blocks)]
latest_facility = facility[(facility["yearId"] == latest_year_id) & facility["blockName"].isin(selected_blocks)]
latest_profile = profile[(profile["yearId"] == latest_year_id) & profile["blockName"].isin(selected_blocks)]
latest_rc = reportcard[(reportcard["yearId"] == latest_year_id) & reportcard["blockName"].isin(selected_blocks)]


# ─── PAGE 1: District Overview ────────────────────────────────────────────────
if page == "District Overview":
    st.title("District Overview — Kishanganj, Bihar")
    st.caption(f"Latest data: {YEAR_MAP.get(latest_year_id, '2024-25')} | Showing {len(selected_blocks)} of 7 blocks")

    total_schools = latest_counts["schoolId"].nunique()
    total_students = latest_counts["totalCount"].sum()
    total_boys = latest_counts["totalBoy"].sum()
    total_girls = latest_counts["totalGirl"].sum()
    gpi = total_girls / total_boys if total_boys > 0 else 0

    total_teachers = latest_counts["totalTeacherReg"].fillna(0).sum() + latest_counts["totalTeacherCon"].fillna(0).sum()
    ptr = total_students / total_teachers if total_teachers > 0 else 0

    elec_yes = (latest_facility["electricityYn"] == 1).sum()
    elec_pct = elec_yes / len(latest_facility) * 100 if len(latest_facility) > 0 else 0

    toilet_g = (latest_facility["toiletgFun"] >= 1).sum()
    toilet_pct = toilet_g / len(latest_facility) * 100 if len(latest_facility) > 0 else 0

    water = (latest_facility["drinkWaterYn"] == 1).sum()
    water_pct = water / len(latest_facility) * 100 if len(latest_facility) > 0 else 0

    internet = (latest_facility["internetYn"] == 1).sum()
    internet_pct = internet / len(latest_facility) * 100 if len(latest_facility) > 0 else 0

    cols = st.columns(4)
    with cols[0]:
        st.metric("Total Schools", f"{total_schools:,}")
    with cols[1]:
        st.metric("Total Enrollment", f"{total_students:,.0f}")
    with cols[2]:
        st.metric("Gender Parity Index", f"{gpi:.2f}", help="1.0 = equal; <0.9 = girls disadvantaged")
    with cols[3]:
        st.metric("Pupil-Teacher Ratio", f"{ptr:.1f}:1", help="National norm: 30:1 (Primary), 35:1 (Upper)")

    cols2 = st.columns(4)
    with cols2[0]:
        st.metric("Schools with Electricity", f"{elec_pct:.1f}%")
    with cols2[1]:
        st.metric("Schools with Girls' Toilet", f"{toilet_pct:.1f}%")
    with cols2[2]:
        st.metric("Schools with Drinking Water", f"{water_pct:.1f}%")
    with cols2[3]:
        st.metric("Schools with Internet", f"{internet_pct:.1f}%")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("School Management Type")
        mgmt_counts = master[master["blockName"].isin(selected_blocks)]["mgmtShort"].value_counts().reset_index()
        mgmt_counts.columns = ["Management Type", "Schools"]
        fig = px.pie(mgmt_counts, names="Management Type", values="Schools",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("School Location: Rural vs Urban")
        loc_data = master[master["blockName"].isin(selected_blocks)]["schLocRuralUrban"].map({1: "Rural", 2: "Urban"}).value_counts().reset_index()
        loc_data.columns = ["Location", "Schools"]
        fig2 = px.bar(loc_data, x="Location", y="Schools",
                      color="Location", color_discrete_sequence=["#2ecc71", "#3498db"])
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Block-wise School Count")
    block_counts = master[master["blockName"].isin(selected_blocks)]["blockName"].value_counts().reset_index()
    block_counts.columns = ["Block", "Schools"]
    fig3 = px.bar(block_counts, x="Block", y="Schools", color="Schools",
                  color_continuous_scale="Blues", text="Schools")
    fig3.update_traces(textposition="outside")
    st.plotly_chart(fig3, use_container_width=True)

    st.divider()
    st.subheader("Medium of Instruction")
    med = f_profile["mediumOfInstrName1"].value_counts().reset_index()
    med.columns = ["Medium", "Count"]
    fig4 = px.bar(med, x="Medium", y="Count", color="Medium",
                  color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig4, use_container_width=True)

    st.info(
        "**Policy Note:** Kishanganj has a high proportion of Madrasa schools (~17%) and Urdu-medium instruction, "
        "reflecting the district's significant Muslim population. NGO programs must account for this religious-education "
        "ecosystem and engage with Madrasa management separately from government schools."
    )


# ─── PAGE 2: Enrollment & Access ─────────────────────────────────────────────
elif page == "Enrollment & Access":
    st.title("Enrollment & Access")

    year_enrol = f_counts.groupby("yearLabel").agg(
        Boys=("totalBoy", "sum"), Girls=("totalGirl", "sum"), Total=("totalCount", "sum")
    ).reset_index()
    year_enrol["GPI"] = year_enrol["Girls"] / year_enrol["Boys"]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Year-wise Enrollment Trend")
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Boys", x=year_enrol["yearLabel"], y=year_enrol["Boys"],
                             marker_color="#3498db"))
        fig.add_trace(go.Bar(name="Girls", x=year_enrol["yearLabel"], y=year_enrol["Girls"],
                             marker_color="#e74c3c"))
        fig.update_layout(barmode="group", xaxis_title="Year", yaxis_title="Students")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Gender Parity Index (GPI) Trend")
        fig2 = px.line(year_enrol, x="yearLabel", y="GPI", markers=True,
                       color_discrete_sequence=["#9b59b6"])
        fig2.add_hline(y=1.0, line_dash="dash", line_color="green",
                       annotation_text="Parity (1.0)")
        fig2.add_hline(y=0.9, line_dash="dot", line_color="orange",
                       annotation_text="Warning (0.9)")
        fig2.update_layout(yaxis_title="GPI (Girls/Boys)")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Block-wise Enrollment (Latest Year)")

    block_enrol = latest_counts.groupby("blockName").agg(
        Boys=("totalBoy", "sum"),
        Girls=("totalGirl", "sum"),
        Total=("totalCount", "sum")
    ).reset_index()
    block_enrol["GPI"] = block_enrol["Girls"] / block_enrol["Boys"]
    block_enrol = block_enrol.sort_values("Total", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(block_enrol, x="blockName", y=["Boys", "Girls"], barmode="group",
                     color_discrete_sequence=["#3498db", "#e74c3c"],
                     labels={"blockName": "Block", "value": "Students"})
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig2 = px.bar(block_enrol, x="blockName", y="GPI",
                      color="GPI", color_continuous_scale="RdYlGn",
                      labels={"blockName": "Block"}, text=block_enrol["GPI"].round(2))
        fig2.add_hline(y=1.0, line_dash="dash", line_color="black")
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Enrollment by School Management Type (Latest Year)")

    mgmt_enrol = latest_counts.groupby("mgmtShort").agg(
        Total=("totalCount", "sum"),
        Schools=("schoolId", "count")
    ).reset_index()
    mgmt_enrol["AvgPerSchool"] = (mgmt_enrol["Total"] / mgmt_enrol["Schools"]).round(1)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.treemap(mgmt_enrol, path=["mgmtShort"], values="Total",
                         title="Total Enrollment Share by Management")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = px.bar(mgmt_enrol.sort_values("AvgPerSchool"), x="AvgPerSchool", y="mgmtShort",
                      orientation="h", color="AvgPerSchool", color_continuous_scale="Blues",
                      labels={"mgmtShort": "Management", "AvgPerSchool": "Avg Students/School"})
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Special Needs & Minority Enrollment")

    cwsn = f_enrol[f_enrol["categoryLabel"] == "CWSN"]
    cwsn_yr = cwsn.groupby("yearLabel")["rowTotal"].sum().reset_index()
    cwsn_yr.columns = ["Year", "CWSN Students"]

    muslim = f_enrol[f_enrol["categoryLabel"] == "Muslim"]
    muslim_yr = muslim.groupby("yearLabel")["rowTotal"].sum().reset_index()
    muslim_yr.columns = ["Year", "Muslim Students"]

    c1, c2 = st.columns(2)
    with c1:
        st.caption("Children with Special Needs (CWSN) Enrollment")
        fig = px.bar(cwsn_yr, x="Year", y="CWSN Students",
                     color_discrete_sequence=["#f39c12"], text="CWSN Students")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.caption("Muslim Community Enrollment")
        fig2 = px.bar(muslim_yr, x="Year", y="Muslim Students",
                      color_discrete_sequence=["#1abc9c"], text="Muslim Students")
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    st.info(
        "**Policy Note:** Kishanganj has one of Bihar's highest Muslim population shares (~68%). Muslim enrollment "
        "data helps track whether community children are in mainstream schools vs. only Madrasas. Low GPI in "
        "specific blocks often correlates with out-of-school girls, especially at secondary level."
    )


# ─── PAGE 3: Dropout Risk Analysis ───────────────────────────────────────────
elif page == "Dropout Risk Analysis":
    st.title("Dropout Risk Analysis")
    st.caption(
        "Class-wise enrollment shrinkage is used as a proxy for dropouts. "
        "A sharp drop between classes signals a critical intervention point."
    )

    all_categories = f_enrol["categoryLabel"].unique().tolist()
    total_cats = [c for c in all_categories if c in ("", None) or pd.isna(c)]
    if total_cats:
        funnel_data = f_enrol[f_enrol["categoryLabel"].isin(total_cats) | f_enrol["categoryLabel"].isna()]
    else:
        non_sub = [c for c in all_categories if c not in
                   ["CWSN", "Repeater", "SC", "ST", "OBC", "General", "Muslim",
                    "Christian", "Sikh", "Buddhist", "Parsi", "Jain", "BPL", "EWS", "RTE"]]
        funnel_data = f_enrol[f_enrol["categoryLabel"].isin(non_sub)]

    if funnel_data.empty:
        funnel_data = f_enrol[f_enrol["category"].astype(str) == "0"]

    if funnel_data.empty:
        funnel_data = f_enrol

    class_total_b = funnel_data[CLASS_COLS_B].sum()
    class_total_g = funnel_data[CLASS_COLS_G].sum()

    funnel_df = pd.DataFrame({
        "Class": CLASS_LABELS,
        "Boys": class_total_b.values,
        "Girls": class_total_g.values,
    })
    funnel_df["Total"] = funnel_df["Boys"] + funnel_df["Girls"]

    st.subheader("Enrollment Funnel: Class 1 → Class 12")

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Boys", x=funnel_df["Class"], y=funnel_df["Boys"],
                             marker_color="#3498db"))
        fig.add_trace(go.Bar(name="Girls", x=funnel_df["Class"], y=funnel_df["Girls"],
                             marker_color="#e74c3c"))
        fig.update_layout(barmode="stack", xaxis_title="Class", yaxis_title="Enrolled Students",
                          xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        c1_total = funnel_df.loc[funnel_df["Class"] == "Class 1", "Total"].values[0]
        funnel_df["RetentionPct"] = funnel_df["Total"] / c1_total * 100 if c1_total > 0 else 0

        fig2 = px.line(funnel_df, x="Class", y="RetentionPct", markers=True,
                       color_discrete_sequence=["#e67e22"],
                       labels={"RetentionPct": "% of Class 1 Enrollment"})
        fig2.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="Class 1 Baseline")
        fig2.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Transition Rate Analysis")

    def transition(df, from_classes, to_classes):
        from_total = df[[f"c{c}B" for c in from_classes] + [f"c{c}G" for c in from_classes]].sum().sum()
        to_total = df[[f"c{c}B" for c in to_classes] + [f"c{c}G" for c in to_classes]].sum().sum()
        return (to_total / from_total * 100) if from_total > 0 else 0

    pri_to_upr = transition(funnel_data, [5], [6])
    upr_to_sec = transition(funnel_data, [8], [9])
    sec_to_hsec = transition(funnel_data, [10], [11])

    col1, col2, col3 = st.columns(3)
    with col1:
        delta_color = "normal" if pri_to_upr >= 80 else "inverse"
        st.metric("Primary → Upper Primary", f"{pri_to_upr:.1f}%",
                  help="Class 5 to Class 6 enrollment ratio")
        if pri_to_upr < 80:
            st.error("Below 80% — High dropout risk at Class 5-6 transition")
    with col2:
        st.metric("Upper Primary → Secondary", f"{upr_to_sec:.1f}%",
                  help="Class 8 to Class 9 enrollment ratio")
        if upr_to_sec < 70:
            st.error("Critical dropout zone at Class 8-9 transition")
    with col3:
        st.metric("Secondary → Higher Secondary", f"{sec_to_hsec:.1f}%",
                  help="Class 10 to Class 11 enrollment ratio")
        if sec_to_hsec < 60:
            st.warning("Significant attrition after Class 10")

    st.divider()
    st.subheader("Year-wise Funnel Comparison")

    funnel_by_year = []
    for yid in year_ids:
        yr_data = enrolment[enrolment["yearId"] == yid]
        if total_cats:
            yr_data = yr_data[yr_data["categoryLabel"].isin(total_cats) | yr_data["categoryLabel"].isna()]
        for i, label in enumerate(CLASS_LABELS):
            b = yr_data[CLASS_COLS_B[i]].sum()
            g = yr_data[CLASS_COLS_G[i]].sum()
            funnel_by_year.append({
                "Year": YEAR_MAP[yid], "Class": label, "Boys": b, "Girls": g, "Total": b + g
            })

    funnel_yr_df = pd.DataFrame(funnel_by_year)
    fig = px.line(funnel_yr_df, x="Class", y="Total", color="Year", markers=True,
                  color_discrete_sequence=px.colors.qualitative.Set1)
    fig.update_layout(xaxis_tickangle=-45, yaxis_title="Total Enrolled")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Block-wise Dropout Risk: Schools with <10 Students in Class 9+")

    school_ids = master[master["blockName"].isin(selected_blocks)]["schoolId"].tolist()
    risk_enrol = enrolment[
        (enrolment["yearId"] == latest_year_id) &
        (enrolment["schoolId"].isin(school_ids))
    ]
    if total_cats:
        risk_enrol = risk_enrol[risk_enrol["categoryLabel"].isin(total_cats) | risk_enrol["categoryLabel"].isna()]

    risk_enrol["sec_total"] = risk_enrol[["c9B", "c9G", "c10B", "c10G"]].sum(axis=1)
    high_risk = risk_enrol[risk_enrol["sec_total"] < 10].merge(
        master[["schoolId", "blockName", "schoolName"]], on="schoolId", how="left"
    )
    risk_block = high_risk.groupby("blockName").size().reset_index(name="At-Risk Schools")

    fig = px.bar(risk_block.sort_values("At-Risk Schools", ascending=False),
                 x="blockName", y="At-Risk Schools",
                 color="At-Risk Schools", color_continuous_scale="Reds",
                 labels={"blockName": "Block"}, text="At-Risk Schools")
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "**Policy Note:** The Class 5→6 and Class 8→9 transitions are the two critical dropout points in "
        "Kishanganj. Girls drop out disproportionately here, often due to absence of upper-primary and secondary "
        "schools within walking distance, lack of girls' toilets, or family pressure. NGO interventions like "
        "bridge camps, conditional cash transfers, and community awareness are most effective at these junctions."
    )


# ─── PAGE 4: Teacher Analysis ─────────────────────────────────────────────────
elif page == "Teacher Analysis":
    st.title("Teacher Analysis")

    st.subheader("Pupil-Teacher Ratio by Block (Latest Year)")
    block_rc = latest_rc.groupby("blockName").agg(
        TotalTeachers=("totalTeacher", "sum"),
        RegTeachers=("tchReg", "sum"),
        ContTeachers=("tchCont", "sum"),
        MaleTeachers=("totMale", "sum"),
        FemaleTeachers=("totFemale", "sum"),
        Schools=("schoolId", "count"),
        BelowGrad=("totTchBelowGraduate", "sum"),
        GradAbove=("totTchGraduateAbove", "sum"),
        PostGrad=("totTchPgraduateAbove", "sum"),
        ServiceTrained=("tchRecvdServiceTrng", "sum"),
    ).reset_index()

    block_students = latest_counts.groupby("blockName")["totalCount"].sum().reset_index()
    block_rc = block_rc.merge(block_students, on="blockName", how="left")
    block_rc["PTR"] = block_rc["totalCount"] / block_rc["TotalTeachers"].replace(0, np.nan)
    block_rc["FemalePct"] = block_rc["FemaleTeachers"] / block_rc["TotalTeachers"].replace(0, np.nan) * 100
    block_rc["RegPct"] = block_rc["RegTeachers"] / block_rc["TotalTeachers"].replace(0, np.nan) * 100
    block_rc["QualPct"] = (block_rc["GradAbove"] + block_rc["PostGrad"]) / block_rc["TotalTeachers"].replace(0, np.nan) * 100

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(block_rc.sort_values("PTR"), x="PTR", y="blockName",
                     orientation="h", color="PTR",
                     color_continuous_scale="RdYlGn_r",
                     labels={"blockName": "Block", "PTR": "Pupil:Teacher Ratio"},
                     text=block_rc.sort_values("PTR")["PTR"].round(1))
        fig.add_vline(x=30, line_dash="dash", line_color="green", annotation_text="Norm (30:1)")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("% Female Teachers by Block")
        fig2 = px.bar(block_rc.sort_values("FemalePct"), x="FemalePct", y="blockName",
                      orientation="h", color="FemalePct",
                      color_continuous_scale="Purples",
                      labels={"blockName": "Block", "FemalePct": "% Female Teachers"},
                      text=block_rc.sort_values("FemalePct")["FemalePct"].round(1))
        fig2.add_vline(x=50, line_dash="dash", line_color="purple", annotation_text="50%")
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Teacher Type: Regular vs Contracted")

    tc_data = latest_rc.groupby("schMgmtStateDesc").agg(
        Regular=("tchReg", "sum"),
        Contracted=("tchCont", "sum"),
        PartTime=("tchPart", "sum"),
    ).reset_index().head(8)

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Regular", x=tc_data["schMgmtStateDesc"], y=tc_data["Regular"],
                         marker_color="#2ecc71"))
    fig.add_trace(go.Bar(name="Contracted", x=tc_data["schMgmtStateDesc"], y=tc_data["Contracted"],
                         marker_color="#f39c12"))
    fig.add_trace(go.Bar(name="Part-Time", x=tc_data["schMgmtStateDesc"], y=tc_data["PartTime"],
                         marker_color="#e74c3c"))
    fig.update_layout(barmode="stack", xaxis_title="Management Type", yaxis_title="Teachers",
                      xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Teacher Qualification Distribution")
        qual_df = pd.DataFrame({
            "Qualification": ["Below Graduate", "Graduate+", "Post-Graduate+"],
            "Count": [
                latest_rc["totTchBelowGraduate"].sum(),
                latest_rc["totTchGraduateAbove"].sum(),
                latest_rc["totTchPgraduateAbove"].sum(),
            ]
        })
        fig = px.pie(qual_df, names="Qualification", values="Count",
                     color_discrete_sequence=["#e74c3c", "#3498db", "#2ecc71"])
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Schools with Critical Teacher Shortage (<3 Teachers)")
        counts_with_block = latest_counts.copy()
        counts_with_block["totalTeacher"] = counts_with_block["totalTeacherReg"].fillna(0) + counts_with_block["totalTeacherCon"].fillna(0)
        shortage = counts_with_block[counts_with_block["totalTeacher"] < 3]
        shortage_block = shortage.groupby("blockName").size().reset_index(name="Schools")
        fig2 = px.bar(shortage_block.sort_values("Schools", ascending=False),
                      x="blockName", y="Schools",
                      color="Schools", color_continuous_scale="Reds",
                      labels={"blockName": "Block"}, text="Schools")
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Year-wise Teacher Count Trend")
    yr_teachers = f_rc.groupby("yearLabel").agg(
        Regular=("tchReg", "sum"),
        Contracted=("tchCont", "sum"),
        Total=("totalTeacher", "sum"),
        Female=("totFemale", "sum"),
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(name="Total", x=yr_teachers["yearLabel"], y=yr_teachers["Total"],
                             mode="lines+markers", line=dict(color="#2c3e50", width=2)))
    fig.add_trace(go.Scatter(name="Regular", x=yr_teachers["yearLabel"], y=yr_teachers["Regular"],
                             mode="lines+markers", line=dict(color="#2ecc71", width=2)))
    fig.add_trace(go.Scatter(name="Contracted", x=yr_teachers["yearLabel"], y=yr_teachers["Contracted"],
                             mode="lines+markers", line=dict(color="#f39c12", width=2)))
    fig.add_trace(go.Scatter(name="Female", x=yr_teachers["yearLabel"], y=yr_teachers["Female"],
                             mode="lines+markers", line=dict(color="#9b59b6", width=2)))
    fig.update_layout(yaxis_title="Teachers", xaxis_title="Year")
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "**Policy Note:** High PTR (>40:1) in certain blocks indicates teacher shortage and correlates with "
        "poor learning outcomes. Low female teacher presence (<30%) is a barrier for girl enrollment at "
        "secondary level — families in conservative areas are more likely to send daughters to school when "
        "female teachers are present. NGOs should advocate for teacher posting policies that prioritize "
        "blocks with high PTR and low female teacher share."
    )


# ─── PAGE 5: Infrastructure Gaps ─────────────────────────────────────────────
elif page == "Infrastructure Gaps":
    st.title("Infrastructure Gaps")

    infra_agg = latest_facility.copy()
    infra_agg["has_electricity"] = infra_agg["electricityYn"] == 1
    infra_agg["has_water"] = infra_agg["drinkWaterYn"] == 1
    infra_agg["has_girls_toilet"] = infra_agg["toiletgFun"] >= 1
    infra_agg["has_boys_toilet"] = infra_agg["toiletbFun"] >= 1
    infra_agg["has_internet"] = infra_agg["internetYn"] == 1
    infra_agg["has_library"] = infra_agg["libraryYn"] == 1
    infra_agg["has_playground"] = infra_agg["playgroundYn"] == 1
    infra_agg["has_ict_lab"] = infra_agg["ictLabYn"] == 1
    infra_agg["has_handwash"] = infra_agg["handwashYn"] == 1
    infra_agg["has_ramp"] = infra_agg["rampsYn"] == 1

    infra_cols = {
        "Electricity": "has_electricity",
        "Drinking Water": "has_water",
        "Girls' Toilet": "has_girls_toilet",
        "Boys' Toilet": "has_boys_toilet",
        "Hand-wash Facility": "has_handwash",
        "Library": "has_library",
        "Playground": "has_playground",
        "Internet": "has_internet",
        "ICT Lab": "has_ict_lab",
        "Ramp (Accessibility)": "has_ramp",
    }

    total = len(infra_agg)
    infra_summary = pd.DataFrame([
        {"Infrastructure": k, "Available": int(infra_agg[v].sum()),
         "Missing": total - int(infra_agg[v].sum()),
         "Pct": infra_agg[v].mean() * 100}
        for k, v in infra_cols.items()
    ]).sort_values("Pct", ascending=True)

    st.subheader("Infrastructure Availability — All Schools (Latest Year)")
    fig = px.bar(infra_summary, x="Pct", y="Infrastructure",
                 orientation="h", color="Pct",
                 color_continuous_scale="RdYlGn",
                 labels={"Pct": "% Schools with Access"},
                 text=infra_summary["Pct"].round(1))
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(xaxis_range=[0, 110])
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Block-wise Infrastructure Scorecard")

    block_infra = latest_facility.groupby("blockName").agg(
        electricity=("electricityYn", lambda x: (x == 1).mean() * 100),
        water=("drinkWaterYn", lambda x: (x == 1).mean() * 100),
        girls_toilet=("toiletgFun", lambda x: (x >= 1).mean() * 100),
        internet=("internetYn", lambda x: (x == 1).mean() * 100),
        library=("libraryYn", lambda x: (x == 1).mean() * 100),
        playground=("playgroundYn", lambda x: (x == 1).mean() * 100),
    ).reset_index()

    block_infra["InfraScore"] = block_infra[["electricity", "water", "girls_toilet",
                                               "internet", "library", "playground"]].mean(axis=1)

    fig = px.imshow(
        block_infra.set_index("blockName")[["electricity", "water", "girls_toilet",
                                             "internet", "library", "playground"]].round(1),
        labels=dict(x="Infrastructure", y="Block", color="% Schools"),
        color_continuous_scale="RdYlGn", aspect="auto",
        text_auto=True
    )
    fig.update_xaxes(ticktext=["Electricity", "Water", "Girls Toilet",
                                "Internet", "Library", "Playground"],
                     tickvals=list(range(6)))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Digital Infrastructure by School Type")
        digital = latest_facility.copy()  # mgmtShort already present from load_data merge
        digi_grp = digital.groupby("mgmtShort").agg(
            computers=("desktopFun", "sum"),
            tablets=("tabletsTot", "sum"),
            projectors=("projectorTot", "sum"),
            laptops=("laptopTot", "sum"),
        ).reset_index().head(5)

        fig = px.bar(digi_grp, x="mgmtShort", y=["computers", "tablets", "projectors", "laptops"],
                     barmode="group",
                     labels={"mgmtShort": "School Type", "value": "Count"},
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(xaxis_tickangle=-20)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Electricity Availability by Year")
        yr_elec = f_facility.groupby("yearLabel").apply(
            lambda x: pd.Series({
                "With Electricity": (x["electricityYn"] == 1).mean() * 100,
                "Without Electricity": (x["electricityYn"] == 2).mean() * 100,
                "Partial": (x["electricityYn"] == 3).mean() * 100,
            })
        ).reset_index()

        fig2 = go.Figure()
        for col, color in [("With Electricity", "#2ecc71"), ("Partial", "#f39c12"),
                            ("Without Electricity", "#e74c3c")]:
            fig2.add_trace(go.Bar(name=col, x=yr_elec["yearLabel"], y=yr_elec[col],
                                  marker_color=color))
        fig2.update_layout(barmode="stack", yaxis_title="% Schools")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Classroom Condition Analysis")

    cls_data = latest_facility.copy()
    cls_data["classroom_need"] = cls_data["clsrmsMaj"].fillna(0) + cls_data["clsrmsMin"].fillna(0)
    cls_data["has_damage"] = cls_data["classroom_need"] > 0

    dmg_block = cls_data.groupby("blockName").agg(
        Schools=("schoolId", "count"),
        WithDamage=("has_damage", "sum"),
        MajorRepair=("clsrmsMaj", "sum"),
        MinorRepair=("clsrmsMin", "sum"),
    ).reset_index()
    dmg_block["DamagePct"] = dmg_block["WithDamage"] / dmg_block["Schools"] * 100

    fig = px.bar(dmg_block.sort_values("DamagePct", ascending=False),
                 x="blockName", y="DamagePct",
                 color="DamagePct", color_continuous_scale="Reds",
                 labels={"blockName": "Block", "DamagePct": "% Schools with Damaged Classrooms"},
                 text=dmg_block.sort_values("DamagePct", ascending=False)["DamagePct"].round(1))
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "**Policy Note:** Absence of functional girls' toilets is one of the strongest predictors of girl dropout "
        "at puberty. Schools without electricity cannot run evening study centres, digital learning, or be used "
        "as safe community spaces. NGOs should prioritize toilet construction and electrification in blocks "
        "showing both high dropout and low infrastructure scores."
    )


# ─── PAGE 6: Governance & Accountability ─────────────────────────────────────
elif page == "Governance & Accountability":
    st.title("Governance & Accountability")

    st.subheader("School Management Committee (SMC) Formation")

    smc_data = latest_profile.copy()
    smc_data["smc_formed"] = smc_data["smcYn"] == 1
    smc_data["smc_not"] = smc_data["smcYn"] == 2

    smc_block = smc_data.groupby("blockName").agg(
        Total=("schoolId", "count"),
        Formed=("smc_formed", "sum"),
        NotFormed=("smc_not", "sum"),
    ).reset_index()
    smc_block["FormedPct"] = smc_block["Formed"] / smc_block["Total"] * 100

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(smc_block.sort_values("FormedPct"),
                     x="FormedPct", y="blockName", orientation="h",
                     color="FormedPct", color_continuous_scale="RdYlGn",
                     labels={"blockName": "Block", "FormedPct": "% Schools with SMC"},
                     text=smc_block.sort_values("FormedPct")["FormedPct"].round(1))
        fig.add_vline(x=100, line_dash="dash", line_color="green")
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        smc_mgmt = smc_data.groupby("mgmtShort").agg(
            Total=("schoolId", "count"),
            Formed=("smc_formed", "sum"),
        ).reset_index()
        smc_mgmt["FormedPct"] = smc_mgmt["Formed"] / smc_mgmt["Total"] * 100
        fig2 = px.bar(smc_mgmt.sort_values("FormedPct"),
                      x="FormedPct", y="mgmtShort", orientation="h",
                      color="FormedPct", color_continuous_scale="Blues",
                      labels={"mgmtShort": "Management", "FormedPct": "% with SMC"},
                      text=smc_mgmt.sort_values("FormedPct")["FormedPct"].round(1))
        fig2.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("School Inspection Frequency")

    inspect_data = latest_profile.copy()
    inspect_block = inspect_data.groupby("blockName").agg(
        AvgInspections=("noInspect", "mean"),
        AvgCRC=("noVisitCrc", "mean"),
        AvgBRC=("noVisitBrc", "mean"),
        AvgDist=("noVisitDis", "mean"),
        ZeroInspect=("noInspect", lambda x: (x == 0).sum()),
        Total=("schoolId", "count"),
    ).reset_index()
    inspect_block["ZeroPct"] = inspect_block["ZeroInspect"] / inspect_block["Total"] * 100

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(inspect_block.sort_values("AvgInspections"),
                     x="AvgInspections", y="blockName", orientation="h",
                     color="AvgInspections", color_continuous_scale="Blues",
                     labels={"blockName": "Block", "AvgInspections": "Avg Inspections/School"},
                     text=inspect_block.sort_values("AvgInspections")["AvgInspections"].round(1))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig2 = px.bar(inspect_block.sort_values("ZeroPct", ascending=False),
                      x="blockName", y="ZeroPct",
                      color="ZeroPct", color_continuous_scale="Reds",
                      labels={"blockName": "Block", "ZeroPct": "% Schools with 0 Inspections"},
                      text=inspect_block.sort_values("ZeroPct", ascending=False)["ZeroPct"].round(1))
        fig2.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Welfare Scheme Delivery")

    welfare = latest_rc.groupby("blockName").agg(
        FreeTextbookPrimary=("ftbPr", "sum"),
        FreeTextbookUpper=("ftbUpr", "sum"),
        UniformPrimary=("uniformPr", "sum"),
        UniformUpper=("uniformUpr", "sum"),
        TransportPrimary=("transptPr", "sum"),
        Schools=("schoolId", "count"),
    ).reset_index()

    for col in ["FreeTextbookPrimary", "FreeTextbookUpper", "UniformPrimary", "UniformUpper", "TransportPrimary"]:
        welfare[f"{col}Pct"] = welfare[col] / welfare["Schools"] * 100

    welfare_melted = pd.melt(
        welfare,
        id_vars="blockName",
        value_vars=["FreeTextbookPrimaryPct", "UniformPrimaryPct", "TransportPrimaryPct"],
        var_name="Scheme", value_name="% Schools"
    )
    welfare_melted["Scheme"] = welfare_melted["Scheme"].str.replace("Pct", "").str.replace("Primary", " (Primary)")

    fig = px.bar(welfare_melted, x="blockName", y="% Schools", color="Scheme",
                 barmode="group",
                 color_discrete_sequence=px.colors.qualitative.Set3,
                 labels={"blockName": "Block"})
    fig.update_layout(xaxis_tickangle=-20)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Financial Overview: Grants & Expenditure")

    finance = latest_rc.groupby("blockName").agg(
        TotalGrant=("totalGrant", "sum"),
        TotalExpend=("totalExpediture", "sum"),
        Schools=("schoolId", "count"),
    ).reset_index()
    finance["GrantPerSchool"] = finance["TotalGrant"] / finance["Schools"]
    finance["ExpendPerSchool"] = finance["TotalExpend"] / finance["Schools"]

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(finance.sort_values("GrantPerSchool"), x="GrantPerSchool", y="blockName",
                     orientation="h", color="GrantPerSchool",
                     color_continuous_scale="Greens",
                     labels={"blockName": "Block", "GrantPerSchool": "Avg Grant/School (₹)"},
                     text=finance.sort_values("GrantPerSchool")["GrantPerSchool"].apply(lambda x: f"₹{x:,.0f}"))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        zero_grant = latest_rc[latest_rc["totalGrant"] == 0].shape[0]
        zero_expend = latest_rc[latest_rc["totalExpediture"] == 0].shape[0]
        total_rc = len(latest_rc)
        st.metric("Schools with ₹0 Grant", f"{zero_grant} ({zero_grant/total_rc*100:.1f}%)",
                  help="Schools reporting no grant received")
        st.metric("Schools with ₹0 Expenditure", f"{zero_expend} ({zero_expend/total_rc*100:.1f}%)",
                  help="Schools reporting no expenditure")
        st.warning("High zero-grant rates may indicate under-reporting or fund absorption failures.")

    st.info(
        "**Policy Note:** SMC (School Management Committee) formation is mandated under RTE Act 2009. "
        "Non-functional or absent SMCs are a governance red flag — they're the community's primary accountability "
        "mechanism. NGOs can provide SMC training, help form parent committees in Madrasa schools, and track "
        "welfare scheme delivery as part of a social audit program."
    )


# ─── PAGE 7: Block-wise Comparison ────────────────────────────────────────────
elif page == "Block-wise Comparison":
    st.title("Block-wise Comparison")
    st.caption("Composite Vulnerability Index and cross-block benchmarking")

    block_schools = master[master["blockName"].isin(selected_blocks)]["blockName"].value_counts().reset_index()
    block_schools.columns = ["blockName", "TotalSchools"]

    block_students = latest_counts.groupby("blockName").agg(
        TotalStudents=("totalCount", "sum"),
        Boys=("totalBoy", "sum"),
        Girls=("totalGirl", "sum"),
    ).reset_index()
    block_students["GPI"] = block_students["Girls"] / block_students["Boys"].replace(0, np.nan)

    block_teachers = latest_rc.groupby("blockName").agg(
        TotalTeachers=("totalTeacher", "sum"),
    ).reset_index()

    block_inf = latest_facility.groupby("blockName").agg(
        ElecPct=("electricityYn", lambda x: (x == 1).mean() * 100),
        WaterPct=("drinkWaterYn", lambda x: (x == 1).mean() * 100),
        ToiletGPct=("toiletgFun", lambda x: (x >= 1).mean() * 100),
        InternetPct=("internetYn", lambda x: (x == 1).mean() * 100),
    ).reset_index()

    block_smc = latest_profile.groupby("blockName").agg(
        SMCPct=("smcYn", lambda x: (x == 1).mean() * 100),
    ).reset_index()

    comp = (block_schools
            .merge(block_students, on="blockName", how="left")
            .merge(block_teachers, on="blockName", how="left")
            .merge(block_inf, on="blockName", how="left")
            .merge(block_smc, on="blockName", how="left"))

    comp["PTR"] = comp["TotalStudents"] / comp["TotalTeachers"].replace(0, np.nan)
    comp["PTR_score"] = (1 - (comp["PTR"] - 30).clip(0) / 30).clip(0, 1) * 100
    comp["GPI_score"] = comp["GPI"].clip(0, 1) * 100

    comp["InfraScore"] = comp[["ElecPct", "WaterPct", "ToiletGPct", "InternetPct"]].mean(axis=1)
    comp["VulnIndex"] = 100 - (
        0.3 * comp["GPI_score"] +
        0.25 * comp["InfraScore"] +
        0.25 * comp["SMCPct"].fillna(0) +
        0.2 * comp["PTR_score"]
    )

    st.subheader("Composite Vulnerability Index by Block")
    st.caption("Higher score = more vulnerable. Components: GPI (30%), Infrastructure (25%), SMC coverage (25%), PTR (20%)")

    comp_sorted = comp.sort_values("VulnIndex", ascending=False)
    fig = px.bar(comp_sorted, x="blockName", y="VulnIndex",
                 color="VulnIndex", color_continuous_scale="RdYlGn_r",
                 labels={"blockName": "Block", "VulnIndex": "Vulnerability Score (0-100)"},
                 text=comp_sorted["VulnIndex"].round(1))
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Block Scorecard")

    display_cols = {
        "blockName": "Block",
        "TotalSchools": "Schools",
        "TotalStudents": "Students",
        "PTR": "PTR",
        "GPI": "GPI",
        "ElecPct": "Electricity %",
        "WaterPct": "Water %",
        "ToiletGPct": "Girls Toilet %",
        "InternetPct": "Internet %",
        "SMCPct": "SMC %",
        "VulnIndex": "Vuln. Score",
    }
    display_df = comp[display_cols.keys()].rename(columns=display_cols)
    display_df["PTR"] = display_df["PTR"].round(1)
    display_df["GPI"] = display_df["GPI"].round(2)
    for col in ["Electricity %", "Water %", "Girls Toilet %", "Internet %", "SMC %", "Vuln. Score"]:
        display_df[col] = display_df[col].round(1)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Radar Chart: Multi-dimensional Block Comparison")

    categories = ["GPI_score", "ElecPct", "WaterPct", "ToiletGPct", "SMCPct", "PTR_score"]
    cat_labels = ["GPI", "Electricity", "Water", "Girls Toilet", "SMC", "PTR"]

    fig = go.Figure()
    colors = px.colors.qualitative.Set1
    for i, row in comp.iterrows():
        vals = [row[c] for c in categories]
        vals += [vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=cat_labels + [cat_labels[0]],
            fill="toself",
            name=row["blockName"],
            line_color=colors[i % len(colors)],
            opacity=0.6,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "**Policy Note:** The Vulnerability Index helps NGOs prioritize where to deploy limited resources. "
        "Blocks with high vulnerability scores need the most attention — typically they have low GPI (girls "
        "not reaching school), poor infrastructure, weak governance (no SMC), and overcrowded classrooms. "
        "For Kishanganj, Madrasa-heavy blocks may score differently because Madrasa data is incomplete in UDISE+."
    )


# ─── PAGE 8: Correlation Explorer ─────────────────────────────────────────────
elif page == "Correlation Explorer":
    st.title("Correlation Explorer")
    st.caption("Explore relationships between infrastructure, governance, and enrollment outcomes")

    merged = latest_counts.merge(
        latest_facility[["schoolId", "electricityYn", "drinkWaterYn", "toiletgFun",
                          "internetYn", "libraryYn", "clsrmsGd", "desktopFun"]],
        on="schoolId", how="left"
    ).merge(
        latest_profile[["schoolId", "smcYn", "noInspect", "noVisitCrc"]],
        on="schoolId", how="left"
    ).merge(
        latest_rc[["schoolId", "totalTeacher", "totFemale", "totTchGraduateAbove", "totalGrant"]],
        on="schoolId", how="left"
    )

    merged["GPI"] = merged["totalGirl"] / merged["totalBoy"].replace(0, np.nan)
    merged["has_electricity"] = (merged["electricityYn"] == 1).astype(int)
    merged["has_toilet_g"] = (merged["toiletgFun"] >= 1).astype(int)
    merged["has_internet"] = (merged["internetYn"] == 1).astype(int)
    merged["has_library"] = (merged["libraryYn"] == 1).astype(int)
    merged["has_smc"] = (merged["smcYn"] == 1).astype(int)
    merged["female_tch_pct"] = merged["totFemale"] / merged["totalTeacher"].replace(0, np.nan) * 100
    merged["PTR"] = merged["totalCount"] / merged["totalTeacher"].replace(0, np.nan)
    merged["qual_tch_pct"] = merged["totTchGraduateAbove"] / merged["totalTeacher"].replace(0, np.nan) * 100

    st.subheader("Correlation Heatmap")
    corr_cols = ["totalCount", "GPI", "has_electricity", "has_toilet_g", "has_internet",
                 "has_library", "has_smc", "female_tch_pct", "PTR", "qual_tch_pct",
                 "noInspect", "totalGrant"]
    corr_labels = ["Enrollment", "GPI", "Electricity", "Girls Toilet", "Internet",
                   "Library", "SMC", "Female Tch %", "PTR", "Qual Tch %",
                   "Inspections", "Grant"]

    corr_df = merged[corr_cols].rename(columns=dict(zip(corr_cols, corr_labels))).dropna()
    corr_matrix = corr_df.corr()

    fig = px.imshow(
        corr_matrix,
        color_continuous_scale="RdBu",
        color_continuous_midpoint=0,
        text_auto=".2f",
        aspect="auto",
        zmin=-1, zmax=1,
    )
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Scatter Plot: Custom Variable Explorer")

    num_cols_available = {
        "Total Enrollment": "totalCount",
        "Gender Parity Index": "GPI",
        "Female Teacher %": "female_tch_pct",
        "Pupil-Teacher Ratio": "PTR",
        "Qualified Teacher %": "qual_tch_pct",
        "Inspections": "noInspect",
        "Total Grant": "totalGrant",
    }

    c1, c2, c3 = st.columns(3)
    with c1:
        x_var = st.selectbox("X-axis", list(num_cols_available.keys()), index=0)
    with c2:
        y_var = st.selectbox("Y-axis", list(num_cols_available.keys()), index=1)
    with c3:
        color_var = st.selectbox("Color by", ["blockName", "mgmtShort", "has_electricity",
                                               "has_toilet_g", "has_smc"], index=0)

    plot_df = merged[[num_cols_available[x_var], num_cols_available[y_var],
                       color_var, "schoolName"]].dropna()

    fig = px.scatter(
        plot_df,
        x=num_cols_available[x_var],
        y=num_cols_available[y_var],
        color=color_var,
        hover_name="schoolName",
        opacity=0.6,
        labels={
            num_cols_available[x_var]: x_var,
            num_cols_available[y_var]: y_var,
        },
        trendline="lowess",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Key Findings: Infrastructure → Enrollment Correlation")

    infra_factors = [
        ("Electricity", "has_electricity"),
        ("Girls' Toilet", "has_toilet_g"),
        ("Internet", "has_internet"),
        ("Library", "has_library"),
        ("SMC Present", "has_smc"),
    ]

    results = []
    for label, col in infra_factors:
        with_factor = merged[merged[col] == 1]["totalCount"].median()
        without_factor = merged[merged[col] == 0]["totalCount"].median()
        gpi_with = merged[merged[col] == 1]["GPI"].median()
        gpi_without = merged[merged[col] == 0]["GPI"].median()
        results.append({
            "Factor": label,
            "Median Enrollment (With)": with_factor,
            "Median Enrollment (Without)": without_factor,
            "Enrollment Diff": with_factor - without_factor,
            "GPI (With)": gpi_with,
            "GPI (Without)": gpi_without,
        })

    results_df = pd.DataFrame(results)
    st.dataframe(results_df.round(1), use_container_width=True, hide_index=True)

    fig = px.bar(results_df, x="Factor", y="Enrollment Diff",
                 color="Enrollment Diff", color_continuous_scale="RdYlGn",
                 labels={"Enrollment Diff": "Extra Enrolled (Median, With vs Without)"},
                 text=results_df["Enrollment Diff"].round(0))
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "**Policy Note:** Correlations show which infrastructure investments most strongly associate with higher "
        "enrollment and better GPI. While correlation is not causation, schools with electricity, girls' toilets, "
        "and functional SMCs consistently have higher enrollment — particularly of girls. "
        "These are the highest-leverage intervention points for an education NGO."
    )

st.sidebar.markdown(
    "<div style='font-size:0.7rem; color:#999; text-align:center; padding:8px 0;'>"
    "UDISE+ · Kishanganj, Bihar<br>2,026 schools · 2022–25"
    "</div>",
    unsafe_allow_html=True,
)
