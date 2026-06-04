# OB맥주/Cass 공정별 Capacity 근거자료 벤치마크

작성일: 2026-06-04  
목적: IMEN376/POM 프로젝트의 Cass 양조 공정 capacity, bottleneck, flow-time 수치를 기존 “LLM 추정”이 아니라 공개자료 + 공학적 산식으로 방어 가능하게 정리한다.

---

## 1. 먼저 결론

1. **OB맥주의 공장별·공정별 실측 capacity는 공개자료에서 직접 확인되지 않는다.** OB 공개/홍보 자료는 이천·청주·광주 3개 생산공장 존재, 이천공장이 3개 공장 중 최대 규모, 청주공장 제맥공정 보유, 광주공장 수출 생산 등을 설명하지만, 발효탱크 수·라인별 kL/day 같은 내부 수치는 공개하지 않는다.
2. 따라서 보고서에는 “실측값”이라고 쓰면 위험하고, **공개 시장규모로 필요한 연간 생산량을 anchor한 뒤, 맥주공장 설비/공정 벤치마크로 공정별 capacity를 역산한 normalized engineering model**이라고 쓰는 게 안전하다.
3. 기존 M2 모델의 핵심 논리 — **발효/숙성 탱크 점유가 bottleneck** — 은 공개 벤치마크와 잘 맞는다. 다만 기존 `20 fermentation tanks`는 OB 전체 공장 실측치라기보다 “표준 batch-equivalent 단위의 정규화 모델”로 처리하는 편이 낫다.
4. OB 전체 생산 규모를 2024H1 가정시장 제조사 점유율 proxy 기준 약 **905,377 kL/year**로 잡으면, 발효 14일·가동률 85% 기준 필요한 총 발효 working volume은 약 **40,855 kL**이다. 탱크 1기가 300~500 kL라면 약 **82~136기**가 필요하다. 이는 3개 공장 전체 또는 복수 라인 기준의 규모감이며, 기존 “20 tanks”만으로 OB 전체를 설명하기엔 작다.

---

## 2. 확인한 공개 근거

| 구분 | 확인 내용 | 프로젝트에서 쓰는 의미 | 출처 |
|---|---|---|---|
| OB 공장 구조 | OB/AB InBev Korea는 이천, 청주, 광주 3개 공장을 운영. 이천은 3개 공장 중 가장 큰 규모, 양조기술연구소·신제품/파일럿 생산. 청주는 제맥공정 보유. 광주는 4개 대륙 17개국 수출 생산. | OB가 단일 소형공장이 아니라 복수 대형 생산거점을 가진다는 근거. 공장별 실측 capacity는 미공개. | AB InBev Korea 오비맥주 공장소개, Naver Blog, https://m.blog.naver.com/abipeople/221475837525 |
| Cass/OB 규모 anchor | Cass 2023 매출 1.52조 원, OB 2023 revenue 1.55조 원. OB는 Hoegaarden, Budweiser bottle, Stella Artois draft 등 AB InBev 포트폴리오 일부도 국내에서 양조/병입. | Cass가 OB 생산 capacity의 핵심 부하라는 근거. OB capacity는 Cass만이 아니라 타 브랜드도 공유. | USDA/FAS South Korea Beer Market Report KS2024-0035, Table 3/4. 로컬 파일: `sources/USDA_FAS_South_Korea_Beer_Market_Report_KS2024-0035.txt` |
| 한국 대형 맥주 제조 면허 최소 설비 | regular brewery license는 최소 발효탱크 250,000 L, holding tank 500,000 L capacity 필요. | 최소 법정 설비 수준도 발효/holding tank capacity로 정의됨. 즉 탱크 capacity가 맥주공장 scale의 핵심 지표. | USDA/FAS KS2024-0035, p.8 텍스트 |
| OB/Cass 수요 proxy | 2024 국내 맥주 출고량 1,637천 kL. 2024H1 OB 제조사 가정시장 점유율 55.3% → OB 전체 규모 proxy 약 905,377 kL/year. Cass Fresh 44.0% → 약 720,372 kL/year. | 공정 capacity 산식의 annual throughput anchor. 실제 출고량은 아니며 off-trade 점유율을 전체 출고량에 곱한 proxy. | 로컬 `data/cass_ob_key_observations.csv`, `cass_demand_data_summary.md` |
| 포장 line 벤치마크 | Krones can line의 can inspector는 33 cans/s 수준을 처리. Krones Modulfill HES glass bottle filler는 최대 78,000 containers/hour. | 포장 공정은 단일 고속 라인만 있어도 수십~100 kL/hour급. 발효 14일 대비 병목 가능성이 낮다는 근거. | Krones can filling page, https://www.krones.com/en/products/bottling-lines-for-cans.php ; Krones Modulfill HES, https://www.krones.com/en/products/machines/modulfill-hes-beer.php |
| 여과 공정 개선 벤치마크 | AB InBev Newark brewery K-filter ML 사례: filter run length 40~50% 증가, barrelage per run 60% 증가, 50개 이상 변수 사용. | 여과는 bottleneck 뒤 손실/지연을 줄이는 AI 개선 대상. 그러나 전체 throughput 제약은 여전히 발효 탱크 점유가 중심. | Google Cloud AB InBev/Pluto7 case, https://cloud.google.com/customers/abinbev-pluto7 |

