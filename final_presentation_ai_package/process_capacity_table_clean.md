# Process Capacity Table

**Load basis:** For the main Cass/Cass Light brewing flow, the same standard batch load passes through each sequential process. Therefore, the load is kept at **7.5 batches/day** from milling through packaging.  
**Exception:** De-alcoholization is only for Cass 0.0, so it uses a separate SKU-specific load.

| Stage | Flow time | Capacity | Resource | Load | Util. |
|---|---:|---:|---|---:|---:|
| Milling | 1 h | 14.0 batches/day | Grain mill | 7.5 | 54% |
| Mashing | 4 h | 14.0 batches/day | Mash system | 7.5 | 54% |
| Wort filtration / Lautering | 2 h | 14.0 batches/day | Mash filter | 7.5 | 54% |
| Boiling / Hopping | 2 h | 12.0 batches/day | Kettle / whirlpool | 7.5 | 63% |
| Cooling / Wort transfer | 1 h | 12.0 batches/day | Cooler / transfer line | 7.5 | 63% |
| **Fermentation** | **~13–14 days** | **~8.0 batches/day** | **~99 vessels × 3,000 hL** | **7.5** | **~94%** |
| **Maturation / Conditioning** | **3 days** | **~20.7 batches/day** | **~62 vessels × 3,000 hL** | **7.5** | **~36%** |
| Final filtration / Centrifuge | ~1 h/batch | 9.6–11.2 batches/day | 2 centrifuge units | 7.5 | 67–78% |
| Bright beer / Holding | 1–2 days | ~13.0 batches/day | ~27 bright beer tanks | 7.5 | ~58% |
| Packaging | Same-day | ~10.0 batches/day | ~5 packaging lines | 7.5 | ~75% |
| De-alcoholization | 8 h | ~1.0 batch/day | Cass 0.0 unit | 0.3–0.4 | 30–40% |

**Bottleneck interpretation:** Since the main process load is constant at **7.5 batches/day**, the bottleneck is determined by the process with the lowest effective capacity. Fermentation has the highest utilization at **~94%**, while maturation is only **~36%** under the 3-day maturation assumption. Therefore, the dominant bottleneck is fermentation.
