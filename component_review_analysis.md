# Component Review Analysis

Pre-change analysis of the 39 `needs_review = 1` components auto-added during stream extraction.
Generated before any database changes were made.

---

## Merges — duplicate aliases of existing components (29 components)

| needs_review component | → merge into | reason |
|---|---|---|
| CM228 `NC3-A` | CM169 `Propane` (N-C3A) | same naming convention, missing hyphen |
| CM229 `hexane` | CM133 `n-Hexane` (HX) | generic name, only hexane in table |
| CM230 `2-methyhexane` | CM018 `2-Methylhexane` (MEHX) | typo (missing 'l') |
| CM237 `methyhexane` | CM018 `2-Methylhexane` (MEHX) | same typo, single methylhexane in table |
| CM240 `methylhexane` | CM018 `2-Methylhexane` (MEHX) | unqualified methylhexane, only one in table |
| CM251 `2-MEHX` | CM018 `2-Methylhexane` (MEHX) | direct abbreviation match |
| CM241 `methyl heptane` | CM023 `3-Methylheptane` (MEHP) | only methylheptane in table |
| CM252 `3-MEHP` | CM023 `3-Methylheptane` (MEHP) | direct abbreviation match |
| CM242 `3.3-dimethylpentane` | CM022 `3,3-Dimethylpentane` (DMP) | period-for-comma typo |
| CM243 `1.3-cyclopentadiene` | CM068 `Cyclopentadiene` (CYPD) | period-for-comma typo; 1,3-CPD = cyclopentadiene |
| CM233 `butane` | CM132 `n-Butane` (N-C4A) | generic name = n-butane |
| CM244 `Butadiene` | CM008 `1,3-Butadiene` (BDI-13) | industrial default; stream named "Butadiene" confirms |
| CM246 `Isobutene` | CM102 `Isobutylene` (I-C4E) | same compound, two names |
| CM245 `n-pentene` | CM013 `1-Pentene` (C5E) | n-pentene = 1-pentene (straight chain) |
| CM236 `ethyl benzene` | CM082 `Ethylbenzene` (EB) | space in name |
| CM247 `4-Trimethylbenzene` | CM005 `1,2,4-Trimethylbenzene` (TMB) | abbreviated locant; only TMB in table |
| CM248 `DCPD` | CM069 `Dicyclopentadiene` (DCYPD) | DCPD is the universal abbreviation |
| CM250 `Naphth` | CM130 `Naphtha` (NAPHTHA) | truncated name |
| CM253 `Sulfonale` | CM197 `Sulfolane` (SL) | typo (transposed letters) |
| CM254 `N-C1A` | CM111 `Methane` (CH4) | N-C1A follows N-C2A=Ethane, N-C3A=Propane pattern |
| CM256 `TRILINOL` | CM216 `Trilinolein` (LLL) | process code for trilinolein |
| CM257 `NAOCH3` | CM190 `Sodium methoxide` (CH3ONA) | NaOCH₃ = sodium methoxide formula |
| CM261 `GLYC` | CM092 `Glycerol` (GLY) | abbreviated code |
| CM262 `PTA` | CM202 `Terephthalic acid` (TPA) | PTA = purified terephthalic acid, industry standard |
| CM263 `CH3OH` | CM112 `Methanol` (MEOH) | molecular formula for methanol |
| CM265 `C2H6` | CM079 `Ethane` (N-C2A) | molecular formula for ethane |
| CM266 `Terbutylalcohol` | CM204 `tert-Butyl alcohol` (T-BUOH) | alternate spelling |
| CM235 `propylmercaptan` | CM146 `n-propylmercaptan` (N-PMC) | same compound |
| CM239 `propyl mercaptan` | CM146 `n-propylmercaptan` (N-PMC) | same compound, space variant |

---

## New entries — genuinely absent, enriched and set needs_review = 0

| component | action |
|---|---|
| CM238 `propylene mercaptan` | Allyl mercaptan (prop-2-ene-1-thiol), CAS 870-23-5, MW 74.14, C3, category `organic` |
| CM255 `food waste` | Not a chemical, category `named_material`, no CAS/MW |

---

## Still needs manual review — needs_review = 1, notes added to DB

| component | reason |
|---|---|
| CM231 `3-methyl heptane 5% o-xylene` | Parser artifact — this name appears to be a fragment of a composition string. Re-examine source CSV row for stream `HC Reformate import`. |
| CM232 `butene` | Isomer not specified; appears in 7 streams. Could be 1-butene (CM012), cis-2-butene (CM064), trans-2-butene (CM212), or isobutylene (CM102). Resolve from source data. |
| CM234 `BDI` | Ambiguous abbreviation. DB has BDI-12 (1,2-Butadiene, CM006) and BDI-13 (1,3-Butadiene, CM008). Check source data to determine isomer. |
| CM249 `Pyridine/Pyrrole` | Two compounds listed as one entry. Pyridine exists as CM178. Pyrrole is absent from nomenclature (CAS 109-97-7, MW 67.09, 4C). Split into two stream_composition rows manually. |
| CM258 `METHY-01` | Process sim code, likely a fatty acid methyl ester (oleate/linoleate/linolenate) — all three exist in table but order unknown. Check sim model. |
| CM259 `METHY-02` | Same as METHY-01. |
| CM260 `METHY-03` | Same as METHY-01. |
| CM264 `METFORM` | Likely methyl formate (CM118, MF) — common byproduct in methanol synthesis light streams. Confirm before merging. |