---

## 3. Capacity 산식

### 3.1 연간 생산량 anchor

보고서에서 가장 방어 가능한 anchor는 “OB 전체 수요/생산 규모 proxy”다.

```text
OB annual throughput proxy
= 2024 국내 맥주 출고량 × 2024H1 OB 제조사 가정시장 판매량 점유율
= 1,637,210 kL/year × 55.3%
≈ 905,377 kL/year
≈ 2,480 kL/day
```

주의: 이 값은 실제 OB 총 생산량이 아니라, 전체 출고량과 가정시장 점유율을 결합한 **capacity sanity-check용 proxy**다. 수출, 수입/위탁, on-trade/off-trade 차이를 무시한다.

### 3.2 발효 tank capacity 역산

발효 공정은 tank가 batch를 14일 동안 점유한다고 보고, 필요한 total working volume을 계산한다.

```text
필요 발효 working volume
= annual throughput × fermentation residence time / 365 / utilization
= 905,377 kL/year × 14 days / 365 / 0.85
≈ 40,855 kL
```

탱크 크기별 필요한 탱크 수:

| 가정 | 필요 발효 working volume | 탱크 1기 300 kL | 탱크 1기 500 kL |
|---|---:|---:|---:|
| OB 전체 proxy 905,377 kL/year, 14일, 85% util. | 40,855 kL | 약 136기 | 약 82기 |
| Cass Fresh proxy 720,372 kL/year, 14일, 85% util. | 32,512 kL | 약 108기 | 약 65기 |

해석: OB 전체를 설명하려면 발효탱크가 “20기” 수준이라는 기존 모델은 작다. 기존 20기는 다음 둘 중 하나로 해석해야 한다.

- **정규화 모델:** 한 tank가 아니라 “standard batch-equivalent capacity unit”으로 두고 병목 구조를 설명한다.
- **단일 라인/부분 공정 모델:** OB 전체 3개 공장이 아니라 특정 Cass-family 라인의 일부 capacity를 보는 모델이다.

만약 20개 탱크만으로 OB 전체 proxy 905,377 kL/year를 처리한다고 가정하면, 1기당 working volume이 약 2,043 kL가 되어야 한다. 이는 일반적인 300~500 kL급 가정과 맞지 않으므로, 보고서에서 “20기 실측”처럼 쓰면 공격받기 쉽다.

### 3.3 숙성/holding tank capacity 역산

숙성/holding은 3일 체류, 75% utilization으로 보수 계산하면:

```text
필요 maturation/holding working volume
= 905,377 × 3 / 365 / 0.75
≈ 9,922 kL
```

| 가정 | 필요 holding working volume | 탱크 1기 300 kL | 탱크 1기 500 kL |
|---|---:|---:|---:|
| OB 전체 proxy 905,377 kL/year, 3일, 75% util. | 9,922 kL | 약 33기 | 약 20기 |

USDA/FAS가 regular brewery license의 최소 holding tank capacity를 500,000 L로 언급한 것도, 맥주공장에서는 fermentation/holding tank가 capacity 정의의 핵심이라는 점을 뒷받침한다.

---

## 4. 공정별 capacity 벤치마크 표 — 보고서용 권장 버전

아래 표는 OB 실측값이 아니라 **OB 규모 proxy 905,377 kL/year를 처리할 수 있도록 보정한 공정별 engineering capacity model**이다. 발표/보고서에서는 “public-data anchored estimate”로 표시하는 것을 권장한다.

