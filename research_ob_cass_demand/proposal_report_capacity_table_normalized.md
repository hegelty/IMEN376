# Proposal Report Capacity Table — Benchmark-Based Bottleneck Analysis

Date: 2026-06-04  
Target process: OB Brewery Cass / Cass Light / Cass 0.0 brewing operations

---

## 1. Estimation Principle

OB Brewery's actual process-level capacities, tank counts, and line-level capacities are not publicly disclosed. Therefore, this table is not an internal OB measurement. It is a **benchmark-based capacity estimate**, normalized from publicly documented large lager breweries to an OB-scale production proxy.

The table keeps the original Proposal Report format:

```text
Stage / Flow time / Capacity / Resource / Load / Util. / Comment
```

The key correction is that the 87% operating level reported for SAB Alrode is **not copied into every process**. It is used only to define the planning load. Each process capacity is estimated separately from public equipment or plant benchmarks.

---

## 2. Load and Unit Basis

### OB production proxy

```text
OB annual production proxy
= 2024 Korea domestic beer shipments × 2024H1 OB home-market manufacturer share
= 1,637,210 kL/year × 55.3%
≈ 905,377 kL/year
= 9,053,770 hL/year
```

### Standard batch unit

- SAB Alrode: fermentation and maturation vessels are **3,000 hL** each.
- AB InBev Leuven: new cold-block tanks are **2,700 hL** and **4,700 hL**.

Therefore, this model uses:

```text
1 standard batch = 3,000 hL
```

### Planning load

```text
Scale factor
= OB proxy / SAB Alrode annual capacity
= 9,053,770 / 8,800,000
≈ 1.029

OB-equivalent nominal brewing capacity
= 176,000 hL/week × 1.029 / 7
≈ 25,868 hL/day

Planning load, using Alrode's reported 87% operating level
= 25,868 hL/day × 0.87
≈ 22,505 hL/day

Planning load in standard batches
= 22,505 / 3,000
≈ 7.5 batches/day
```

---

## 3. Process Capacity Table

| Stage | Flow time | Capacity | Resource | Load | Util. | Comment |
|---|---:|---:|---|---:|---:|---|
| Milling | 1 h | **14.0 batches/day** | Grain handling and milling system sized to feed a high-rate Steinecker brewhouse | **7.5** | **54%** | Slack process. Milling does not occupy product for multiple days and is sized to support brewhouse input. |
| Mashing | 4 h | **14.0 batches/day** | Steinecker mash/lauter system; mash-filter benchmark supports up to 14 brews/day | **7.5** | **54%** | Slack process. Public Steinecker data support high daily brew rates, so this stage is not the bottleneck. |
| Wort filtration / Lautering | 2 h | **14.0 batches/day** | Steinecker mash filter / lautering block | **7.5** | **54%** | Slack process. Steinecker explicitly reports short lautering times and 14 brews/day output. |
| Boiling / Hopping | 2 h | **12.0 batches/day** | Kettle / whirlpool block, conservatively set below mash-filter maximum | **7.5** | **63%** | Not constraining. The active processing time is short and can be scheduled within the brewhouse day. |
| Cooling / Wort transfer | 1 h | **12.0 batches/day** | Cooling and transfer equipment sized to brewhouse output | **7.5** | **63%** | Not constraining. It must follow brew starts but does not create long-residence WIP. |
| **Fermentation** | **~13–14 days** | **~8.0 batches/day** | **~99 fermentation-vessel equivalents × 3,000 hL** | **7.5** | **~94%** | **Primary bottleneck.** Capacity is limited by 13–14 days of tank occupancy, not by instantaneous line speed. Contamination, quality issues, or SKU changeovers can quickly consume the remaining slack. |
| **Maturation / Conditioning** | **~7–8 days** | **~8.6 batches/day** | **~62 maturation-vessel equivalents × 3,000 hL** | **7.5** | **~87%** | Secondary cold-block constraint. It is slightly less tight than fermentation, but still highly utilized because beer remains in tanks for a week-scale residence time. |
| Final filtration / Centrifuge | ~1 h per standard batch, parallel operation | **9.6–11.2 batches/day** | Two GEA GSE-550-equivalent centrifuge units; each unit rated at 600–700 hL/hour | **7.5** | **67–78%** | Some slack. Important for quality and yield, but two industrial units can process more than the daily planning load. |
| Bright beer / Holding | 1–2 days | **~13.0 batches/day** | ~27 bright beer tanks, scaled from Alrode's 26 bright beer tanks by the 1.029 scale factor | **7.5** | **~58%** | Buffer stage before packaging. It smooths downstream operations and is less bottleneck-prone than fermentation and maturation. |
| Packaging | Same-day operation | **~10.0 batches/day** | Alrode packaging capacity of 205,000 hL/week and five packaging lines, scaled to OB proxy | **7.5** | **~75%** | Slack relative to the cold block. Packaging capacity is higher than the planning load and can absorb daily scheduling variation. |
| De-alcoholization | 8 h | **~1.0 batch/day** | One dedicated Cass 0.0 de-alcoholization unit, illustrative SKU-specific estimate | **0.3–0.4** | **30–40%** | Cass 0.0 only. Not a family-level bottleneck at low non-alcohol volume share, but it could become a SKU-level bottleneck if Cass 0.0 demand grows sharply. |

