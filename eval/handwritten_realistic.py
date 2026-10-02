"""Hand-written realistic held-out slips. Never used in training.

Lines were generated in code (`SPECS` below), not handwritten by Vedant.
Gold is the dict next to each line in this file. They are de-identified
typical clinic / caregiver slips (clinic print, doctor shorthand, WhatsApp).
NOT photographed prescriptions. Created after FT2 at git 5619cee.

67 of 102 lines use drug names that also appear in data/synth/train.jsonl
(counted from those files). Treat as a dev set, not a drug-held-out test.

The photographed test set is Public real-world set: HMR-100 (India)
(data/public/ + data/public_labels/hmr100_gold.jsonl). Never call it family data.
"""

from __future__ import annotations

import json
from pathlib import Path

from pillclerk.schema import MedLine

ROOT = Path(__file__).resolve().parents[1]
HELD = ROOT / "data" / "heldout" / "handwritten_realistic.jsonl"
REAL = ROOT / "data" / "real" / "gt.jsonl"


def _d(morning=0.0, afternoon=0.0, night=0.0, unit="tab") -> dict:
    return {"morning": morning, "afternoon": afternoon, "night": night, "unit": unit}


# (rx_id, style, line, gold_kwargs)
SPECS: list[tuple[str, str, str, dict]] = [
    # --- Rx01 diabetes + BP clinic print ---
    ("rx01", "clinic_print", "TAB. Glycomet 500MG  1-0-1  AFTER FOOD  x 30 DAYS",
     dict(drug="Glycomet", strength="500MG", form="tab", dose=_d(1, 0, 1), food="after", duration_days=30)),
    ("rx01", "clinic_print", "TAB. Telma 40MG  1-0-0  EMPTY STOMACH  x 30 DAYS",
     dict(drug="Telma", strength="40MG", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=30)),
    ("rx01", "clinic_print", "TAB. Ecosprin 75MG  0-0-1  AFTER FOOD  CONTINUE",
     dict(drug="Ecosprin", strength="75MG", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    ("rx01", "clinic_print", "TAB. Atorva 10MG  0-0-1  AFTER FOOD  CONTINUE",
     dict(drug="Atorva", strength="10MG", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    ("rx01", "clinic_print", "TAB. Thyronorm 50MCG  1-0-0  EMPTY STOMACH  CONTINUE",
     dict(drug="Thyronorm", strength="50MCG", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=None)),
    ("rx01", "clinic_print", "SACHET Calcirol 60k  1-0-0  AFTER FOOD  WEEKLY x 90 DAYS",
     dict(drug="Calcirol", strength="60k", form="sachet", dose=_d(1, 0, 0, "sachet"), food="after", duration_days=90, every_n_days=7)),
    # --- Rx02 cardiology doctor short ---
    ("rx02", "doctor_short", "Tab Clopitab 75mg HS PC cont",
     dict(drug="Clopitab", strength="75mg", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    ("rx02", "doctor_short", "Cap Ecosprin AV 75mg/10mg HS PC 1/12",
     dict(drug="Ecosprin AV", strength="75mg/10mg", form="cap", dose=_d(0, 0, 1, "cap"), food="after", duration_days=30)),
    ("rx02", "doctor_short", "Tab Telma AM 40mg/5mg OD ES 1/12",
     dict(drug="Telma AM", strength="40mg/5mg", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=30)),
    ("rx02", "doctor_short", "Tab Metolar 25mg BD AC x30d",
     dict(drug="Metolar", strength="25mg", form="tab", dose=_d(1, 0, 1), food="before", duration_days=30)),
    ("rx02", "doctor_short", "Tab Rozavel 10mg HS PC cont",
     dict(drug="Rozavel", strength="10mg", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    # --- Rx03 GERD + pain ---
    ("rx03", "doctor_short", "Cap Pan 40mg BD AC x14d",
     dict(drug="Pan", strength="40mg", form="cap", dose=_d(1, 0, 1, "cap"), food="before", duration_days=14)),
    ("rx03", "clinic_print", "TAB. Dolo 650MG  SOS / PRN max 3/d  x 3 DAYS",
     dict(drug="Dolo", strength="650MG", form="tab", kind="prn", food="any", duration_days=3, prn_max_per_day=3)),
    ("rx03", "clinic_print", "TAB. Combiflam 400MG  SOS / PRN max 2/d  x 5 DAYS",
     dict(drug="Combiflam", strength="400MG", form="tab", kind="prn", food="any", duration_days=5, prn_max_per_day=2)),
    # --- Rx04 steroid taper ---
    ("rx04", "clinic_print", "TAB. Wysolone 10 mg  1-0-1 x 5d then 0-0-1 x 5d  AFTER FOOD",
     dict(drug="Wysolone", strength="10 mg", form="tab", kind="taper", food="after", duration_days=10,
          taper=[{"dose": _d(1, 0, 1), "days": 5}, {"dose": _d(0, 0, 1), "days": 5}])),
    ("rx04", "clinic_print", "TAB. Pantop 40MG  1-0-0  BEFORE FOOD  x 10 DAYS",
     dict(drug="Pantop", strength="40MG", form="tab", dose=_d(1, 0, 0), food="before", duration_days=10)),
    # --- Rx05 respiratory ---
    ("rx05", "clinic_print", "INH. Foracort 200MCG  1-0-1  x 30 DAYS",
     dict(drug="Foracort", strength="200MCG", form="inhaler", dose=_d(1, 0, 1, "puff"), food="any", duration_days=30)),
    ("rx05", "doctor_short", "Inh Asthalin puff SOS",
     dict(drug="Asthalin", form="inhaler", kind="prn", food="any")),
    ("rx05", "clinic_print", "SYR. Ascoril LS  5-0-5  AFTER FOOD  x 5 DAYS",
     dict(drug="Ascoril LS", form="syrup", dose=_d(5, 0, 5, "ml"), food="after", duration_days=5)),
    ("rx05", "clinic_print", "INH. Duolin  1-1-1  x 7 DAYS",
     dict(drug="Duolin", form="inhaler", dose=_d(1, 1, 1, "puff"), food="any", duration_days=7)),
    # --- Rx06 insulin + oral ---
    ("rx06", "clinic_print", "INJ. Lantus 100 IU/ml  0-0-12  NIGHT",
     dict(drug="Lantus", strength="100 IU/ml", form="injection", dose=_d(0, 0, 12, "unit"), food="any", duration_days=None)),
    ("rx06", "clinic_print", "INJ. Novorapid 100 IU/ml  6-6-6  BEFORE FOOD  CONTINUE",
     dict(drug="Novorapid", strength="100 IU/ml", form="injection", dose=_d(6, 6, 6, "unit"), food="before", duration_days=None)),
    ("rx06", "clinic_print", "TAB. Glycomet SR 1000MG  0-0-1  AFTER FOOD  CONTINUE",
     dict(drug="Glycomet SR", strength="1000MG", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    # --- Rx07 eyes + cream ---
    ("rx07", "clinic_print", "DROPS Refresh Tears  1-1-1  x 15 DAYS",
     dict(drug="Refresh Tears", form="drops", dose=_d(1, 1, 1, "drop"), food="any", duration_days=15)),
    ("rx07", "clinic_print", "DROPS Ciplox D  1-0-1  x 7 DAYS",
     dict(drug="Ciplox D", form="drops", dose=_d(1, 0, 1, "drop"), food="any", duration_days=7)),
    ("rx07", "clinic_print", "CREAM Betnovate  0-0-1  x 7 DAYS",
     dict(drug="Betnovate", form="cream", dose=_d(0, 0, 1, "apply"), food="any", duration_days=7)),
    # --- Rx08 UTI ---
    ("rx08", "clinic_print", "CAP Nitrofurantoin 100 mg  1-0-1  AFTER FOOD  x 7 DAYS",
     dict(drug="Nitrofurantoin", strength="100 mg", form="cap", dose=_d(1, 0, 1, "cap"), food="after", duration_days=7)),
    ("rx08", "clinic_print", "TAB. Pan 40MG  1-0-0  BEFORE FOOD  x 7 DAYS",
     dict(drug="Pan", strength="40MG", form="tab", dose=_d(1, 0, 0), food="before", duration_days=7)),
    # --- Rx09 half-tab + 1-1-1 ---
    ("rx09", "clinic_print", "TAB. Ecosprin 75MG  ½-0-½  AFTER FOOD  x 30 DAYS",
     dict(drug="Ecosprin", strength="75MG", form="tab", dose=_d(0.5, 0, 0.5), food="after", duration_days=30)),
    ("rx09", "clinic_print", "TAB. Amlong 5MG  ½-0-0  AFTER FOOD  x 30 DAYS",
     dict(drug="Amlong", strength="5MG", form="tab", dose=_d(0.5, 0, 0), food="after", duration_days=30)),
    ("rx09", "clinic_print", "TAB. Januvia 100MG  1-0-0  AFTER FOOD  x 30 DAYS",
     dict(drug="Januvia", strength="100MG", form="tab", dose=_d(1, 0, 0), food="after", duration_days=30)),
    ("rx09", "clinic_print", "TAB. Glycomet GP1 500mg/1mg  1-0-1  AFTER FOOD  x 30 DAYS",
     dict(drug="Glycomet GP1", strength="500mg/1mg", form="tab", dose=_d(1, 0, 1), food="after", duration_days=30)),
    # --- Rx10 weekly D3 doctor short ---
    ("rx10", "doctor_short", "Tab Uprise D3 60k OD PC WEEKLY x90d",
     dict(drug="Uprise D3", strength="60k", form="tab", dose=_d(1, 0, 0), food="after", duration_days=90, every_n_days=7)),
    ("rx10", "doctor_short", "Tab Shelcal 500 BD PC 1/12",
     dict(drug="Shelcal", strength="500", form="tab", dose=_d(1, 0, 1), food="after", duration_days=30)),
    # --- Rx11 sachet + drops kids vs aaji ---
    ("rx11", "clinic_print", "SACHET Econorm  1-0-1  AFTER FOOD  x 5 DAYS",
     dict(drug="Econorm", form="sachet", dose=_d(1, 0, 1, "sachet"), food="after", duration_days=5)),
    ("rx11", "clinic_print", "SYR. Ambrodil LS  5-0-5  AFTER FOOD  x 5 DAYS",
     dict(drug="Ambrodil LS", form="syrup", dose=_d(5, 0, 5, "ml"), food="after", duration_days=5)),
    # --- Rx12 thyroid combo ---
    ("rx12", "doctor_short", "Tab Thyronorm 75mcg OD ES cont",
     dict(drug="Thyronorm", strength="75mcg", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=None)),
    ("rx12", "doctor_short", "Tab Eltroxin 50mcg OD ES cont",
     dict(drug="Eltroxin", strength="50mcg", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=None)),
    # --- Rx13 GP2 TDS ---
    ("rx13", "doctor_short", "Tab Glycomet GP2 500mg/2mg TDS PC x30d",
     dict(drug="Glycomet GP2", strength="500mg/2mg", form="tab", dose=_d(1, 1, 1), food="after", duration_days=30)),
    ("rx13", "doctor_short", "Tab Forxiga 10mg OD PC 1/12",
     dict(drug="Forxiga", strength="10mg", form="tab", dose=_d(1, 0, 0), food="after", duration_days=30)),
    # --- Rx14 cream + sachet calcium ---
    ("rx14", "clinic_print", "CREAM Volini  0-0-1  x 10 DAYS",
     dict(drug="Volini", form="cream", dose=_d(0, 0, 1, "apply"), food="any", duration_days=10)),
    ("rx14", "clinic_print", "SACHET Gemcal  0-0-1  AFTER FOOD  x 30 DAYS",
     dict(drug="Gemcal", form="sachet", dose=_d(0, 0, 1, "sachet"), food="after", duration_days=30)),
    # --- Rx15 constipation syrup ---
    ("rx15", "clinic_print", "SYR. Duphalac  15-0-15  AFTER FOOD  x 7 DAYS",
     dict(drug="Duphalac", form="syrup", dose=_d(15, 0, 15, "ml"), food="after", duration_days=7)),
    ("rx15", "clinic_print", "TAB. Dulcoflex 5MG  0-0-1  AFTER FOOD  x 5 DAYS",
     dict(drug="Dulcoflex", strength="5MG", form="tab", dose=_d(0, 0, 1), food="after", duration_days=5)),
    # --- WhatsApp hinglish caregiver ---
    ("wa01", "hinglish_wa", "aaji ko Glycomet 500 subah ek raat ko ek khane ke baad 30 din",
     dict(drug="Glycomet", strength="500", form="tab", dose=_d(1, 0, 1), food="after", duration_days=30)),
    ("wa02", "hinglish_wa", "Telma 40 subah ek khali pet dena continue",
     dict(drug="Telma", strength="40", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=None)),
    ("wa03", "hinglish_wa", "Ecosprin 75 raat ko ek khane ke baad",
     dict(drug="Ecosprin", strength="75", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    ("wa04", "hinglish_wa", "Pan 40 subah ek khane se pehle 14 din",
     dict(drug="Pan", strength="40", form="tab", dose=_d(1, 0, 0), food="before", duration_days=14)),
    ("wa05", "hinglish_wa", "Dolo 650 zarurat pe max 3/d 3 din",
     dict(drug="Dolo", strength="650", form="tab", kind="prn", food="any", duration_days=3, prn_max_per_day=3)),
    ("wa06", "hinglish_wa", "Calcirol 60k hafte mein ek baar khane ke baad 90 din",
     dict(drug="Calcirol", strength="60k", form="tab", dose=_d(1, 0, 0), food="after", duration_days=90, every_n_days=7)),
    ("wa07", "hinglish_wa", "Asthalin inhaler zarurat pe puff",
     dict(drug="Asthalin", form="inhaler", kind="prn", food="any")),
    ("wa08", "hinglish_wa", "Lantus 12 unit raat ko",
     dict(drug="Lantus", form="injection", dose=_d(0, 0, 12, "unit"), food="any", duration_days=None)),
    ("wa09", "hinglish_wa", "Amlong aadhi tablet subah khane ke baad 30 din",
     dict(drug="Amlong", form="tab", dose=_d(0.5, 0, 0), food="after", duration_days=30)),
    ("wa10", "hinglish_wa", "Wysolone 10 1-0-1 5 din then 0-0-1 5 din khane ke baad",
     dict(drug="Wysolone", strength="10", form="tab", kind="taper", food="after", duration_days=10,
          taper=[{"dose": _d(1, 0, 1), "days": 5}, {"dose": _d(0, 0, 1), "days": 5}])),
    # --- Hindi Devanagari ---
    ("hi01", "hindi", "टैब ग्लाइकोमेट 500 सुबह एक रात एक खाने के बाद 30 दिन",
     dict(drug="ग्लाइकोमेट", strength="500", form="tab", dose=_d(1, 0, 1), food="after", duration_days=30)),
    ("hi02", "hindi", "टेल्मा 40 सुबह एक खाली पेट 30 दिन",
     dict(drug="टेल्मा", strength="40", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=30)),
    ("hi03", "hindi", "इकोस्प्रिन 75 रात एक खाने के बाद",
     dict(drug="इकोस्प्रिन", form="tab", strength="75", dose=_d(0, 0, 1), food="after", duration_days=None)),
    ("hi04", "hindi", "पैन 40 सुबह एक खाने से पहले 14 दिन",
     dict(drug="पैन", strength="40", form="tab", dose=_d(1, 0, 0), food="before", duration_days=14)),
    ("hi05", "hindi", "डोलो 650 जरूरत पर",
     dict(drug="डोलो", strength="650", form="tab", kind="prn", food="any")),
    ("hi06", "hindi", "थाइरोनॉर्म 50 सुबह एक खाली पेट",
     dict(drug="थाइरोनॉर्म", strength="50", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=None)),
    # --- Marathi ---
    ("mr01", "marathi", "टॅब Glycomet 500 सकाळी एक रात्री एक जेवणानंतर 30 दिवस",
     dict(drug="Glycomet", strength="500", form="tab", dose=_d(1, 0, 1), food="after", duration_days=30)),
    ("mr02", "marathi", "Telma 40 सकाळी एक उपाशीपोटी continue",
     dict(drug="Telma", strength="40", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=None)),
    ("mr03", "marathi", "Ecosprin 75 रात्री एक जेवणानंतर",
     dict(drug="Ecosprin", strength="75", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    ("mr04", "marathi", "Pan 40 सकाळी एक जेवणाआधी 14 दिवस",
     dict(drug="Pan", strength="40", form="tab", dose=_d(1, 0, 0), food="before", duration_days=14)),
    ("mr05", "marathi", "Dolo 650 गरजेनुसार दिवसाला 3",
     dict(drug="Dolo", strength="650", form="tab", kind="prn", food="any", prn_max_per_day=3)),
    ("mr06", "marathi", "Calcirol 60k आठवड्यातून एकदा जेवणानंतर 90 दिवस",
     dict(drug="Calcirol", strength="60k", form="tab", dose=_d(1, 0, 0), food="after", duration_days=90, every_n_days=7)),
    # --- Mixed / clinic extras stressing form ---
    ("rx16", "clinic_print", "CAP Pregaba 75MG  0-0-1  AFTER FOOD  x 30 DAYS",
     dict(drug="Pregaba", strength="75MG", form="cap", dose=_d(0, 0, 1, "cap"), food="after", duration_days=30)),
    ("rx16", "clinic_print", "CAP Becosules  1-0-0  AFTER FOOD  x 15 DAYS",
     dict(drug="Becosules", form="cap", dose=_d(1, 0, 0, "cap"), food="after", duration_days=15)),
    ("rx16", "clinic_print", "DROPS Zincovit  0.5-0-0.5  AFTER FOOD  x 10 DAYS",
     dict(drug="Zincovit", form="drops", dose=_d(0.5, 0, 0.5, "drop"), food="after", duration_days=10)),
    ("rx16", "clinic_print", "INH. Seroflo  1-0-1  x 30 DAYS",
     dict(drug="Seroflo", form="inhaler", dose=_d(1, 0, 1, "puff"), food="any", duration_days=30)),
    ("rx16", "clinic_print", "INJ. Mixtard 30/70  10-0-8  BEFORE FOOD  CONTINUE",
     dict(drug="Mixtard", strength="30/70", form="injection", dose=_d(10, 0, 8, "unit"), food="before", duration_days=None)),
    # --- doctor latin food ---
    ("rx17", "doctor_short", "Tab Cardace 5mg OD AC x30d",
     dict(drug="Cardace", strength="5mg", form="tab", dose=_d(1, 0, 0), food="before", duration_days=30)),
    ("rx17", "doctor_short", "Tab Envas 5mg BD WF x30d",
     dict(drug="Envas", strength="5mg", form="tab", dose=_d(1, 0, 1), food="with", duration_days=30)),
    ("rx17", "doctor_short", "Tab Losar 50mg OD PC 1/12",
     dict(drug="Losar", strength="50mg", form="tab", dose=_d(1, 0, 0), food="after", duration_days=30)),
    ("rx17", "doctor_short", "Tab Cilacar 10mg HS PC cont",
     dict(drug="Cilacar", strength="10mg", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    ("rx17", "doctor_short", "Tab Storvas 20mg HS PC cont",
     dict(drug="Storvas", strength="20mg", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    # --- ASK / hard negatives (copy ASK, never guess) ---
    ("ask1", "hard", "Tab [?] 500mg 1-[?]-[?] x 30d",
     dict(drug=None, strength="500mg", form="tab", kind="daily", dose=None, food="any", duration_days=30,
          needs_check=["drug", "dose", "schedule"], note="partially illegible")),
    ("ask2", "hard", "Tab Glycomet 500mg as directed",
     dict(drug="Glycomet", strength="500mg", form="tab", kind="daily", dose=None, food="any", duration_days=None,
          needs_check=["dose", "schedule", "duration_days"], note="as directed")),
    ("ask3", "hard", "Cap Pan 40mg as directed",
     dict(drug="Pan", strength="40mg", form="cap", kind="daily", dose=None, food="any", duration_days=None,
          needs_check=["dose", "schedule", "duration_days"], note="as directed")),
    ("ask4", "hard", "Tab Telma 40mg x 30d",
     dict(drug="Telma", strength="40mg", form="tab", kind="daily", dose=None, food="any", duration_days=30,
          needs_check=["dose", "schedule"], note="frequency not written")),
    ("ask5", "hard", "SYR. Ascoril LS AFTER FOOD x 5 DAYS",
     dict(drug="Ascoril LS", form="syrup", kind="daily", dose=None, food="after", duration_days=5,
          needs_check=["dose", "schedule"], note="frequency not written")),
    # --- more food / dose stress ---
    ("rx18", "clinic_print", "TAB. Jardiance 10MG  1-0-0  BEFORE FOOD  x 30 DAYS",
     dict(drug="Jardiance", strength="10MG", form="tab", dose=_d(1, 0, 0), food="before", duration_days=30)),
    ("rx18", "clinic_print", "TAB. Trajenta 5MG  1-0-0  WITH FOOD  x 30 DAYS",
     dict(drug="Trajenta", strength="5MG", form="tab", dose=_d(1, 0, 0), food="with", duration_days=30)),
    ("rx18", "clinic_print", "TAB. Galvus Met 50 mg/500 mg  1-0-1  AFTER FOOD  x 30 DAYS",
     dict(drug="Galvus Met", strength="50 mg/500 mg", form="tab", dose=_d(1, 0, 1), food="after", duration_days=30)),
    ("rx18", "mixed", "Tab Glycomet 500mg सुबह एक रात एक khane ke baad x30d",
     dict(drug="Glycomet", strength="500mg", form="tab", dose=_d(1, 0, 1), food="after", duration_days=30)),
    ("rx18", "mixed", "Cap Pan 40 BD खाने से पहले 14 दिन",
     dict(drug="Pan", strength="40", form="cap", dose=_d(1, 0, 1, "cap"), food="before", duration_days=14)),
    ("rx19", "clinic_print", "TAB. Autrin  1-0-0  AFTER FOOD  x 30 DAYS",
     dict(drug="Autrin", form="tab", dose=_d(1, 0, 0), food="after", duration_days=30)),
    ("rx19", "clinic_print", "CAP Evion 400MG  1-0-0  AFTER FOOD  x 15 DAYS",
     dict(drug="Evion", strength="400MG", form="cap", dose=_d(1, 0, 0, "cap"), food="after", duration_days=15)),
    ("rx19", "clinic_print", "TAB. Zincovit  1-0-0  AFTER FOOD  x 15 DAYS",
     dict(drug="Zincovit", form="tab", dose=_d(1, 0, 0), food="after", duration_days=15)),
    ("rx20", "doctor_short", "Tab Amaryl 1mg OD PC x30d",
     dict(drug="Amaryl", strength="1mg", form="tab", dose=_d(1, 0, 0), food="after", duration_days=30)),
    ("rx20", "doctor_short", "Tab Diamicron XR 60mg OD PC 1/12",
     dict(drug="Diamicron XR", strength="60mg", form="tab", dose=_d(1, 0, 0), food="after", duration_days=30)),
    ("rx20", "doctor_short", "Tab Pioglar 15mg OD PC x30d",
     dict(drug="Pioglar", strength="15mg", form="tab", dose=_d(1, 0, 0), food="after", duration_days=30)),
    ("wa11", "hinglish_wa", "aaji ki BP ki dawai Telma AM 40/5 subah khali pet 30 din",
     dict(drug="Telma AM", strength="40/5", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=30)),
    ("wa12", "hinglish_wa", "Refresh Tears drops subah dopahar raat 15 din",
     dict(drug="Refresh Tears", form="drops", dose=_d(1, 1, 1, "drop"), food="any", duration_days=15)),
    ("wa13", "hinglish_wa", "Betnovate cream raat ko lagana 7 din",
     dict(drug="Betnovate", form="cream", dose=_d(0, 0, 1, "apply"), food="any", duration_days=7)),
    ("wa14", "hinglish_wa", "Duphalac 15ml subah 15ml raat khane ke baad 7 din",
     dict(drug="Duphalac", form="syrup", dose=_d(15, 0, 15, "ml"), food="after", duration_days=7)),
    ("wa15", "hinglish_wa", "Foracort inhaler subah ek raat ek 30 din",
     dict(drug="Foracort", form="inhaler", dose=_d(1, 0, 1, "puff"), food="any", duration_days=30)),
    ("wa16", "hinglish_wa", "Thyronorm 50 subah khali pet continue, paani ke saath",
     dict(drug="Thyronorm", strength="50", form="tab", dose=_d(1, 0, 0), food="empty_stomach", duration_days=None)),
    ("wa17", "hinglish_wa", "Clopitab 75 raat ko khane ke baad continue",
     dict(drug="Clopitab", strength="75", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    ("wa18", "hinglish_wa", "Novorapid 6 unit subah dopahar raat khane se pehle",
     dict(drug="Novorapid", form="injection", dose=_d(6, 6, 6, "unit"), food="before", duration_days=None)),
    ("wa19", "hinglish_wa", "aaji ko Atorva 10 raat ko khane ke baad dena",
     dict(drug="Atorva", strength="10", form="tab", dose=_d(0, 0, 1), food="after", duration_days=None)),
    ("wa20", "hinglish_wa", "Shelcal 500 subah ek raat ek khane ke baad 1 mahina",
     dict(drug="Shelcal", strength="500", form="tab", dose=_d(1, 0, 1), food="after", duration_days=30)),
]


def rows() -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for rx_id, style, line, kwargs in SPECS:
        gold = MedLine(**kwargs)
        key = " ".join(line.lower().split())
        if key in seen:
            raise ValueError(f"duplicate line: {line}")
        seen.add(key)
        out.append(
            {
                "line": line,
                "gold": json.loads(gold.model_dump_json()),
                "source": rx_id,
                "style": style,
                "synthetic": False,
                "held_out": True,
                "authored": "code:eval/handwritten_realistic.py",
            }
        )
    return out


def write() -> dict[str, int]:
    data = rows()
    HELD.parent.mkdir(parents=True, exist_ok=True)
    blob = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in data)
    HELD.write_text(blob, encoding="utf-8")
    rx = {r["source"] for r in data}
    return {"n": len(data), "sources": len(rx), "whatsapp": sum(1 for r in data if r["source"].startswith("wa"))}


if __name__ == "__main__":
    print(json.dumps(write(), indent=2))