| Stage | Flow/residence time | Capacity 산식/범위 | 권장 capacity 표현 | Utilization 해석 | 근거/메모 |
|---|---:|---:|---:|---:|---|
| Milling/Grain handling | 1~2 h | brewhouse batch 투입을 따라가는 전처리. 하루 여러 batch 가능 | `> 2,480 kL/day` 처리 가능하도록 설계되는 upstream slack stage | 낮음/중간 | 대형공장은 brewhouse·전처리 설비가 발효탱크 투입 속도에 맞춰 batch로 운전됨. 병목은 아님. |
| Mashing/Lautering | 3~5 h | 1일 복수 brew 가능. 발효 투입 필요량 2,480 kL/day 이상 | `3,000~6,000 kL/day`급 line/복수 line 가정 | 낮음/중간 | 기존 M2의 mashing 4h, upstream <1 day 논리 유지 가능. |
| Boiling/Hopping/Whirlpool | 2~3 h | kettle 회전으로 1일 복수 batch | `3,000~6,000 kL/day`급 | 낮음 | 발효보다 active processing time이 짧아 보통 병목 아님. |
| Cooling/Wort transfer | ~1 h | brewhouse batch discharge를 따라감 | `> brewhouse rate` | 낮음 | 발효탱크 투입 전 단계. |
| **Fermentation** | **~14 days** | `N_tanks × tank_kL / 14 days` | OB 전체 proxy 기준 필요 working volume **약 40,855 kL**; 300~500 kL tank 기준 **82~136기** | **높음, primary bottleneck** | 장기 biological residence time 때문에 overtime으로 회복 불가. 기존 M2/M3의 bottleneck 논리 유지. |
| Maturation/Holding | ~3 days | `holding volume / 3 days` | 필요 working volume **약 9,922 kL**; 300~500 kL tank 기준 **20~33기** | 중간, secondary constraint | 발효 뒤 품질 안정화/holding. 발효보다 짧지만 tank capacity 필요. |
| Final filtration | hours/run | filter run length와 CIP 주기에 의존 | bottleneck 뒤 손실/지연 관리 stage | 낮음~중간 | AB InBev K-filter ML 사례에서 run length +40~50%, barrelage/run +60% 개선. |
| De-alcoholization, Cass 0.0 only | 추가 4~8 h 또는 batch 처리 | Cass 0.0 volume share에만 적용 | SKU-specific constraint | Cass 0.0 성장 시 상승 | 전체 Cass family bottleneck은 발효. 다만 0.0 비중이 커지면 별도 병목 후보. |
| Packaging — cans | line speed 기반 | Krones can inspector 33 cans/s ≈ 118,800 cans/h. 500 mL 기준 약 59 kL/h, 20h/day면 1,180 kL/day/line | 복수 line이면 발효보다 훨씬 큰 순간 처리능력 | 일반적으로 병목 아님 | 포장은 high-speed, 단기 buffer로 흡수 가능. |
| Packaging — bottles | 최대 78,000 containers/h | 500 mL 기준 39 kL/h, 20h/day면 780 kL/day/line | 복수 line 필요 가능하나 active bottleneck은 아님 | 낮음~중간 | Krones Modulfill HES 최대 78,000 containers/h. |

---

## 5. 기존 M2/M3 문서에 넣으면 좋은 보정 문구

기존 문서에는 `20 tanks`, `1.20 batches/day`, `84% utilization`이 들어가 있다. 이 숫자를 유지하려면 다음처럼 설명을 바꾸는 것이 안전하다.

> OB맥주의 공장별 실제 탱크 수와 라인별 생산능력은 공개되어 있지 않다. 따라서 본 분석의 “20 fermentation tanks”는 OB 전체 설비의 실측치가 아니라, Cass-family 공유 발효 capacity를 설명하기 위한 normalized batch-equivalent model이다. 공개시장 자료로 OB 전체 생산규모를 sanity check하면 2024년 기준 약 90만 kL/year 수준의 throughput이 필요하며, 14일 발효·85% utilization·300~500 kL급 탱크를 가정할 경우 총 발효 working volume은 약 40,855 kL, 즉 82~136기의 탱크-equivalent가 필요하다. 따라서 최종 보고서에서는 절대 탱크 수보다 `capacity = tank working volume / residence time`이라는 병목 산식과 발효/숙성의 장기 체류시간이 전체 throughput을 제한한다는 구조적 결론에 초점을 둔다.

---

## 6. 발표용 한 문단 요약