---

## 4. Evidence and Calculations

### SAB Alrode Brewery benchmark

| Item | Public figure | Use in this model |
|---|---:|---|
| Annual capacity | **8.8 million hL/year** | Scale-factor denominator |
| Weekly brewing capacity | **176,000 hL/week** | OB-equivalent nominal brewing capacity |
| Weekly packaging capacity | **205,000 hL/week** | Packaging capacity estimate |
| Reported operating level | **87% of capacity** | Used only to define planning load |
| Brewhouse | **600 hL brewlength × 2 + 1,500 hL brewlength × 1** | Large-lager brewhouse benchmark |
| Fermentation vessels | **96 vessels × 3,000 hL** | Fermentation tank-count and tank-size benchmark |
| Maturation vessels | **60 vessels × 3,000 hL** | Maturation tank-count and tank-size benchmark |
| Bright beer tanks | **26 tanks** | Bright beer / holding estimate |
| Packaging lines | **5 lines** | Packaging-line benchmark |

Source: SASSDA, “Stainless Steel in Breweries”  
https://sassda.co.za/news-home/stainless-steel-magazine/stainless-steel-magazine-archives/august-2016/stainless-steel-in-breweries/

### OB-scale normalization

```text
Scale factor = 9,053,770 / 8,800,000 ≈ 1.029

Brewing capacity
= 176,000 hL/week × 1.029
≈ 181,075 hL/week
≈ 25,868 hL/day

Packaging capacity
= 205,000 hL/week × 1.029
≈ 210,912 hL/week
≈ 30,130 hL/day
≈ 10.0 batches/day

Fermentation vessels
= 96 × 1.029
≈ 99 vessels

Maturation vessels
= 60 × 1.029
≈ 62 vessels

Bright beer tanks
= 26 × 1.029
≈ 27 tanks
```

### Steinecker mash-filter evidence

Steinecker reports:

- “more than 12 brews per day”
- “output of 14 brews per day”

Therefore, mashing and lautering capacity is set at **14 batches/day**.

```text
Mashing/Lautering utilization
= 7.5 / 14.0
≈ 54%
```

Source: Steinecker, “Lautering with a mash filter”  
https://www.steinecker.com/en/products/mash-filter.php

### AB InBev Leuven / GEA evidence

GEA's AB InBev Leuven case reports:

| Item | Public figure |
|---|---:|
| New cold-block tanks | 36 tanks |
| Total tanks after expansion | 116 tanks |
| Tank group 1 | 16 tanks × 4,700 hL |
| Tank group 2 | 20 tanks × 2,700 hL |
| New cold-block volume | 129,200 hL |
| GSE-550 centrifuge capacity | 600–700 hL/hour |

Tank-size calculation:

```text
New cold-block volume
= 16 × 4,700 + 20 × 2,700
= 129,200 hL
```

This validates the 3,000 hL standard-batch assumption because it falls inside the 2,700–4,700 hL industrial tank range.

Centrifuge calculation:

