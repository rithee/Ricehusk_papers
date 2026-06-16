#!/usr/bin/env python3
"""Generate extraction/2026.json"""
import json
from pathlib import Path

data = {
    "year": 2026,
    "rha_dataset": [],
    "non_rha_agro_ash": [],
    "excluded_papers": [
        {
            "paper_id": "2026_01",
            "paper_title": "Stacked-based machine learning to predict the uniaxial compressive strength of concrete materials",
            "reason": "ML on Yeh UCI 1030 OPC mixes (cement, slag, FA, aggregates, water, SP); no RHA variable or experiments.",
        },
        {
            "paper_id": "2026_02",
            "paper_title": "Predicting the compressive strength of concrete with fly ash admixture using machine learning algorithms",
            "reason": "Own 98 fly-ash concrete mixes (Annexure A); RHA appears only in literature-review Table 1, not in experimental program.",
        },
        {
            "paper_id": "2026_03",
            "paper_title": "Evaluating compressive strength of concrete made with recycled concrete aggregates using machine learning approach",
            "reason": "RCA concrete ML meta-analysis (721 literature samples); no RHA in mix variables.",
        },
        {
            "paper_id": "2026_04",
            "paper_title": "Residual compressive strength of concrete after exposure to high temperatures: A review and probabilistic models",
            "reason": "Post-fire residual-strength review (1240 data points); SCMs are FA/SF/slag, not RHA; not standard cured mix design data.",
        },
        {
            "paper_id": "2026_05",
            "paper_title": "Relationship between fractal feature and compressive strength of concrete based on MIP",
            "reason": "OPC + silica fume pore-fractal study (C10-C150); no RHA. Strengths in figures only.",
        },
        {
            "paper_id": "2026_06",
            "paper_title": "High correlated variables creator machine: Prediction of the compressive strength of concrete",
            "reason": "NDT-based ML (UPV + rebound); 516 pooled literature points; no mix design with RHA.",
        },
        {
            "paper_id": "2026_07",
            "paper_title": "Prediction of concrete compressive strength using support vector machine regression and non-destructive testing",
            "reason": "NDT + SVR case study on 180 OPC specimens (Poorarbabi & Ghasemi); no RHA.",
        },
    ],
    "cited_sources_to_fetch": [
        {
            "from_paper": "2026_01",
            "citation": "Yeh I-C, Concrete Compressive Strength, UCI Machine Learning Repository (1030 OPC mix records: cement, slag, FA, water, SP, aggregates, age -> CS).",
            "reason": "Primary training database for stacked ML paper; no RHA but bulk OPC strength data.",
            "doi": None,
        },
        {
            "from_paper": "2026_02",
            "citation": "Song et al. 98 fly-ash concrete mixes (Annexure A: kg/m3 + CS at 3/7/14/28/56/90d); Table 1 cites external RHA ML datasets from other authors.",
            "reason": "FA concrete experimental DB; Table 1 lists RHA studies by others for literature comparison.",
            "doi": "10.1016/j.conbuildmat.2021.125021",
        },
        {
            "from_paper": "2026_03",
            "citation": "721 RCA concrete samples compiled from 67 literature sources (Tran et al. Table 1).",
            "reason": "Bulk RCA compressive-strength database for ML; no RHA.",
            "doi": "10.1016/j.conbuildmat.2022.126578",
        },
        {
            "from_paper": "2026_04",
            "citation": "1240 post-fire residual compressive strength data points from 53 articles (1990-2020).",
            "reason": "Bulk post-fire strength database; SCM subset includes FA/SF/slag not RHA.",
            "doi": "10.1016/j.firesaf.2022.103698",
        },
        {
            "from_paper": "2026_06",
            "citation": "516 NDT data points pooled from 8 prior UPV/rebound studies (Na, Poorarbabi, Rashid, Mulik, Arioz, Domingo, Bahmani, Asteris).",
            "reason": "Bulk NDT-to-strength database; no RHA mix proportions.",
            "doi": None,
        },
        {
            "from_paper": "2026_07",
            "citation": "180-specimen dataset from Poorarbabi & Ghasemi (20 OPC mix schemes x 3 ages, NDT + destructive CS).",
            "reason": "Bulk NDT OPC mix/strength database cited by SVR paper.",
            "doi": "10.1016/j.cscm.2024.e03416",
        },
    ],
}

# Map paper_id -> source filename
source_map = {
    "2026_01": "2026/1-s2.0-S0045794925000021-main.pdf",
    "2026_02": "2026/1-s2.0-S0950061821027677-main.pdf",
    "2026_03": "2026/1-s2.0-S0950061822002707-main.pdf",
    "2026_04": "2026/1-s2.0-S0379711222001758-main.pdf",
    "2026_05": "2026/1-s2.0-S0950061822001969-main.pdf",
    "2026_06": "2026/1-s2.0-S0045794921000018-main.pdf",
    "2026_07": "2026/1-s2.0-S2214509524005679-main.pdf",
}
for ex in data["excluded_papers"]:
    ex["source_file"] = source_map.get(ex["paper_id"])

out = Path(__file__).resolve().parents[1] / "extraction" / "2026.json"
out.write_text(json.dumps(data, indent=2) + "\n")
print(f"Wrote {out}: 0 extracted, {len(data['excluded_papers'])} excluded, {len(data['cited_sources_to_fetch'])} to-fetch")