공개자료상 OB맥주의 이천·청주·광주 3개 공장은 확인되지만, 공정별 실제 capacity는 공개되지 않는다. 그래서 본 프로젝트는 2024년 국내 맥주 출고량과 OB 가정시장 점유율을 이용해 OB 전체 처리량을 약 90.5만 kL/year로 anchor하고, 맥주 양조 공정의 tank residence-time 산식으로 capacity를 역산했다. 그 결과 14일 발효·85% 가동률 기준으로 약 40,855 kL의 발효 working volume, 즉 300~500 kL 탱크 약 82~136기 규모가 필요하다. 반면 포장 설비는 Krones 기준 병/캔 라인이 시간당 수만~10만 개 이상 처리 가능하므로 단기 처리속도는 높다. 따라서 Cass-family 공급망의 구조적 병목은 포장이나 전처리 설비보다, 14일 이상 제품을 묶어두는 발효/숙성 탱크 capacity라고 보는 것이 가장 타당하다.

---

## 7. 사용 시 caveat

- 이 문서의 수치는 **OB 내부 실측 capacity가 아니다.** 공개자료 기반의 size check 및 engineering estimate다.
- `OB 가정시장 점유율 × 전체 국내 출고량`은 생산량 proxy일 뿐이다. 수출, 수입, 위탁생산, on-trade 채널 차이를 반영하지 못한다.
- 그래도 “발효가 병목”이라는 정성적 결론은 강하다. 왜냐하면 capacity 산식 자체가 tank volume과 residence time에 의해 결정되고, 14일 내외의 biological residence time은 overtime이나 라인 속도 증가로 단기 회복이 어렵기 때문이다.

---

## 8. 추가 보강: 유사 대형공장 생산량 기준 normalization

사용자가 제공한 ChatGPT 공유 조사 결과를 브라우저로 확인했고, 그중 원문에서 숫자가 명확히 확인되는 자료는 다음 두 개가 가장 강하다.

### 8.1 SAB Alrode를 OB/Cass 규모로 scaling하는 방식

SAB Alrode Brewery는 대형 라거 생산공장으로, SASSDA 자료가 공정별 capacity를 매우 구체적으로 제시한다.

| 항목 | SAB Alrode 공개 수치 | 출처 |
|---|---:|---|
| 연간 생산능력 | 8.8 million hL/year | SASSDA |
| 주간 brewing capacity | 176,000 hL/week | SASSDA |
| 주간 packaging capacity | 205,000 hL/week | SASSDA |
| Brewhouse | 600 hL brewlength × 2, 1,500 hL brewlength × 1 | SASSDA |
| Fermentation vessels | 96 vessels × 3,000 hL | SASSDA |
| Maturation vessels | 60 vessels × 3,000 hL | SASSDA |
| Bright beer tanks | 26 tanks | SASSDA |
| Packaging lines | 5 lines | SASSDA |
| Reported operating level | 87% of capacity | SASSDA |

OB proxy는 앞 절에서 계산한 **905,377 kL/year = 9,053,770 hL/year**를 사용한다. Alrode 8,800,000 hL/year 대비 scale factor는 다음과 같다.

```text
Scale factor = OB proxy annual hL / SAB Alrode annual hL
             = 9,053,770 / 8,800,000
             ≈ 1.029
```

따라서 “OB가 Alrode와 유사한 대형 라거 공장 구조로 같은 연간 생산량을 처리한다면” 필요한 공정별 capacity는 다음처럼 normalization할 수 있다.

| 공정/설비 | SAB Alrode 원수치 | OB proxy normalized estimate | 해석 |
|---|---:|---:|---|
| Annual capacity | 8.8 million hL/year | 9.05 million hL/year | OB proxy가 Alrode보다 약 2.9% 큼 |
| Weekly brewing capacity | 176,000 hL/week | 약 181,075 hL/week | OB proxy의 peak/nominal brewing capacity 추정 |
| Weekly packaging capacity | 205,000 hL/week | 약 210,912 hL/week | 포장이 brewing보다 약 16.5% 여유 있는 구조 |
| Fermentation vessels | 96 × 3,000 hL | 약 99 × 3,000 hL-equivalent | 발효 설비 규모 추정 |
| Maturation vessels | 60 × 3,000 hL | 약 62 × 3,000 hL-equivalent | 숙성 설비 규모 추정 |
| Brewhouse | 600 hL×2 + 1,500 hL×1 | 유사하게 600 hL급 복수 + 1,500 hL급 대형 kettle/line 조합 | batch active processing 설비 |
| Packaging lines | 5 lines | 약 5 lines | OB proxy와 Alrode 규모가 거의 같으므로 line 수 scale도 유사 |

