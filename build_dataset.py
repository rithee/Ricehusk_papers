# -*- coding: utf-8 -*-
"""
Compile per-year extraction JSON files in extraction/ into a single Excel workbook.
One row per (mix x curing age) for the RHA dataset.
"""
import json, glob, os
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
EXTRACT = ROOT / "extraction"
OUT = ROOT / "RHA_concrete_ML_dataset.xlsx"

RHA_COLS = [
    "year", "paper_id", "paper_title", "authors", "country_region", "rha_source_location",
    "material_type", "primary_binder_scm", "mix_id",
    "cement_kg_m3", "rha_kg_m3", "rha_pct_cement_replacement",
    "fine_agg_kg_m3", "course_agg_kg_m3",
    "other_additives_used_and_quantity", "water_cement_ratio",
    "curing_age_days",
    "comp_strength_MPa", "flexural_strength_MPa", "split_tensile_strength_MPa",
    "output_availability", "value_source", "data_origin", "notes", "evidence", "source_file",
]


def rha_rows():
    rows = []
    for jf in sorted(EXTRACT.glob("*.json")):
        data = json.loads(jf.read_text())
        year = data.get("year")
        for paper in data.get("rha_dataset", []):
            base = {
                "year": year,
                "paper_id": paper.get("paper_id"),
                "paper_title": paper.get("paper_title"),
                "authors": paper.get("authors"),
                "country_region": paper.get("country_region"),
                "rha_source_location": paper.get("rha_source_location"),
                "material_type": paper.get("material_type"),
                "primary_binder_scm": paper.get("primary_binder_scm"),
                "output_availability": paper.get("output_availability"),
                "value_source": paper.get("value_source"),
                "data_origin": paper.get("data_origin"),
                "notes": paper.get("notes"),
                "evidence": paper.get("evidence"),
                "source_file": paper.get("source_file"),
            }
            for mix in paper.get("mixes", []):
                mbase = dict(base)
                mbase.update({
                    "mix_id": mix.get("mix_id"),
                    "cement_kg_m3": mix.get("cement_kg_m3"),
                    "rha_kg_m3": mix.get("rha_kg_m3"),
                    "rha_pct_cement_replacement": mix.get("rha_pct_cement_replacement"),
                    "fine_agg_kg_m3": mix.get("fine_agg_kg_m3"),
                    "course_agg_kg_m3": mix.get("coarse_agg_kg_m3"),
                    "other_additives_used_and_quantity": mix.get("other_additives"),
                    "water_cement_ratio": mix.get("water_cement_ratio"),
                })
                strengths = mix.get("strengths", [])
                if not strengths:
                    rows.append({**mbase, "curing_age_days": None,
                                 "comp_strength_MPa": None, "flexural_strength_MPa": None,
                                 "split_tensile_strength_MPa": None})
                else:
                    for s in strengths:
                        rows.append({**mbase,
                                     "curing_age_days": s.get("age"),
                                     "comp_strength_MPa": s.get("comp"),
                                     "flexural_strength_MPa": s.get("flexural"),
                                     "split_tensile_strength_MPa": s.get("split")})
    df = pd.DataFrame(rows)
    for c in RHA_COLS:
        if c not in df.columns:
            df[c] = None
    return df[RHA_COLS] if not df.empty else pd.DataFrame(columns=RHA_COLS)


def collect(key, cols):
    rows = []
    for jf in sorted(EXTRACT.glob("*.json")):
        data = json.loads(jf.read_text())
        for item in data.get(key, []):
            item = dict(item)
            item.setdefault("year", data.get("year"))
            rows.append(item)
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns:
            df[c] = None
    front = [c for c in cols if c in df.columns]
    rest = [c for c in df.columns if c not in front]
    return df[front + rest]


def data_dictionary():
    rows = [
        ("year", "Publication year (folder)"),
        ("paper_id", "Internal paper id (year_index)"),
        ("country_region", "SPATIAL: country/region where the study was conducted"),
        ("rha_source_location", "SPATIAL: where the rice husk / RHA was sourced + burning condition"),
        ("material_type", "concrete / mortar / SCC / HPC etc."),
        ("primary_binder_scm", "Binder system, e.g. OPC+RHA, OPC+RHA+FA"),
        ("mix_id", "Mix identifier within the paper"),
        ("cement_kg_m3", "Cement content (kg/m3). Blank = not reported in kg/m3"),
        ("rha_kg_m3", "Rice husk ash content (kg/m3) if reported"),
        ("rha_pct_cement_replacement", "INPUT: RHA as % replacement of cement by weight"),
        ("fine_agg_kg_m3", "INPUT: fine aggregate (sand) kg/m3"),
        ("course_agg_kg_m3", "INPUT: coarse aggregate kg/m3 (user spelling 'course')"),
        ("other_additives_used_and_quantity", "INPUT: other SCMs/admixtures/fibers + quantity"),
        ("water_cement_ratio", "INPUT: water/cement (or water/binder) ratio"),
        ("curing_age_days", "TEMPORAL: curing age at test (days)"),
        ("comp_strength_MPa", "OUTPUT: compressive strength (MPa = N/mm2)"),
        ("flexural_strength_MPa", "OUTPUT: flexural strength / modulus of rupture (MPa)"),
        ("split_tensile_strength_MPa", "OUTPUT: splitting tensile strength (MPa)"),
        ("output_availability", "tabulated / partial / figure_only  data quality flag"),
        ("value_source", "Where values came from: table/text/computed/figure"),
        ("data_origin", "primary (this study) or cited (from a referenced paper)"),
        ("notes", "Caveats, assumptions, unit conversions"),
        ("evidence", "Verbatim quote / table reference supporting the numbers"),
    ]
    return pd.DataFrame(rows, columns=["column", "description"])


def main():
    rha = rha_rows()
    non_rha = collect("non_rha_agro_ash",
                      ["year", "paper_id", "paper_title", "country_region", "primary_material",
                       "data_available", "key_values", "reason"])
    excluded = collect("excluded_papers", ["year", "paper_id", "paper_title", "reason"])
    tofetch = collect("cited_sources_to_fetch",
                      ["year", "from_paper", "citation", "reason", "doi"])
    ddict = data_dictionary()

    with pd.ExcelWriter(OUT, engine="openpyxl") as w:
        rha.to_excel(w, index=False, sheet_name="RHA_dataset")
        non_rha.to_excel(w, index=False, sheet_name="NonRHA_agro_ash")
        excluded.to_excel(w, index=False, sheet_name="Excluded_papers")
        tofetch.to_excel(w, index=False, sheet_name="Cited_sources_to_fetch")
        ddict.to_excel(w, index=False, sheet_name="Data_dictionary")
        for ws in w.book.worksheets:
            ws.freeze_panes = "A2"
            for col in ws.columns:
                letter = col[0].column_letter
                width = 16
                if letter in ("A",):
                    width = 8
                ws.column_dimensions[letter].width = width
    print(f"Wrote {OUT}")
    print(f"RHA dataset rows: {len(rha)}")
    print(f"  papers in RHA sheet: {rha['paper_id'].nunique()}")
    print(f"  rows with comp strength: {rha['comp_strength_MPa'].notna().sum()}")
    print(f"NonRHA agro-ash entries: {len(non_rha)}")
    print(f"Excluded papers: {len(excluded)}")
    print(f"Cited sources to fetch: {len(tofetch)}")


if __name__ == "__main__":
    main()
