
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Rigid Diaphragm Shear Distribution", layout="wide")

# -----------------------------
# Helpers
# -----------------------------
def _to_float(x, default=np.nan):
    """Best-effort conversion to float."""
    try:
        if x is None:
            return default
        if isinstance(x, str) and x.strip() == "":
            return default
        return float(x)
    except Exception:
        return default

def compute_rigid_diaph(walls: pd.DataFrame, inputs: dict) -> tuple[pd.DataFrame, dict]:
    """
    Reproduces the core spreadsheet logic for rigid diaphragm shear distribution.

    Expected wall columns:
      marker, L, H, w, x, y   (x,y are global coordinates)
    inputs:
      Vx, Vy, origin_x, origin_y, plan_dim_x, plan_dim_y,
      diaphragm_w, diaphragm_x, diaphragm_y   (diaphragm coords are global)
    """
    df = walls.copy()

    # Normalize / coerce
    for c in ["L", "H", "w", "x", "y"]:
        df[c] = df[c].map(_to_float)

    # Drop empty rows (no marker and no geometry)
    df["marker"] = df["marker"].astype(str).replace("nan", "").str.strip()
    df = df[~((df["marker"] == "") & df[["L", "H", "x", "y"]].isna().all(axis=1))].copy()

    ox = _to_float(inputs.get("origin_x"))
    oy = _to_float(inputs.get("origin_y"))

    Vx = _to_float(inputs.get("Vx"), 0.0)
    Vy = _to_float(inputs.get("Vy"), 0.0)

    plan_x = _to_float(inputs.get("plan_dim_x"), 0.0)  # used for 10% accidental ecc
    plan_y = _to_float(inputs.get("plan_dim_y"), 0.0)

    dia_w = _to_float(inputs.get("diaphragm_w"), 0.0)
    dia_x = _to_float(inputs.get("diaphragm_x"))
    dia_y = _to_float(inputs.get("diaphragm_y"))

    # Local coords for walls
    df["xk"] = df["x"] - ox
    df["yk"] = df["y"] - oy

    # delta = 4*(H/L)^3 + 3*(H/L)
    hl = df["H"] / df["L"]
    df["delta"] = 4.0 * (hl ** 3) + 3.0 * hl

    # Directional rigidities based on marker prefix EW/NS (matches the spreadsheet pattern)
    is_EW = df["marker"].str.upper().str.startswith("EW")
    is_NS = df["marker"].str.upper().str.startswith("NS")

    df["Ri_EW"] = np.where(is_EW, 1.0 / df["delta"], 0.0)
    df["Ri_NS"] = np.where(is_NS, 1.0 / df["delta"], 0.0)

    sum_Ri_EW = float(np.nansum(df["Ri_EW"].to_numpy()))
    sum_Ri_NS = float(np.nansum(df["Ri_NS"].to_numpy()))

    # Rigidity center (xr uses NS rigidity, yr uses EW rigidity)
    xr = (np.nansum((df["Ri_NS"] * df["xk"]).to_numpy()) / sum_Ri_NS) if sum_Ri_NS != 0 else np.nan
    yr = (np.nansum((df["Ri_EW"] * df["yk"]).to_numpy()) / sum_Ri_EW) if sum_Ri_EW != 0 else np.nan

    df["xbar"] = df["xk"] - xr
    df["ybar"] = df["yk"] - yr

    # Jp terms
    Jpy = float(np.nansum((df["Ri_NS"] * (df["xbar"] ** 2)).to_numpy()))
    Jpx = float(np.nansum((df["Ri_EW"] * (df["ybar"] ** 2)).to_numpy()))
    Jp = Jpx + Jpy

    # Mass centroid (walls + diaphragm). Spreadsheet does sum(w*xk)/sum(w)
    # Using provided wall weights; blanks -> NaN -> treated as 0 in sums
    wall_w = df["w"].fillna(0.0)
    # diaphragm local coords
    dia_xk = dia_x - ox
    dia_yk = dia_y - oy

    Wtot = float(wall_w.sum() + (0.0 if np.isnan(dia_w) else dia_w))
    if Wtot != 0:
        xcg = float((wall_w * df["xk"]).sum() + dia_w * dia_xk) / Wtot
        ycg = float((wall_w * df["yk"]).sum() + dia_w * dia_yk) / Wtot
    else:
        xcg, ycg = np.nan, np.nan

    # Eccentricities
    ex_real = abs(xcg - xr) if (not np.isnan(xcg) and not np.isnan(xr)) else np.nan
    ey_real = abs(ycg - yr) if (not np.isnan(ycg) and not np.isnan(yr)) else np.nan

    ex_acc = 0.1 * plan_x
    ey_acc = 0.1 * plan_y

    # Direct shear ratio: X and Y directions
    df["DirectRatio_X"] = np.where(sum_Ri_EW != 0, df["Ri_EW"] / sum_Ri_EW, np.nan)
    df["DirectRatio_Y"] = np.where(sum_Ri_NS != 0, df["Ri_NS"] / sum_Ri_NS, np.nan)

    # Direct shear
    df["DirectShear_X"] = Vx * df["DirectRatio_X"]
    df["DirectShear_Y"] = Vy * df["DirectRatio_Y"]

    # Torsion ratios (match the spreadsheet structure):
    # For Vx torsion, ratio uses (ey * xbar * Ri_EW) / Jp
    # For Vy torsion, ratio uses (ex * ybar * Ri_NS) / Jp
    df["RealTorRatio_X"] = np.where(Jp != 0, ey_real * df["Ri_EW"] * df["ybar"] / Jp, np.nan)
    df["RealTorRatio_Y"] = np.where(Jp != 0, ex_real * df["Ri_NS"] * df["xbar"] / Jp, np.nan)

    df["AccTorRatio_X"] = np.where(Jp != 0, ey_acc * df["Ri_EW"] * df["ybar"] / Jp, np.nan)
    df["AccTorRatio_Y"] = np.where(Jp != 0, ex_acc * df["Ri_NS"] * df["xbar"] / Jp, np.nan)

    # Torsion shear
    df["RealTor_X"] = Vx * df["RealTorRatio_X"]
    df["RealTor_Y"] = Vy * df["RealTorRatio_Y"]

    df["AccTor_X"] = Vx * df["AccTorRatio_X"]
    df["AccTor_Y"] = Vy * df["AccTorRatio_Y"]

    # Final per the sheet: V = Direct + RealTor + ABS(AccTor)
    df["V_X"] = df["DirectShear_X"] + df["RealTor_X"] + np.abs(df["AccTor_X"])
    df["V_Y"] = df["DirectShear_Y"] + df["RealTor_Y"] + np.abs(df["AccTor_Y"])

    globals_out = {
        "sum_Ri_EW": sum_Ri_EW,
        "sum_Ri_NS": sum_Ri_NS,
        "xr_local": xr,
        "yr_local": yr,
        "xcg_local": xcg,
        "ycg_local": ycg,
        "ex_real": ex_real,
        "ey_real": ey_real,
        "ex_acc": ex_acc,
        "ey_acc": ey_acc,
        "Jpx": Jpx,
        "Jpy": Jpy,
        "Jp": Jp,
        "Wtot": Wtot,
    }
    return df, globals_out

