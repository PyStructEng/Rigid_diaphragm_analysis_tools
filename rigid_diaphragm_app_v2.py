"""
Rigid Diaphragm Analysis — Streamlit App
======================================
- Flexible: supports any number of walls (EW and NS) via an editable table.
- Displays the reference figure to the right of inputs.
"""

from __future__ import annotations

from io import BytesIO
from typing import Dict, List, Tuple

import base64
import pandas as pd
import streamlit as st
from PIL import Image


# -----------------------------
# Embedded reference figure (self-contained; no external image file needed)
# -----------------------------
_FIGURE_B64 = "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"


def _load_reference_figure() -> Image.Image:
    raw = base64.b64decode(_FIGURE_B64.encode("ascii"))
    return Image.open(BytesIO(raw))


def _wall_orientation_factors(wall_name: str, Di: float) -> Tuple[float, float]:
    """
    Match the spreadsheet convention:
      - 'EW' walls: Rix = 1/Di, Riy = 0
      - 'NS' walls: Rix = 0, Riy = 1/Di
    """
    nm = str(wall_name).upper()
    if "EW" in nm:
        return (1.0 / Di, 0.0)
    if "NS" in nm:
        return (0.0, 1.0 / Di)
    raise ValueError(f"Wall Name '{wall_name}' must contain 'EW' or 'NS'.")


