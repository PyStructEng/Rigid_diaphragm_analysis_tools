"""
Rigid Diaphragm Analysis — Streamlit App
======================================

This app implements the SAME calculation logic as rigid_diaphragm_analysis.py (Excel-matching),
but lets you input an arbitrary number of walls (EW / NS) through an editable table.

Run:
    streamlit run rigid_diaphragm_streamlit_app.py

Notes on display (avoiding ellipsis):
- Uses st.dataframe with horizontal scrolling (wide tables) + download buttons.
"""

from __future__ import annotations

import math
from io import BytesIO
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st


# -----------------------------
# Excel-matching helpers / logic
# -----------------------------

def _clean_wall_name(name: str) -> str:
    return str(name).strip()

def _wall_orientation_factors(wall_name: str, Di: float) -> Tuple[float, float]:
    """
    Match the spreadsheet convention:
      - 'EW' walls: Rix = 1/Di, Riy = 0
      - 'NS' walls: Rix = 0, Riy = 1/Di
    """
    nm = wall_name.upper()
    if "EW" in nm:
        return (1.0 / Di, 0.0)
    if "NS" in nm:
        return (0.0, 1.0 / Di)
    raise ValueError(f"Wall Name '{wall_name}' must contain 'EW' or 'NS'.")

def compute_rigid_diaphragm(inputs: Dict[str, float], walls: List[Dict[str, object]]) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    SAME math as the Excel template + your corrected Jp V-term:
      U = Riy*xbar^2
      V = Rix*ybar^2
      Jp = ΣU + ΣV
    """
    # Unpack
    L = float(inputs["L"])
    B = float(inputs["B"])
    Xcm_manual = float(inputs["Xcm_manual"])
    Ycm_manual = float(inputs["Ycm_manual"])
    W = float(inputs["W"])  # kept for completeness
    X_offset = float(inputs["X_offset"])
    Y_offset = float(inputs["Y_offset"])
    Fx = float(inputs["Fx"])
    Fy = float(inputs["Fy"])

    # Accidental eccentricities (Excel: 10%)
    exbar = 0.1 * L
    eybar = 0.1 * B

    # Working coordinates (critical zero shift)
    Xcm = Xcm_manual - X_offset
    Ycm = Ycm_manual - Y_offset

    rows = []
    for w in walls:
        name = _clean_wall_name(w["Wall Name"])
        length = float(w["Length (m)"])
        height = float(w["Height (m)"])
        wk = w.get("w_k (kN)", None)
        x_coord = float(w["x_coord (m)"])
        y_coord = float(w["y_coord (m)"])

        xk = x_coord - X_offset
        yk = y_coord - Y_offset

        # Di (same as sheet)
        Di = 4.0 * (height / length) ** 3 + 3.0 * (height / length)

        # Rix/Riy from wall naming
        Rix, Riy = _wall_orientation_factors(name, Di)

        rows.append(
            {
                "Wall Name": name,
                "Length (m)": length,
                "Height (m)": height,
                "w_k (kN)": wk,
                "x_coord (m)": x_coord,
                "y_coord (m)": y_coord,
                "xk (m)": xk,
                "yk (m)": yk,
                "Di": Di,
                "Rix": Rix,
                "Riy": Riy,
                "Riy*xk": Riy * xk,
                "Rix*yk": Rix * yk,
            }
        )

    df = pd.DataFrame(rows)

    sum_Rix = float(df["Rix"].sum())
    sum_Riy = float(df["Riy"].sum())

    # Center of Rigidity (sheet convention)
    Xcr = (float(df["Riy*xk"].sum()) / sum_Riy) if sum_Riy != 0 else float("nan")
    Ycr = (float(df["Rix*yk"].sum()) / sum_Rix) if sum_Rix != 0 else float("nan")

    # Real eccentricities
    ex = abs(Xcm - Xcr)
    ey = abs(Ycm - Ycr)

    # Relative distances to CoR
    df["xbar"] = df["xk (m)"] - Xcr
    df["ybar"] = df["yk (m)"] - Ycr

    # Jp (corrected)
    df["Riy*xbar2"] = df["Riy"] * (df["xbar"] ** 2)
    df["Rix*ybar2"] = df["Rix"] * (df["ybar"] ** 2)
    Jp = float(df["Riy*xbar2"].sum() + df["Rix*ybar2"].sum())

    # Real torsion ratios
    df["Real Tor Ratio_x"] = df["Rix"] * df["ybar"] * ey / Jp
    df["Real Tor Ratio_y"] = df["Riy"] * df["xbar"] * ex / Jp
    df["Vx_Real Tor"] = Fx * df["Real Tor Ratio_x"]
    df["Vy_Real Tor"] = Fy * df["Real Tor Ratio_y"]

    # Direct shear
    df["Direct Shear Ratio_x"] = (df["Rix"] / sum_Rix) if sum_Rix != 0 else 0.0
    df["Direct Shear Ratio_y"] = (df["Riy"] / sum_Riy) if sum_Riy != 0 else 0.0
    df["Direct Shear_x"] = Fx * df["Direct Shear Ratio_x"]
    df["Direct Shear_y"] = Fy * df["Direct Shear Ratio_y"]

    # Accidental torsion (10%) — match sheet multiplications
    df["AccTorRatio_x"] = eybar * df["Rix"] * df["ybar"] / Jp
    df["AccTorRatio_y"] = exbar * df["Riy"] * df["xbar"] / Jp
    df["Vx_Acc_Tor"] = Fy * df["AccTorRatio_x"]
    df["Vy_Acc_Tor"] = Fx * df["AccTorRatio_y"]

    # Totals (match sheet)
    df["Vx (kN)"] = df["Vx_Real Tor"] + df["Direct Shear_x"] + df["Vx_Acc_Tor"]
    df["Vy (kN)"] = df["Vy_Real Tor"] + df["Direct Shear_y"] + df["Vy_Acc_Tor"].abs()

    # Optional: sort EW then NS (stable), as requested
    def _dir_key(nm: str) -> int:
        u = nm.upper()
        if "EW" in u:
            return 0
        if "NS" in u:
            return 1
        return 2

    df["_dir"] = df["Wall Name"].apply(_dir_key)
    df = df.sort_values(by=["_dir", "Wall Name"], kind="mergesort").drop(columns=["_dir"]).reset_index(drop=True)

    ordered_cols = [
        "Wall Name", "Length (m)", "Height (m)", "w_k (kN)",
        "x_coord (m)", "y_coord (m)", "xk (m)", "yk (m)",
        "Di", "Rix", "Riy", "Riy*xk", "Rix*yk",
        "xbar", "ybar", "Riy*xbar2", "Rix*ybar2",
        "Real Tor Ratio_x", "Real Tor Ratio_y", "Vx_Real Tor", "Vy_Real Tor",
        "Direct Shear Ratio_x", "Direct Shear Ratio_y", "Direct Shear_x", "Direct Shear_y",
        "AccTorRatio_x", "AccTorRatio_y", "Vx_Acc_Tor", "Vy_Acc_Tor",
        "Vx (kN)", "Vy (kN)",
    ]
    df = df[ordered_cols]

    summary = {
        "L": L,
        "B": B,
        "X_offset": X_offset,
        "Y_offset": Y_offset,
        "Xcm": Xcm,
        "Ycm": Ycm,
        "Xcr": Xcr,
        "Ycr": Ycr,
        "ex": ex,
        "ey": ey,
        "exbar": exbar,
        "eybar": eybar,
        "Jp": Jp,
        "Fx": Fx,
        "Fy": Fy,
        "sum_Rix": sum_Rix,
        "sum_Riy": sum_Riy,
    }
    return df, summary


# -----------------------------
# Streamlit UI
# -----------------------------

st.set_page_config(page_title="Rigid Diaphragm Analysis", layout="wide")

st.title("Rigid Diaphragm Analysis (Rigid Plan)")

with st.expander("What this app does (same logic as Excel)", expanded=False):
    st.markdown(
        """