```text
Capacity with two centrifuge-equivalent units
= 600–700 hL/hour × 2 × 24 hours/day
= 28,800–33,600 hL/day
= 9.6–11.2 batches/day

Utilization
= 7.5 / 9.6 to 7.5 / 11.2
≈ 78% to 67%
```

Source: GEA, “How AB InBev and GEA teamed up to build a new cold block in Leuven”  
https://www.gea.com/en/customer-cases/ab-inbev-brewery/

### Krones packaging evidence

Packaging capacity is primarily based on SAB Alrode's public plant-level packaging capacity:

```text
OB-normalized packaging capacity
= 205,000 hL/week × 1.029
= 210,912 hL/week
= 30,130 hL/day
= ~10.0 batches/day

Packaging utilization
= 7.5 / 10.0
≈ 75%
```

Krones data support the interpretation that packaging is a high-speed line process rather than a week-scale residence-time constraint:

- Modulfill HES glass bottle filler: up to **78,000 containers/hour**.
- Can-line equipment reference: can inspection at **33 cans/second**.

Sources:
- Krones, “Modulfill HES”  
  https://www.krones.com/en/products/machines/modulfill-hes-beer.php
- Krones, “Can Filling: Innovative Systems”  
  https://www.krones.com/en/products/bottling-lines-for-cans.php

### Fermentation and maturation capacity

Fermentation:

```text
Fermentation vessels ≈ 99
Tank size = 3,000 hL
Residence time ≈ 13–14 days

Daily capacity
= 99 × 3,000 / 13–14
≈ 21,214–22,846 hL/day
≈ 7.1–7.6 batches/day
```

The table uses a rounded value of **~8.0 batches/day** to allow scheduling buffers, tank overlap, and practical operating flexibility.

```text
Fermentation utilization
= 7.5 / 8.0
≈ 94%
```

Maturation:

```text
Maturation vessels ≈ 62
Tank size = 3,000 hL
Residence time ≈ 7–8 days

Daily capacity
= 62 × 3,000 / 7–8
≈ 23,250–26,571 hL/day
≈ 7.75–8.86 batches/day
```

The table uses **~8.6 batches/day**.

```text
Maturation utilization
= 7.5 / 8.6
≈ 87%
```

---

## 5. Report-Ready Interpretation

The revised capacity table shows that the dominant bottleneck is the **fermentation-centered cold block**. Milling, mashing, lautering, boiling, and cooling operate at roughly **54–63% utilization** because their active processing times are short and their rated capacities are higher than the planning load. Packaging is also below the bottleneck level at about **75% utilization**, and final filtration/centrifuge capacity is about **67–78%**.

In contrast, fermentation reaches approximately **94% utilization**, and maturation reaches approximately **87% utilization**. This difference occurs because fermentation and maturation capacity is governed by tank residence time rather than instantaneous line speed. Once a batch enters a fermentation tank, that tank cannot be used for another batch for roughly 13–14 days. Therefore, demand spikes, contamination, quality failures, or SKU changeovers directly constrain the production schedule through tank availability. The primary operational bottleneck is therefore not packaging or upstream brewing, but fermentation tank capacity.

---

## 6. References

1. SASSDA, “Stainless Steel in Breweries” — SAB Alrode capacity, vessel count, packaging lines  
   https://sassda.co.za/news-home/stainless-steel-magazine/stainless-steel-magazine-archives/august-2016/stainless-steel-in-breweries/
2. Steinecker, “Lautering with a mash filter” — more than 12 brews/day, output of 14 brews/day  
   https://www.steinecker.com/en/products/mash-filter.php
3. GEA, “How AB InBev and GEA teamed up to build a new cold block in Leuven” — tank sizes, 116 tanks, centrifuge 600–700 hL/hour  
   https://www.gea.com/en/customer-cases/ab-inbev-brewery/
4. Krones, “Modulfill HES” — glass bottle filler up to 78,000 containers/hour  
   https://www.krones.com/en/products/machines/modulfill-hes-beer.php
5. Krones, “Can Filling: Innovative Systems” — high-speed can line / 33 cans per second can inspection reference  
   https://www.krones.com/en/products/bottling-lines-for-cans.php
