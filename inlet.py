import io

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ParaInlet", page_icon="✈️", layout="wide")

# ---------------------------------------------------------------- constants
MAX_INLETS = 10
# Colour-blind-friendly palette, one fixed colour per inlet slot so an inlet
# keeps the same colour in every chart.
PALETTE = [
    "#4C78A8", "#F58518", "#54A24B", "#E45756", "#B279A2",
    "#72B7B2", "#EECA3B", "#FF9DA6", "#9D755D", "#8C8C8C",
]

# field -> (default, label, unit)
FIELDS = {
    "gamma": (1.4, "Gamma (γ)", ""),
    "mach": (2.0, "Free-stream Mach (Mi)", ""),
    "pr_th": (0.98, "Theoretical PR (Pt,e/Pt,i)th", ""),
    "pt_i": (101325.0, "Inlet Pt,i", "Pa"),
    "pt_e": (95000.0, "Exit Pt,e", "Pa"),
    "pt_max": (98000.0, "Pt,max", "Pa"),
    "pt_min": (92000.0, "Pt,min", "Pa"),
    "pt_avg": (95000.0, "Pt,avg", "Pa"),
    "tt_i": (300.0, "Total T in (Tt,i)", "K"),
    "tt_e": (350.0, "Total T out (Tt,e)", "K"),
    "t_i": (280.0, "Static T in (Ti)", "K"),
    "t_e": (330.0, "Static T out (Te)", "K"),
}

PRESETS = {
    "Default (Mach 2 demo)": {},
    "Subsonic pitot (M 0.8)": dict(
        mach=0.8, pr_th=0.995, pt_i=101325.0, pt_e=99800.0,
        pt_max=100500.0, pt_min=98800.0, pt_avg=99800.0,
        tt_i=300.0, tt_e=300.0, t_i=270.0, t_e=288.0),
    "Normal shock (M 1.5)": dict(
        mach=1.5, pr_th=0.93, pt_i=101325.0, pt_e=94200.0,
        pt_max=97000.0, pt_min=91000.0, pt_avg=94200.0,
        tt_i=300.0, tt_e=300.0, t_i=240.0, t_e=330.0),
    "Ext. compression (M 2.2)": dict(
        mach=2.2, pr_th=0.95, pt_i=101325.0, pt_e=88000.0,
        pt_max=91000.0, pt_min=84500.0, pt_avg=88000.0,
        tt_i=300.0, tt_e=300.0, t_i=215.0, t_e=380.0),
    "Mixed compression (M 3.0)": dict(
        mach=3.0, pr_th=0.90, pt_i=101325.0, pt_e=84000.0,
        pt_max=87500.0, pt_min=80500.0, pt_avg=84000.0,
        tt_i=300.0, tt_e=300.0, t_i=110.0, t_e=300.0),
}


# --------------------------------------------------------------- state utils
def key(field, i):
    return f"{field}_{i}"


def init_inlet(i):
    st.session_state.setdefault(key("name", i), f"Inlet {i + 1}")
    for f, (default, _, _) in FIELDS.items():
        st.session_state.setdefault(key(f, i), default)


def apply_values(i, values):
    for f, v in values.items():
        st.session_state[key(f, i)] = v


def apply_preset_cb():
    preset = PRESETS[st.session_state["preset_choice"]]
    target = st.session_state["preset_target"]
    n = st.session_state["num_inlets"]
    idxs = range(n) if target == "All inlets" else [int(target.split()[-1]) - 1]
    for i in idxs:
        # reset to defaults first so presets are complete, not a partial overlay
        apply_values(i, {f: d for f, (d, _, _) in FIELDS.items()})
        apply_values(i, preset)


def reset_cb():
    for k in [k for k in st.session_state if "_" in k and k.split("_")[-1].isdigit()]:
        del st.session_state[k]


def import_csv(upload):
    try:
        df = pd.read_csv(upload)
    except Exception as e:  # noqa: BLE001 - surface any parse error to the user
        st.sidebar.error(f"Could not read CSV: {e}")
        return
    missing = [f for f in FIELDS if f not in df.columns]
    if missing:
        st.sidebar.error(f"CSV is missing columns: {', '.join(missing)}")
        return
    df = df.head(MAX_INLETS)
    st.session_state["num_inlets"] = len(df)
    for i, row in df.reset_index(drop=True).iterrows():
        st.session_state[key("name", i)] = str(row.get("name", f"Inlet {i + 1}"))
        apply_values(i, {f: float(row[f]) for f in FIELDS})