이 normalization은 보고서에서 “공정별 capa를 임의 설정하지 않고, 공개 대형 라거 공장의 연간 생산능력에 맞춰 scale했다”고 설명하기 좋다.

### 8.2 Alrode 자료에서 체류시간 검증

Alrode의 fermentation + maturation tank 총량과 주간 brewing capacity를 이용하면, cold-block 전체 평균 체류시간을 역산할 수 있다.

```text
Fermentation tank volume = 96 × 3,000 hL = 288,000 hL
Maturation tank volume   = 60 × 3,000 hL = 180,000 hL
Total cold-block volume  = 468,000 hL

Daily brewing capacity   = 176,000 / 7 ≈ 25,143 hL/day

Fermentation occupancy   = 288,000 / 25,143 ≈ 11.45 days
Maturation occupancy     = 180,000 / 25,143 ≈ 7.16 days
Total cold-block time    = 468,000 / 25,143 ≈ 18.61 days
```

SASSDA가 Alrode가 87% of capacity로 운영된다고도 제시하므로, 실제 운영 부하 기준으로 보면:

```text
Operating daily throughput = 176,000 × 0.87 / 7 ≈ 21,874 hL/day
Fermentation occupancy     = 288,000 / 21,874 ≈ 13.17 days
Maturation occupancy       = 180,000 / 21,874 ≈ 8.23 days
Total cold-block time      = 468,000 / 21,874 ≈ 21.39 days
```

이 결과는 기존 팀 모델의 **발효 14일 + 숙성 3일 = 17일**과 방향이 잘 맞는다. 다만 Alrode 기준으로는 maturation/conditioning 쪽이 7~8일로 더 길게 잡힌다. 따라서 최종 보고서에서는 다음처럼 잡는 것이 더 방어력 있다.

| 항목 | 기존 값 | 공개 proxy 기반 권장값 |
|---|---:|---:|
| Fermentation | 14 days | 13~14 days 유지 가능 |
| Maturation/conditioning | 3 days | 3 days는 보수/단순화; sensitivity로 7~8 days 추가 권장 |
| Total cold-block residence | 17 days | base 17 days, sensitivity 21 days |

즉, 발표에서는 17일을 유지해도 되지만, 보고서/부록에는 “Alrode 공개자료 역산 시 18.6~21.4일이므로 본 모델의 17일은 다소 보수적인 단순화”라고 적으면 좋다.

### 8.3 AB InBev Leuven 자료로 탱크 크기 range 검증

GEA의 AB InBev Leuven cold block 사례는 OB와 같은 AB InBev 계열 대형 라거 공장이라는 점에서 탱크 크기 근거로 좋다.

원문 확인 수치:

| 항목 | Leuven/GEA 공개 수치 |
|---|---:|
| 신규 cold block 증설 효과 | capacity +30% |
| 신규 탱크 수 | 36 tanks |
| 증설 후 전체 탱크 수 | 116 tanks |
| 신규 탱크 구성 1 | 16 tanks × 4,700 hL |
| 신규 탱크 구성 2 | 20 tanks × 2,700 hL |
| 신규 cold block 총 탱크 용량 | 129,200 hL = 12,920 kL |
| 신규 centrifuge capacity | 600~700 hL/hour |
| loading/unloading bay capacity | 400 hL/hour |

계산:

```text
New cold block tank volume
= 16 × 4,700 + 20 × 2,700
= 75,200 + 54,000
= 129,200 hL
```

따라서 기존 문서에서 사용한 300~500 kL tank 가정은 Leuven의 2,700~4,700 hL, 즉 270~470 kL와 거의 일치한다. 최종 문서에서는 **3,000 hL base case, 2,700~4,700 hL sensitivity range**로 쓰는 것이 가장 안전하다.

### 8.4 공정별 capacity를 생산량 기준으로 normalize하는 최종 방식

최종 보고서에서는 특정 탱크 수를 OB 실측처럼 주장하지 말고, 다음 순서로 제시하는 것을 권장한다.

1. 공개자료로 OB/Cass 생산량 proxy를 정한다.
   - 예: OB proxy = 9.05 million hL/year.
2. 유사 대형 라거 공장인 SAB Alrode의 공정별 capacity를 기준으로 scale factor를 계산한다.
   - `scale = OB proxy annual hL / Alrode annual hL`.
