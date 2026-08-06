# Multi-Agent Due Diligence Engine — DAX/MDAX

[![CI](https://github.com/aralati/de-due-diligence-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/<KULLANICI_ADIN>/de-due-diligence-engine/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

> 🚧 Aktif geliştirme aşamasında. Şu an **Modül 1: Pydantic Veri Sözleşmesi (Contract Layer)** tamamlandı.

Almanya'daki DAX 40 / MDAX şirketleri için otonom, çoklu-ajanlı (LangGraph tabanlı)
due diligence ve yatırım risk raporu üreten sistem.

## ⚠️ Yasal Uyarı (Disclaimer)

Bu proje **eğitim ve portföy amaçlı** geliştirilmiştir. Ürettiği raporlar, skorlar ve
"BUY/SELL/HOLD" önerileri **gerçek bir yatırım tavsiyesi değildir** ve finansal karar
alma sürecinde tek başına kullanılmamalıdır. Sistem, halka açık veri kaynaklarını ve
büyük dil modellerini kullanır; çıktılar hatalı, eksik veya güncel olmayan bilgi
içerebilir. Yazılım "olduğu gibi" (AS IS), hiçbir garanti verilmeksizin sunulmaktadır
(bkz. [LICENSE](LICENSE)). Gerçek yatırım kararları için lisanslı bir finansal
danışmana başvurun.

## Mimari (planlanan)

```
              ┌─────────────────────┐
   ticker ──▶ │   LangGraph State    │
              └──────────┬───────────┘
                          │ fan-out (parallel)
        ┌─────────┬───────┴───────┬─────────┐
        ▼         ▼               ▼         ▼
     Macro     Financial       Sentiment  Risk/ESG
     Agent      Agent            Agent    /Compliance
        │         │               │         │
        └─────────┴───────┬───────┴─────────┘
                          │ fan-in
                          ▼
                    CIO Agent
                          │
                          ▼
              Otonom Yatırım & Risk Raporu (Markdown)
```

## Modül Durumu

| # | Modül | Durum |
|---|-------|-------|
| 1 | Pydantic Veri Sözleşmesi (`core/`) | ✅ Tamamlandı |
| 2 | Veri Konnektörleri | ⏳ Sırada |
| 3 | RAG Altyapısı (Qdrant) | ⏳ |
| 4 | Bireysel Ajanlar | ⏳ |
| 5 | LangGraph Orkestrasyonu | ⏳ |
| 6 | Celery + Redis | ⏳ |
| 7 | FastAPI Katmanı | ⏳ |
| 8 | Test & Gözlemlenebilirlik | ⏳ |
| 9 | Deployment & Sunum | ⏳ |

## Modül 1 — Contract Layer

`core/enums.py` — Tüm ajanların paylaştığı ortak enum tipleri (Recommendation, RiskLevel,
SentimentLabel, ESGCategory, vb.)

`core/schemas.py` — Her ajanın çıktı şeması:
- `MacroSignal` — Macroeconomic Agent
- `FinancialMetrics` (+ `MonteCarloResult`) — Financial Statement Agent
- `SentimentScore` — Market Sentiment Agent
- `ComplianceFlag` (+ `ESGSubScore`) — Risk/Compliance/ESG Agent
- `InvestmentReport` (+ `AgentConflict`) — CIO Agent'ın nihai çıktısı

`core/state.py` — LangGraph `StateGraph` için ortak `AgentState` (TypedDict)

Tasarım kararları:
- Tüm modeller `frozen=True` — bir ajan başka bir ajanın çıktısını sessizce mutasyona
  uğratamaz; her state güncellemesi açıkça yeni bir obje olmalı.
- `strict=True` — LLM tool-call çıktılarında tip zorlama (coercion) risklerini engeller.
- Her ajan çıktısı zorunlu bir `AgentMetadata` taşır (confidence, sources, timestamp) —
  CIO Agent'ın çelişki çözümü bu metadata'ya dayanır.

### Test

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Kurulum

```bash
docker compose up -d   # Redis + Qdrant (Modül 6-7'de eklenecek)
pip install -e ".[dev]"
```