# ----------------------------------------------------------------- physics
def mil_recovery(mach):
    """MIL-E-5008B total pressure recovery reference for a given Mach."""
    if mach <= 1:
        return 1.0
    if mach < 5:
        return 1 - 0.075 * (mach - 1) ** 1.35
    return 800 / (mach**4 + 935)


def calculate_parameters(d):
    pt_i, pt_e = d["pt_i"], d["pt_e"]
    recovery = pt_e / pt_i if pt_i else 0.0

    ke_eff = 0.0
    if d["mach"] > 0 and d["gamma"] > 1 and pt_e > 0 and pt_i > 0:
        exponent = (d["gamma"] - 1) / d["gamma"]
        temp_ratio = d["tt_e"] / d["tt_i"] if d["tt_i"] else 1
        bracket = temp_ratio * (pt_i / pt_e) ** exponent - 1
        ke_eff = 1 - bracket / ((d["gamma"] - 1) * d["mach"] ** 2)

    ad_eff = 0.0
    static_ratio = d["t_e"] / d["t_i"] if d["t_i"] else 1
    if static_ratio != 1:
        num = (d["gamma"] - 1) * d["mach"] ** 2 / 2
        ad_eff = 1 - num * (1 - ke_eff) / (static_ratio - 1)

    di = (d["pt_max"] - d["pt_min"]) / d["pt_avg"] if d["pt_avg"] > 0 else 0.0
    shock_eff = recovery / d["pr_th"] if d["pr_th"] > 0 else 0.0
    mil = mil_recovery(d["mach"])

    # Composite figure of merit (documented in the UI): pressure recovery,
    # kinetic-energy efficiency and flow uniformity, each clamped to [0, 1].
    clamp = lambda x: max(0.0, min(1.0, x))  # noqa: E731
    score = 100 * (0.4 * clamp(recovery) + 0.3 * clamp(ke_eff) + 0.3 * (1 - clamp(di)))

    return {
        "Name": d["name"],
        "Mach": d["mach"],
        "Recovery": recovery,
        "Pressure Loss (%)": (1 - recovery) * 100,
        "MIL-E-5008B Recovery": mil,
        "Δ vs MIL-E-5008B": recovery - mil,
        "KE Eff (%)": ke_eff * 100,
        "Adiabatic Eff (%)": ad_eff * 100,
        "Shock Eff (%)": shock_eff * 100,
        "Distortion": di,
        "Total T Ratio": d["tt_e"] / d["tt_i"] if d["tt_i"] else 0.0,
        "Static T Ratio": static_ratio,
        "Score": score,
    }


def validate(d):
    w = []
    if d["gamma"] <= 1:
        w.append("γ must be > 1.")
    if d["mach"] <= 0:
        w.append("Mach must be > 0.")
    if d["pt_i"] <= 0 or d["pt_e"] <= 0:
        w.append("Total pressures must be positive.")
    if d["pt_e"] > d["pt_i"]:
        w.append("Pt,e > Pt,i — recovery above 1 is unphysical for a passive inlet.")
    if d["pt_max"] < d["pt_min"]:
        w.append("Pt,max is lower than Pt,min.")
    if d["pt_avg"] > 0 and not d["pt_min"] <= d["pt_avg"] <= d["pt_max"]:
        w.append("Pt,avg lies outside [Pt,min, Pt,max].")
    if d["t_i"] <= 0 or d["tt_i"] <= 0:
        w.append("Temperatures must be positive (Kelvin).")
    if d["t_i"] > d["tt_i"] or d["t_e"] > d["tt_e"]:
        w.append("Static temperature exceeds total temperature.")
    if d["t_e"] == d["t_i"]:
        w.append("Ti = Te: adiabatic efficiency is undefined (reported as 0).")
    return w


# ----------------------------------------------------------------- charts
def color_scale(df):
    # keep each inlet's colour tied to its slot, not its sort position
    return alt.Scale(domain=list(df["Name"]), range=PALETTE[: len(df)])


def style(chart):
    return (
        chart.configure_axis(grid=True, gridOpacity=0.15, labelFontSize=12, titleFontSize=12)
        .configure_title(fontSize=15, anchor="start", fontWeight=600)
        .configure_view(stroke=None)
    )