def format_like_excel(df: pd.DataFrame) -> pd.DataFrame:
    """Order & round columns for an Excel-like table presentation."""
    cols = [
        "marker","L","H","w","x","y",
        "xk","yk","delta","Ri_EW","Ri_NS",
        "xbar","ybar",
        "DirectRatio_X","DirectShear_X",
        "RealTorRatio_X","RealTor_X",
        "AccTorRatio_X","AccTor_X",
        "V_X",
        "DirectRatio_Y","DirectShear_Y",
        "RealTorRatio_Y","RealTor_Y",
        "AccTorRatio_Y","AccTor_Y",
        "V_Y",
    ]
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    out = out[cols]
    # Round numeric columns for display
    for c in out.columns:
        if c != "marker":
            out[c] = pd.to_numeric(out[c], errors="coerce").round(6)
    return out

# -----------------------------
# UI
# -----------------------------
st.title("Rigid Diaphragm Shear Distribution (Excel-like)")

with st.sidebar:
    st.header("Global Inputs")

    c1, c2 = st.columns(2)
    with c1:
        Vx = st.number_input("Vx (kN)", value=67.0, step=1.0, format="%.6f")
        origin_x = st.number_input("Origin X (global)", value=0.0, step=0.1, format="%.6f")
        plan_dim_x = st.number_input("Plan Dim X (used for 10% accidental ecc)", value=1.0, step=0.1, format="%.6f")
        diaphragm_w = st.number_input("Diaphragm Weight (kN)", value=2456.0, step=1.0, format="%.6f")
        diaphragm_x = st.number_input("Diaphragm X (global)", value=0.5, step=0.1, format="%.6f")
    with c2:
        Vy = st.number_input("Vy (kN)", value=0.0, step=1.0, format="%.6f")
        origin_y = st.number_input("Origin Y (global)", value=0.0, step=0.1, format="%.6f")
        plan_dim_y = st.number_input("Plan Dim Y (used for 10% accidental ecc)", value=1.0, step=0.1, format="%.6f")
        diaphragm_y = st.number_input("Diaphragm Y (global)", value=0.5, step=0.1, format="%.6f")

    st.divider()
    st.caption("Markers must start with **EW** or **NS** to match the spreadsheet logic.")