def compute_rigid_diaphragm(inputs: Dict[str, float], walls: List[Dict[str, object]]) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    SAME math as the Excel template + corrected Jp V-term:
      U = Riy*xbar^2
      V = Rix*ybar^2
      Jp = ΣU + ΣV
    """
    # Unpack
    L = float(inputs["L"])
    B = float(inputs["B"])
    Xcm_manual = float(inputs["Xcm_manual"])
    Ycm_manual = float(inputs["Ycm_manual"])
    W = float(inputs.get("W", 0.0))  # kept for completeness
    X_offset = float(inputs["X_offset"])
    Y_offset = float(inputs["Y_offset"])
    Fx = float(inputs["Fx"])
    Fy = float(inputs["Fy"])

    # Apply offsets (critical "zero" definition)
    Xcm = Xcm_manual - X_offset
    Ycm = Ycm_manual - Y_offset

    # Build wall dataframe
    df = pd.DataFrame(walls).copy()
    if df.empty:
        raise ValueError("No walls provided.")

    # Normalize names
    df["Wall Name"] = df["Wall Name"].astype(str).str.strip()

    # Working coordinates (offset-adjusted)
    df["xk (m)"] = df["x_coord (m)"].astype(float) - X_offset
    df["yk (m)"] = df["y_coord (m)"].astype(float) - Y_offset

    # Di term
    df["Di"] = 4.0 * (df["Height (m)"].astype(float) / df["Length (m)"].astype(float)) ** 3 + 3.0 * (
        df["Height (m)"].astype(float) / df["Length (m)"].astype(float)
    )

    # Rix/Riy based on name
    rix_list, riy_list = [], []
    for nm, Di in zip(df["Wall Name"].tolist(), df["Di"].tolist()):
        rix, riy = _wall_orientation_factors(nm, float(Di))
        rix_list.append(rix)
        riy_list.append(riy)
    df["Rix"] = rix_list
    df["Riy"] = riy_list

    # Sorting: EW first then NS (stable), as requested
    def _dir_order(nm: str) -> int:
        nm = nm.upper()
        if "EW" in nm:
            return 0
        if "NS" in nm:
            return 1
        return 2

    df["_dir_order"] = df["Wall Name"].map(_dir_order)
    df = df.sort_values(by=["_dir_order", "Wall Name"], kind="stable").drop(columns=["_dir_order"]).reset_index(drop=True)

    # CoR terms
    df["Riy*xk"] = df["Riy"] * df["xk (m)"]
    df["Rix*yk"] = df["Rix"] * df["yk (m)"]
    sum_Rix = float(df["Rix"].sum())
    sum_Riy = float(df["Riy"].sum())

    # Centers of rigidity (Excel convention)
    Xcr = float(df["Riy*xk"].sum() / sum_Riy) if sum_Riy != 0 else 0.0
    Ycr = float(df["Rix*yk"].sum() / sum_Rix) if sum_Rix != 0 else 0.0

    # Eccentricities
    ex = abs(Xcm - Xcr)
    ey = abs(Ycm - Ycr)

    exbar = 0.10 * L
    eybar = 0.10 * B

    # Relative coordinates
    df["xbar"] = df["xk (m)"] - Xcr
    df["ybar"] = df["yk (m)"] - Ycr

    # Jp (corrected)
    df["Riy*xbar2"] = df["Riy"] * (df["xbar"] ** 2)
    df["Rix*ybar2"] = df["Rix"] * (df["ybar"] ** 2)
    Jp = float(df["Riy*xbar2"].sum() + df["Rix*ybar2"].sum())
    if Jp == 0:
        raise ZeroDivisionError("Jp is zero (division by zero).")

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

    # Accidental torsion (10%) — same convention as your validated script
    df["AccTorRatio_x"] = (eybar * df["Rix"] * df["ybar"] / Jp)
    df["AccTorRatio_y"] = (exbar * df["Riy"] * df["xbar"] / Jp)
    df["Vx_Acc_Tor"] = Fy * df["AccTorRatio_x"]
    df["Vy_Acc_Tor"] = Fx * df["AccTorRatio_y"]

    # Totals (same as script / template)
    df["Vx (kN)"] = df["Vx_Real Tor"] + df["Direct Shear_x"] + df["Vx_Acc_Tor"]
    df["Vy (kN)"] = df["Vy_Real Tor"] + df["Direct Shear_y"] + df["Vy_Acc_Tor"].abs()

    # Order columns similar to the Excel-style table in your script
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
        "W": W,
    }
    return df, summary


def _df_to_excel_bytes(df: pd.DataFrame, summary: Dict[str, float]) -> bytes:
    """
    Export results and key summary to an Excel file in-memory.
    All values rounded to 2 decimals (per your requirement).
    """
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl import Workbook

    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Key Results"

    key_rows = [
        ("Xcm (working)", summary["Xcm"]),
        ("Ycm (working)", summary["Ycm"]),
        ("Xcr (CoR)", summary["Xcr"]),
        ("Ycr (CoR)", summary["Ycr"]),
        ("ex (real)", summary["ex"]),
        ("ey (real)", summary["ey"]),
        ("exbar (0.1L)", summary["exbar"]),
        ("eybar (0.1B)", summary["eybar"]),
        ("Jp", summary["Jp"]),
        ("Fx", summary["Fx"]),
        ("Fy", summary["Fy"]),
    ]
    ws1.append(["Result", "Value"])
    for k, v in key_rows:
        ws1.append([k, round(float(v), 2)])

    ws2 = wb.create_sheet("Wall Results")
    df_round = df.copy()
    numeric_cols = [c for c in df_round.columns if c != "Wall Name"]
    df_round[numeric_cols] = df_round[numeric_cols].apply(pd.to_numeric, errors="coerce").round(2)

    for r in dataframe_to_rows(df_round, index=False, header=True):
        ws2.append(r)

    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()


def _key_results_table(summary: Dict[str, float]) -> pd.DataFrame:
    rows = [
        ("Xcm (working)", summary["Xcm"], "m"),
        ("Ycm (working)", summary["Ycm"], "m"),
        ("Xcr (CoR)", summary["Xcr"], "m"),
        ("Ycr (CoR)", summary["Ycr"], "m"),
        ("ex (real)", summary["ex"], "m"),
        ("ey (real)", summary["ey"], "m"),
        ("exbar (0.1L)", summary["exbar"], "m"),
        ("eybar (0.1B)", summary["eybar"], "m"),
        ("Jp", summary["Jp"], "-"),
        ("Fx", summary["Fx"], "kN"),
        ("Fy", summary["Fy"], "kN"),
    ]
    dfk = pd.DataFrame(rows, columns=["Result", "Value", "Unit"])
    dfk["Value"] = dfk["Value"].astype(float).round(2)
    return dfk


def main() -> None:
    st.set_page_config(page_title="Rigid Diaphragm Analysis", layout="wide")
    st.title("Rigid Diaphragm Analysis (Rigid Plan)")

    # Layout: inputs left, figure right
    left, right = st.columns([2.2, 1.0], gap="large")

    with right:
        st.subheader("Reference figure")
        st.image(_load_reference_figure(), use_container_width=True)
        st.caption("Paper origin + offset definition used for the working coordinate system.")

    with left:
        with st.expander("What this app does (same logic as your Excel)", expanded=False):
            st.markdown(
                """