def bar_chart(df, y, title, fmt=".2f", ref=None, ref_label=None, sort_desc=True):
    scale = color_scale(df)
    order = "-y" if sort_desc else "x"
    base = alt.Chart(df).encode(
        x=alt.X("Name:N", sort=order, axis=alt.Axis(labelAngle=0, title=None)),
        y=alt.Y(f"{y}:Q", title=None),
    )
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        color=alt.Color("Name:N", scale=scale, legend=None),
        tooltip=["Name", alt.Tooltip(f"{y}:Q", format=fmt)],
    )
    labels = base.mark_text(dy=-8, fontWeight=600).encode(
        text=alt.Text(f"{y}:Q", format=fmt)
    )
    layers = [bars, labels]
    if ref is not None:
        rule_df = pd.DataFrame({"ref": [ref]})
        layers.append(
            alt.Chart(rule_df).mark_rule(strokeDash=[6, 4], color="#888", size=2)
            .encode(y="ref:Q")
        )
        if ref_label:
            layers.append(
                alt.Chart(rule_df.assign(t=ref_label)).mark_text(
                    align="right", dx=-4, dy=-6, color="#888", fontSize=11
                ).encode(y="ref:Q", text="t:N", x=alt.value(10_000))
            )
    return style(alt.layer(*layers).properties(title=title, height=280))


def recovery_chart(df):
    """Recovery bars with a MIL-E-5008B reference tick for each inlet's Mach."""
    scale = color_scale(df)
    base = alt.Chart(df).encode(x=alt.X("Name:N", axis=alt.Axis(labelAngle=0, title=None)))
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        y=alt.Y("Recovery:Q", title=None, scale=alt.Scale(zero=False, padding=10)),
        color=alt.Color("Name:N", scale=scale, legend=None),
        tooltip=["Name", alt.Tooltip("Recovery:Q", format=".4f"),
                 alt.Tooltip("MIL-E-5008B Recovery:Q", format=".4f")],
    )
    ticks = base.mark_tick(color="#222", thickness=3, size=40).encode(
        y="MIL-E-5008B Recovery:Q"
    )
    labels = base.mark_text(dy=-8, fontWeight=600).encode(
        y="Recovery:Q", text=alt.Text("Recovery:Q", format=".3f")
    )
    return style(alt.layer(bars, ticks, labels).properties(
        title="Pressure recovery (π) — black tick = MIL-E-5008B at that Mach", height=280))


