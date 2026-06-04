# OB Cass Process Capacity and Bottleneck Summary

## Core message

OB Brewery's internal process-level capacity data are not public. This analysis therefore normalizes public data from comparable large lager breweries to an OB-scale production proxy. The main benchmark is SAB Alrode Brewery, with supporting evidence from AB InBev Leuven / GEA, Steinecker, and Krones.

## Load basis

- OB production proxy: `1,637,210 kL/year × 55.3% ≈ 905,377 kL/year = 9.05 million hL/year`
- SAB Alrode benchmark: 8.8 million hL/year; 176,000 hL/week brewing; 205,000 hL/week packaging; 96 fermentation vessels × 3,000 hL; 60 maturation vessels × 3,000 hL
- Scale factor: `9.05 / 8.8 ≈ 1.029`
- Planning load: `176,000 hL/week × 1.029 / 7 × 87% ≈ 22,505 hL/day`
- Standard batch: `3,000 hL`; therefore load is `~7.5 batches/day`

## Process capacity table

| Stage | Capacity | Load | Utilization | Interpretation |
|---|---:|---:|---:|---|
| Milling | 14.0 batches/day | 7.5 | 54% | Slack |
| Mashing | 14.0 | 7.5 | 54% | Slack |
| Wort filtration / Lautering | 14.0 | 7.5 | 54% | Slack |
| Boiling / Hopping | 12.0 | 7.5 | 63% | Not constraining |
| Cooling / Wort transfer | 12.0 | 7.5 | 63% | Not constraining |
| Fermentation | ~8.0 | 7.5 | ~94% | Primary bottleneck |
| Maturation / Conditioning | ~8.6 | 7.5 | ~87% | Secondary constraint |
| Final filtration / Centrifuge | 9.6–11.2 | 7.5 | 67–78% | Some slack |
| Bright beer / Holding | ~13.0 | 7.5 | ~58% | Buffer |
| Packaging | ~10.0 | 7.5 | ~75% | Slack |

## Conclusion

Upstream brewing, final filtration, and packaging all have lower utilization than fermentation. Fermentation reaches about 94% utilization because beer occupies scarce tanks for roughly 13–14 days. Therefore, the dominant bottleneck is the fermentation-centered cold block, not packaging or upstream brewing.

## Main sources

1. SASSDA, “Stainless Steel in Breweries” — SAB Alrode capacity and vessel count  
   https://sassda.co.za/news-home/stainless-steel-magazine/stainless-steel-magazine-archives/august-2016/stainless-steel-in-breweries/
2. Steinecker, “Lautering with a mash filter” — output of 14 brews/day  
   https://www.steinecker.com/en/products/mash-filter.php
3. GEA, “How AB InBev and GEA teamed up to build a new cold block in Leuven” — tank size and centrifuge capacity  
   https://www.gea.com/en/customer-cases/ab-inbev-brewery/
4. Krones, “Modulfill HES” — high-speed bottle filling  
   https://www.krones.com/en/products/machines/modulfill-hes-beer.php
5. Krones, “Can Filling: Innovative Systems” — high-speed can-line reference  
   https://www.krones.com/en/products/bottling-lines-for-cans.php