- Takes diaphragm inputs and a wall table data input.
- Assigns wall direction by name:
  - contains **EW** → x-direction wall (Rix = 1/Di, Riy = 0)
  - contains **NS** → y-direction wall (Rix = 0, Riy = 1/Di)
- Applies the **paper offsets** to set the working origin (critical).
- Computes CoR, eccentricities, **Jp**, direct shear, real torsion, accidental torsion (10%), then totals.
- Displays a table with all the calculations.
                """
            )

        st.subheader("Diaphragm inputs")
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            L = st.number_input("L (EW / X dimension) [m]", value=64.61, step=0.01, format="%.2f")
            Xcm_manual = st.number_input("Xcm (manual, paper coords) [m]", value=31.50, step=0.01, format="%.2f")
            X_offset = st.number_input("X paper offset (treat as x=0) [m]", value=55.80, step=0.01, format="%.2f")

        with c2:
            B = st.number_input("B (NS / Y dimension) [m]", value=62.61, step=0.01, format="%.2f")
            Ycm_manual = st.number_input("Ycm (manual, paper coords) [m]", value=34.50, step=0.01, format="%.2f")
            Y_offset = st.number_input("Y paper offset (treat as y=0) [m]", value=14.70, step=0.01, format="%.2f")

        with c3:
            Fx = st.number_input("Fx (applied force in X) [kN]", value=100.00, step=0.01, format="%.2f")
            Fy = st.number_input("Fy (applied force in Y) [kN]", value=80.00, step=0.01, format="%.2f")

        with c4:
            W = st.number_input("W (diaphragm weight) [kN] (kept for completeness)", value=0.00, step=0.01, format="%.2f")

        inputs = {
            "L": L, "B": B,
            "Xcm_manual": Xcm_manual, "Ycm_manual": Ycm_manual,
            "W": W,
            "X_offset": X_offset, "Y_offset": Y_offset,
            "Fx": Fx, "Fy": Fy,
        }

        st.subheader("Wall table (add/remove any number of walls)")
        st.caption("Wall Name must contain EW or NS. You can add rows using the table controls.")

        # Default rows (clean, no ellipsis)
        if "walls_df" not in st.session_state:
            st.session_state["walls_df"] = pd.DataFrame(
                [
                    {"Wall Name": "EW1", "Length (m)": 3.40, "Height (m)": 3.07, "w_k (kN)": 0.00, "x_coord (m)": 0.00, "y_coord (m)": 62.61},
                    {"Wall Name": "EW2", "Length (m)": 4.10, "Height (m)": 3.07, "w_k (kN)": 0.00, "x_coord (m)": 0.00, "y_coord (m)": 62.61},
                    {"Wall Name": "NS1", "Length (m)": 6.50, "Height (m)": 3.07, "w_k (kN)": 0.00, "x_coord (m)": 64.61, "y_coord (m)": 0.00},
                    {"Wall Name": "NS2", "Length (m)": 4.80, "Height (m)": 3.07, "w_k (kN)": 0.00, "x_coord (m)": 62.81, "y_coord (m)": 0.00},
                ]
            )

        edited = st.data_editor(
            st.session_state["walls_df"],
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Wall Name": st.column_config.TextColumn(width="medium"),
                "Length (m)": st.column_config.NumberColumn(format="%.2f", step=0.01),
                "Height (m)": st.column_config.NumberColumn(format="%.2f", step=0.01),
                "w_k (kN)": st.column_config.NumberColumn(format="%.2f", step=0.01),
                "x_coord (m)": st.column_config.NumberColumn(format="%.2f", step=0.01),
                "y_coord (m)": st.column_config.NumberColumn(format="%.2f", step=0.01),
            },
            key="walls_editor",
        )
        st.session_state["walls_df"] = edited

        run = st.button("Run rigid diaphragm analysis", type="primary")

    # Run outside the columns so results can use full page width
    if run:
        df_in = st.session_state["walls_df"].copy()
        df_in = df_in[df_in["Wall Name"].astype(str).str.strip() != ""].reset_index(drop=True)

        bad = []
        for nm in df_in["Wall Name"].astype(str).tolist():
            up = nm.upper()
            if ("EW" not in up) and ("NS" not in up):
                bad.append(nm)
        if bad:
            st.error(f"These walls do not contain 'EW' or 'NS' in the name: {bad}")
            st.stop()

        walls = df_in.to_dict(orient="records")

        try:
            df_out, summary = compute_rigid_diaphragm(inputs, walls)
        except ZeroDivisionError:
            st.error("Jp became zero (division by zero). Check wall geometry, naming, and coordinates.")
            st.stop()
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

        st.subheader("Key results")
        st.table(_key_results_table(summary))

        # -----------------------------
        # Wall forces summary (per wall)
        # -----------------------------
        st.markdown(
            "<h3 style='margin-top: 0.6rem;'>Wall forces summary</h3>",
            unsafe_allow_html=True,
        )

        # Pick key force columns (keep the logic untouched; this is just a view)
        force_cols = [
            "Wall Name",
            "Direct Shear_x", "Direct Shear_y",
            "Vx_Real Tor", "Vy_Real Tor",
            "Vx_Acc_Tor", "Vy_Acc_Tor",
            "Vx (kN)", "Vy (kN)",
        ]
        df_forces = df_out[force_cols].copy()

        # Round numeric values to 2 decimals for display
        num_cols = [c for c in df_forces.columns if c != "Wall Name"]
        df_forces[num_cols] = df_forces[num_cols].apply(pd.to_numeric, errors="coerce").round(2)

        # Optional: color negatives vs positives (works in Streamlit with pandas Styler)
        try:
            def _force_color(v):
                if pd.isna(v):
                    return ""
                return "color: #1f7a1f;" if v >= 0 else "color: #b00020;"

            styler = df_forces.style.format(precision=2).applymap(_force_color, subset=num_cols)
            st.dataframe(styler, use_container_width=True, height=320)
        except Exception:
            # Fallback if Styler isn't supported in the installed Streamlit version
            st.dataframe(df_forces, use_container_width=True, height=320)


        st.subheader("Wall-by-wall results")
        df_show = df_out.copy()
        numeric_cols = [c for c in df_show.columns if c != "Wall Name"]
        df_show[numeric_cols] = df_show[numeric_cols].apply(pd.to_numeric, errors="coerce").round(2)

        st.dataframe(
            df_show,
            use_container_width=True,
            height=560,
            hide_index=True,
        )

        st.subheader("Download")
        csv_bytes = df_show.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download results as CSV",
            data=csv_bytes,
            file_name="rigid_diaphragm_results.csv",
            mime="text/csv",
        )

        xlsx_bytes = _df_to_excel_bytes(df_out, summary)
        st.download_button(
            "Download results as Excel (.xlsx)",
            data=xlsx_bytes,
            file_name="rigid_diaphragm_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()