- Takes diaphragm inputs (same as your blue cells **J10–J29**) and a wall table (same fields as **D49–I52**).
- Assigns wall direction by **name**:
  - contains **EW** → x-direction wall (Rix = 1/Di, Riy = 0)
  - contains **NS** → y-direction wall (Rix = 0, Riy = 1/Di)
- Applies the **paper offsets** to set the coordinate origin (critical).
- Computes CoR, eccentricities, **Jp**, direct shear, real torsion, accidental torsion (10%), then totals.
- Displays a wide table with horizontal scrolling + download buttons (to avoid truncation/ellipsis).
        """
    )

# Diaphragm-level inputs (kept explicit like the Excel inputs)
st.subheader("Diaphragm inputs")

col1, col2, col3, col4 = st.columns(4)

with col1:
    L = st.number_input("L (EW / X dimension) [m]", value=64.61, format="%.6f")
    Xcm_manual = st.number_input("Xcm (manual, paper coords) [m]", value=31.5, format="%.6f")
    X_offset = st.number_input("X paper offset (treat as x=0) [m]", value=55.8, format="%.6f")

with col2:
    B = st.number_input("B (NS / Y dimension) [m]", value=62.61, format="%.6f")
    Ycm_manual = st.number_input("Ycm (manual, paper coords) [m]", value=35.0, format="%.6f")
    Y_offset = st.number_input("Y paper offset (treat as y=0) [m]", value=9.87, format="%.6f")

with col3:
    Fx = st.number_input("Fx (lateral force in x) [kN]", value=145.0, format="%.6f")
    Fy = st.number_input("Fy (lateral force in y) [kN]", value=145.0, format="%.6f")
with col4:
    W = st.number_input("W (diaphragm weight) [kN] (kept for completeness)", value=0.0, format="%.6f")

inputs = {
    "L": L, "B": B,
    "Xcm_manual": Xcm_manual, "Ycm_manual": Ycm_manual,
    "W": W,
    "X_offset": X_offset, "Y_offset": Y_offset,
    "Fx": Fx, "Fy": Fy,
}

st.subheader("Wall table (add/remove any number of walls)")
st.caption("Tip: use the 'add row' control in the table. Wall Name must contain EW or NS.")

if "walls_df" not in st.session_state:
    st.session_state["walls_df"] = pd.DataFrame(
        [
            {"Wall Name": "EW1", "Length (m)": 3.4, "Height (m)": 3.07, "w_k (kN)": 0.0, "x_coord (m)": 0.0, "y_coord (m)": 62.61},
            {"Wall Name": "EW2", "Length (m)": 4.1, "Height (m)": 3.07, "w_k (kN)": 0.0, "x_coord (m)": 0.0, "y_coord (m)": 62.61},
            {"Wall Name": "NS1", "Length (m)": 6.5, "Height (m)": 3.07, "w_k (kN)": 0.0, "x_coord (m)": 64.61, "y_coord (m)": 0.0},
            {"Wall Name": "NS2", "Length (m)": 4.8, "Height (m)": 3.07, "w_k (kN)": 0.0, "x_coord (m)": 62.81, "y_coord (m)": 0.0},
        ]
    )

edited = st.data_editor(
    st.session_state["walls_df"],
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Wall Name": st.column_config.TextColumn(width="medium"),
        "Length (m)": st.column_config.NumberColumn(format="%.6f"),
        "Height (m)": st.column_config.NumberColumn(format="%.6f"),
        "w_k (kN)": st.column_config.NumberColumn(format="%.6f"),
        "x_coord (m)": st.column_config.NumberColumn(format="%.6f"),
        "y_coord (m)": st.column_config.NumberColumn(format="%.6f"),
    },
    key="walls_editor",
)
st.session_state["walls_df"] = edited

run = st.button("Run rigid diaphragm analysis", type="primary")

def _df_to_excel_bytes(df: pd.DataFrame, summary: Dict[str, float]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
        pd.DataFrame([summary]).to_excel(writer, index=False, sheet_name="Summary")
    return output.getvalue()

if run:
    # Build walls list, ignore blank rows
    walls_df = st.session_state["walls_df"].copy()
    walls_df["Wall Name"] = walls_df["Wall Name"].fillna("").astype(str).str.strip()
    walls_df = walls_df[walls_df["Wall Name"] != ""]

    if len(walls_df) == 0:
        st.error("Please add at least one wall.")
        st.stop()

    walls: List[Dict[str, object]] = walls_df.to_dict(orient="records")

    # Validate names
    bad = [w["Wall Name"] for w in walls if ("EW" not in str(w["Wall Name"]).upper() and "NS" not in str(w["Wall Name"]).upper())]
    if bad:
        st.error(f"These walls do not contain 'EW' or 'NS' in the name: {bad}")
        st.stop()

    try:
        df_out, summary = compute_rigid_diaphragm(inputs, walls)
    except ZeroDivisionError:
        st.error("Jp became zero (division by zero). Check wall geometry, naming, and coordinates.")
        st.stop()
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

    st.subheader("Key results")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Xcm (working)", f"{summary['Xcm']:.6f} m")
    m2.metric("Ycm (working)", f"{summary['Ycm']:.6f} m")
    m3.metric("Xcr", f"{summary['Xcr']:.6f} m")
    m4.metric("Ycr", f"{summary['Ycr']:.6f} m")
    m5.metric("Jp", f"{summary['Jp']:.6f}")

    m6, m7, m8, m9 = st.columns(4)
    m6.metric("ex", f"{summary['ex']:.6f} m")
    m7.metric("ey", f"{summary['ey']:.6f} m")
    m8.metric("exbar (10%L)", f"{summary['exbar']:.6f} m")
    m9.metric("eybar (10%B)", f"{summary['eybar']:.6f} m")

    st.subheader("Wall-by-wall results (scroll horizontally — no truncation)")
    st.dataframe(
        df_out,
        use_container_width=True,
        height=520,
        hide_index=True,
    )

    # Downloads (best way to avoid any “ellipsis” concerns)
    st.subheader("Download")
    csv_bytes = df_out.to_csv(index=False).encode("utf-8")
    st.download_button("Download results as CSV", data=csv_bytes, file_name="rigid_diaphragm_results.csv", mime="text/csv")

    xlsx_bytes = _df_to_excel_bytes(df_out, summary)
    st.download_button("Download results as Excel (.xlsx)", data=xlsx_bytes, file_name="rigid_diaphragm_results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