def mil_curve_chart(df):
    mach = [x / 20 for x in range(0, 121)]
    curve = pd.DataFrame({"Mach": mach, "Recovery": [mil_recovery(m) for m in mach]})
    line = alt.Chart(curve).mark_line(color="#888", strokeDash=[6, 4], size=2).encode(
        x=alt.X("Mach:Q", title="Mach number"),
        y=alt.Y("Recovery:Q", title="Total pressure recovery", scale=alt.Scale(zero=False)),
    )
    pts = alt.Chart(df).mark_point(filled=True, size=220, opacity=0.95).encode(
        x="Mach:Q", y="Recovery:Q",
        color=alt.Color("Name:N", scale=color_scale(df), legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Name", "Mach", alt.Tooltip("Recovery:Q", format=".4f")],
    )
    return style(alt.layer(line, pts).properties(
        title="Recovery vs Mach (dashed = MIL-E-5008B)", height=280))


def tradeoff_chart(df):
    pts = alt.Chart(df).mark_circle(opacity=0.9).encode(
        x=alt.X("Distortion:Q", title="Distortion index (lower is better)",
                scale=alt.Scale(zero=False, padding=15)),
        y=alt.Y("Recovery:Q", title="Pressure recovery (higher is better)",
                scale=alt.Scale(zero=False, padding=15)),
        size=alt.Size("KE Eff (%):Q", title="KE eff (%)", scale=alt.Scale(range=[150, 900])),
        color=alt.Color("Name:N", scale=color_scale(df), legend=None),
        tooltip=["Name", alt.Tooltip("Recovery:Q", format=".4f"),
                 alt.Tooltip("Distortion:Q", format=".4f"),
                 alt.Tooltip("KE Eff (%):Q", format=".2f")],
    )
    txt = pts.mark_text(dy=-18, fontWeight=600).encode(text="Name:N", size=alt.value(12))
    return style(alt.layer(pts, txt).properties(
        title="Recovery vs distortion trade-off (bubble = KE efficiency)", height=320))


def grouped_efficiency_chart(df):
    long = df.melt(id_vars="Name",
                   value_vars=["KE Eff (%)", "Adiabatic Eff (%)", "Shock Eff (%)"],
                   var_name="Metric", value_name="Value")
    return style(alt.Chart(long).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Metric:N", title=None, axis=alt.Axis(labelAngle=0, labelLimit=120)),
        xOffset="Name:N",
        y=alt.Y("Value:Q", title="Efficiency (%)"),
        color=alt.Color("Name:N", scale=color_scale(df), legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Name", "Metric", alt.Tooltip("Value:Q", format=".2f")],
    ).properties(title="Efficiency comparison", height=300))


def heatmap_chart(df):
    metrics = {
        "Recovery": True, "KE Eff (%)": True, "Adiabatic Eff (%)": True,
        "Shock Eff (%)": True, "Distortion": False,
    }
    rows = []
    for m, higher_better in metrics.items():
        lo, hi = df[m].min(), df[m].max()
        for _, r in df.iterrows():
            norm = 0.5 if hi == lo else (r[m] - lo) / (hi - lo)
            rows.append({"Name": r["Name"], "Metric": m, "Value": r[m],
                         "Rank score": norm if higher_better else 1 - norm})
    h = pd.DataFrame(rows)
    base = alt.Chart(h).encode(
        x=alt.X("Metric:N", title=None, axis=alt.Axis(labelAngle=0, labelLimit=110),
                sort=list(metrics)),
        y=alt.Y("Name:N", title=None, sort=list(df["Name"])),
    )
    rect = base.mark_rect(cornerRadius=3).encode(
        color=alt.Color("Rank score:Q", scale=alt.Scale(scheme="redyellowgreen", domain=[0, 1]),
                        legend=None),
        tooltip=["Name", "Metric", alt.Tooltip("Value:Q", format=".4f")],
    )
    text = base.mark_text(fontSize=12, fontWeight=600, color="#222").encode(
        text=alt.Text("Value:Q", format=".3g"))
    return style(alt.layer(rect, text).properties(
        title="Scorecard (green = best among inlets, red = worst)",
        height=max(120, 42 * len(df))))


# ------------------------------------------------------------------ sidebar
st.title("✈️ ParaInlet")
st.caption("Aerodynamic inlet performance calculator — compare up to 10 inlet configurations.")

with st.sidebar:
    st.header("Setup")
    num_inlets = st.number_input("Number of inlets", 1, MAX_INLETS, 1, key="num_inlets")

    st.subheader("Presets")
    st.selectbox("Preset", list(PRESETS), key="preset_choice")
    st.selectbox("Apply to", ["All inlets"] + [f"Inlet {i + 1}" for i in range(num_inlets)],
                 key="preset_target")
    st.button("Apply preset", on_click=apply_preset_cb, width="stretch")

    st.subheader("Data")
    upload = st.file_uploader("Import CSV", type="csv", help="Columns: name + all parameter fields. "
                              "Export a CSV first to get the template.")
    if upload is not None and st.session_state.get("_last_upload") != (upload.name, upload.size):
        st.session_state["_last_upload"] = (upload.name, upload.size)
        import_csv(upload)
        st.rerun()
    st.button("Reset all inputs", on_click=reset_cb, width="stretch")

# ------------------------------------------------------------------- inputs
for i in range(num_inlets):
    init_inlet(i)

st.subheader("Parameters")
tabs = st.tabs([st.session_state[key("name", i)] or f"Inlet {i + 1}" for i in range(num_inlets)])
for i, tab in enumerate(tabs):
    with tab:
        k = lambda f: key(f, i)  # noqa: E731
        st.text_input("Name", key=k("name"))
        st.caption("Flow properties")
        c1, c2, c3 = st.columns(3)
        c1.number_input("Gamma (γ)", key=k("gamma"), format="%.2f", step=0.01)
        c2.number_input("Free-stream Mach (Mi)", key=k("mach"), format="%.2f", step=0.1)
        c3.number_input("Theoretical PR (Pt,e/Pt,i)th", key=k("pr_th"), format="%.3f", step=0.005)
        st.caption("Total pressures [Pa]")
        p1, p2 = st.columns(2)
        p1.number_input("Inlet Pt,i", key=k("pt_i"), step=100.0)
        p2.number_input("Exit Pt,e", key=k("pt_e"), step=100.0)
        st.caption("Distortion pressures [Pa]")
        d1, d2, d3 = st.columns(3)
        d1.number_input("Pt,max", key=k("pt_max"), step=100.0)
        d2.number_input("Pt,min", key=k("pt_min"), step=100.0)
        d3.number_input("Pt,avg", key=k("pt_avg"), step=100.0)
        st.caption("Temperatures [K]")
        t1, t2, t3, t4 = st.columns(4)
        t1.number_input("Total T in (Tt,i)", key=k("tt_i"), step=1.0)
        t2.number_input("Total T out (Tt,e)", key=k("tt_e"), step=1.0)
        t3.number_input("Static T in (Ti)", key=k("t_i"), step=1.0)
        t4.number_input("Static T out (Te)", key=k("t_e"), step=1.0)

inlets = [
    {"name": st.session_state[key("name", i)] or f"Inlet {i + 1}",
     **{f: st.session_state[key(f, i)] for f in FIELDS}}
    for i in range(num_inlets)
]
# duplicate names would merge colours/bars, so make them unique
seen = {}
for d in inlets:
    n = seen.get(d["name"], 0)
    seen[d["name"]] = n + 1
    if n:
        d["name"] = f"{d['name']} ({n + 1})"

for d in inlets:
    for w in validate(d):
        st.warning(f"**{d['name']}** — {w}", icon="⚠️")

st.divider()

# ------------------------------------------------------------------ results
df = pd.DataFrame([calculate_parameters(d) for d in inlets])
best = df.loc[df["Score"].idxmax()]

st.subheader("Results")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Best overall", best["Name"], f"score {best['Score']:.1f}", delta_color="off")
k2.metric("Highest recovery", df.loc[df["Recovery"].idxmax(), "Name"], f"{df['Recovery'].max():.4f}", delta_color="off")
k3.metric("Highest KE efficiency", df.loc[df["KE Eff (%)"].idxmax(), "Name"], f"{df['KE Eff (%)'].max():.2f}%", delta_color="off")
k4.metric("Lowest distortion", df.loc[df["Distortion"].idxmin(), "Name"], f"{df['Distortion'].min():.4f}", delta_color="off")
st.caption("Score = 100 × (0.4·recovery + 0.3·KE efficiency + 0.3·(1 − distortion)), each term clamped to [0, 1].")

tab_over, tab_charts, tab_table = st.tabs(["Overview", "Charts", "Table & export"])

with tab_over:
    left, right = st.columns(2)
    left.altair_chart(tradeoff_chart(df), width="stretch")
    right.altair_chart(mil_curve_chart(df), width="stretch")
    st.altair_chart(heatmap_chart(df), width="stretch")
    st.altair_chart(bar_chart(df, "Score", "Overall score (0–100)", fmt=".1f"),
                    width="stretch")

with tab_charts:
    a, b = st.columns(2)
    a.altair_chart(bar_chart(df, "KE Eff (%)", "Kinetic energy efficiency (%)"), width="stretch")
    b.altair_chart(bar_chart(df, "Adiabatic Eff (%)", "Adiabatic compression efficiency (%)"), width="stretch")
    c, d = st.columns(2)
    c.altair_chart(recovery_chart(df), width="stretch")
    d.altair_chart(bar_chart(df, "Distortion", "Distortion index (lower is better)", fmt=".4f", sort_desc=False),
                   width="stretch")
    e, f = st.columns(2)
    e.altair_chart(bar_chart(df, "Shock Eff (%)", "Shock compression efficiency (%)"), width="stretch")
    f.altair_chart(bar_chart(df, "Pressure Loss (%)", "Total pressure loss (%) (lower is better)",
                             sort_desc=False), width="stretch")
    st.altair_chart(grouped_efficiency_chart(df), width="stretch")

with tab_table:
    st.dataframe(
        df.style.format({
            "Mach": "{:.2f}", "Recovery": "{:.4f}", "Pressure Loss (%)": "{:.2f}",
            "MIL-E-5008B Recovery": "{:.4f}", "Δ vs MIL-E-5008B": "{:+.4f}",
            "KE Eff (%)": "{:.2f}", "Adiabatic Eff (%)": "{:.2f}", "Shock Eff (%)": "{:.2f}",
            "Distortion": "{:.4f}", "Total T Ratio": "{:.3f}", "Static T Ratio": "{:.3f}",
            }),
        column_config={"Score": st.column_config.ProgressColumn(
            "Score", min_value=0, max_value=100, format="%.1f")},
        width="stretch", hide_index=True,
    )
    dl1, dl2 = st.columns(2)
    dl1.download_button("⬇️ Download results (CSV)", df.to_csv(index=False),
                        "parainlet_results.csv", "text/csv", width="stretch")
    inputs_df = pd.DataFrame(inlets)[["name", *FIELDS]]
    dl2.download_button("⬇️ Download inputs (CSV, re-importable)", inputs_df.to_csv(index=False),
                        "parainlet_inputs.csv", "text/csv", width="stretch")