3. 각 공정별 capacity를 `Alrode 공정 capacity × scale`로 normalize한다.
4. 병목 분석은 `demand / normalized capacity`로 한다.

수식:

```text
Normalized capacity_i = Benchmark capacity_i × (Target annual production / Benchmark annual production)

Utilization_i = Target load_i / Normalized capacity_i
```

여기서 `i`는 brewing, fermentation, maturation, filtration/centrifuge, packaging 등 각 공정을 의미한다.

### 8.5 최종 보고서용 문단

> Because OB Brewery’s internal process-level capacity data are not publicly disclosed, this study normalizes capacity from publicly documented large lager breweries rather than assigning arbitrary values. SAB Alrode Brewery is used as the main benchmark because its annual capacity, brewhouse capacity, fermentation vessels, maturation vessels, bright beer tanks, and packaging lines are all publicly reported. Alrode has an annual capacity of 8.8 million hL/year, 176,000 hL/week brewing capacity, 205,000 hL/week packaging capacity, 96 fermentation vessels and 60 maturation vessels, each with 3,000 hL capacity. Using OB’s public-data-based production proxy of 9.05 million hL/year, the scale factor is 9.05/8.8 = 1.029. Therefore, OB-equivalent capacity can be approximated by scaling Alrode’s process capacities by 1.029. This yields approximately 181,000 hL/week brewing capacity, 211,000 hL/week packaging capacity, 99 fermentation-vessel equivalents, and 62 maturation-vessel equivalents. AB InBev’s Leuven cold-block data further validates the tank-size assumption because its disclosed industrial tank range is 2,700–4,700 hL, consistent with the 3,000 hL base case used in this model.

### 8.6 한국어 발표용 요약

OB맥주의 공정별 실측 capacity는 공개되지 않기 때문에, 본 분석은 공개된 유사 대형 라거 공장인 SAB Alrode를 benchmark로 사용했다. Alrode는 연간 880만 hL 생산능력, 주간 176,000 hL brewing capacity, 주간 205,000 hL packaging capacity, 3,000 hL급 발효 vessel 96기와 숙성 vessel 60기를 보유한다. OB의 공개자료 기반 생산량 proxy는 약 905만 hL/year이므로 Alrode 대비 scale factor는 1.029이다. 따라서 Alrode 수치를 1.029배 정규화하면 OB-equivalent capacity는 주간 brewing 약 181,000 hL, packaging 약 211,000 hL, 발효 vessel 약 99기, 숙성 vessel 약 62기 수준으로 추정된다. 또한 AB InBev Leuven 공장의 공개 cold-block 자료에서 2,700~4,700 hL급 탱크가 확인되므로, 본 모델의 3,000 hL 탱크 base case는 임의값이 아니라 공개 대형공장 사례에 근거한 값이다.

---

## 9. Proposal Report 표 형태로 정리한 최종 normalized table

Proposal Report의 기존 `Stage / Flow time / Capacity / Resource / Load / Util. / Comment` 표와 같은 형태의 최종 표는 별도 파일로 저장했다.

- 파일: `proposal_report_capacity_table_normalized.md`
- 기준: SAB Alrode capacity를 OB proxy 9.05 million hL/year로 1.029배 scaling
- 표준 batch unit: 3,000 hL
- planning load: 7.5 standard batches/day
- 핵심 결과: fermentation ≈99 vessels, maturation ≈62 vessels, brewing ≈181,000 hL/week, packaging ≈211,000 hL/week

---

## 10. 병목 분석용 revised table 업데이트

사용자 지적에 따라, Alrode의 87% 전체 공장 operating level을 모든 공정에 동일 적용한 이전 표는 병목 분석에 부적절하다고 판단했다. `proposal_report_capacity_table_normalized.md`를 revised version으로 덮어썼다.

핵심 변경:
- 87%는 planning load 산정에만 사용.
- 공정별 capacity는 별도 공개 benchmark로 산정.
- Steinecker mash filter: up to 14 brews/day → mashing/lautering capacity 14 batches/day.
- GEA Leuven centrifuge: 600–700 hL/hour → 2 units 기준 final filtration 9.6–11.2 batches/day.
- SAB Alrode packaging: 205,000 hL/week, 5 lines → packaging 10 batches/day.
- Cold block은 normalized tank count와 residence time으로 산정.
- 결과: warm process 54–63%, packaging ~75%, filtration 67–78%, fermentation ~94%, maturation ~87%. 따라서 dominant bottleneck은 fermentation-centered cold block으로 설명 가능.