# Default table (user can edit)
st.subheader("Wall Input Table")

default_rows = [
    {"marker":"EW01A","L":1.0,"H":2.0,"w":0.0,"x":0.0,"y":0.0},
    {"marker":"EW02A","L":1.0,"H":2.0,"w":0.0,"x":1.0,"y":0.0},
    {"marker":"NS01A","L":1.0,"H":2.0,"w":0.0,"x":0.0,"y":1.0},
    {"marker":"NS02A","L":1.0,"H":2.0,"w":0.0,"x":1.0,"y":1.0},
]
if "walls_df" not in st.session_state:
    st.session_state["walls_df"] = pd.DataFrame(default_rows)

edited = st.data_editor(
    st.session_state["walls_df"],
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "marker": st.column_config.TextColumn("marker", help="Start with EW or NS"),
        "L": st.column_config.NumberColumn("L", help="Wall length", format="%.6f"),
        "H": st.column_config.NumberColumn("H", help="Wall height", format="%.6f"),
        "w": st.column_config.NumberColumn("w", help="Wall weight (optional)", format="%.6f"),
        "x": st.column_config.NumberColumn("x", help="Global X coordinate", format="%.6f"),
        "y": st.column_config.NumberColumn("y", help="Global Y coordinate", format="%.6f"),
    },
    key="walls_editor"
)
st.session_state["walls_df"] = edited

inputs = dict(
    Vx=Vx, Vy=Vy,
    origin_x=origin_x, origin_y=origin_y,
    plan_dim_x=plan_dim_x, plan_dim_y=plan_dim_y,
    diaphragm_w=diaphragm_w, diaphragm_x=diaphragm_x, diaphragm_y=diaphragm_y,
)

run = st.button("Compute", type="primary")
if run:
    result_df, globals_out = compute_rigid_diaph(st.session_state["walls_df"], inputs)
    display_df = format_like_excel(result_df)

    st.subheader("Results (Excel-like)")
    st.dataframe(display_df, use_container_width=True, height=520)

    st.subheader("Global Results")
    g = globals_out
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Rigidity Center Xr (local)", f'{g["xr_local"]:.6f}' if not np.isnan(g["xr_local"]) else "—")
        st.metric("Rigidity Center Yr (local)", f'{g["yr_local"]:.6f}' if not np.isnan(g["yr_local"]) else "—")
        st.metric("ΣRi_EW", f'{g["sum_Ri_EW"]:.6f}')
        st.metric("ΣRi_NS", f'{g["sum_Ri_NS"]:.6f}')
    with m2:
        st.metric("Mass CG Xcg (local)", f'{g["xcg_local"]:.6f}' if not np.isnan(g["xcg_local"]) else "—")
        st.metric("Mass CG Ycg (local)", f'{g["ycg_local"]:.6f}' if not np.isnan(g["ycg_local"]) else "—")
        st.metric("Real ecc ex", f'{g["ex_real"]:.6f}' if not np.isnan(g["ex_real"]) else "—")
        st.metric("Real ecc ey", f'{g["ey_real"]:.6f}' if not np.isnan(g["ey_real"]) else "—")
    with m3:
        st.metric("Jpx", f'{g["Jpx"]:.6f}')
        st.metric("Jpy", f'{g["Jpy"]:.6f}')
        st.metric("Jp", f'{g["Jp"]:.6f}')
        st.metric("W total", f'{g["Wtot"]:.6f}')

    # Download
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download results as CSV", data=csv, file_name="rigid_results_streamlit.csv", mime="text/csv")

else:
    st.info("Edit the wall table and global inputs on the left, then click **Compute**.")
