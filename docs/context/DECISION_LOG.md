# SecureOps Local — Decision Log

Bu dosya kısa mimari karar kaydıdır. Ayrıntılı ADR’ler `docs/adr/` altında daha sonra oluşturulabilir.

Durumlar: `Proposed`, `Accepted`, `Superseded`, `Rejected`.

## D-001 — Ürün bir SIEM/IDS değildir

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Ürün ilk inceleme ve doküman destekli karar destek prototipidir.
- Gerekçe: Dört haftalık kapsam ve yanlış güvenlik iddialarını önleme.
- Sonuç: Real-time monitoring ve otomatik engelleme yok.

## D-002 — Deterministik parser, LLM’den önce gelir

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Sayım ve temel gerçekler Python kurallarıyla çıkarılır.
- Gerekçe: LLM aritmetiği ve log ayrıştırması güvenilir truth source değildir.
- Sonuç: `observed_findings` parser truth ile sınırlandırılır.

## D-003 — Model eğitimi/fine-tuning yok

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Hazır local instruct modeller ve RAG kullanılacak.
- Gerekçe: RAG training değildir; eğitim süre/donanım açısından gereksiz scope expansion.

## D-004 — Multi-runtime provider mimarisi

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Foundry Local ve Ollama eşit provider’lardır.
- Gerekçe: Güçlü portföy çıktısı, vendor lock-in azaltma ve objektif deployment karşılaştırması.
- Sonuç: Ortak `LocalLLMProvider`; default profil benchmark öncesi seçilmez.

## D-005 — Benchmark birimi deployment profile’dır

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Model+runtime+quantization+execution provider birlikte raporlanır.
- Gerekçe: Farklı runtime’lar saf model karşılaştırması değildir.

## D-006 — Foundry ve Ollama Windows host üzerinde

- Durum: Accepted, spike doğrulamasına tabi
- Tarih: 2026-08-03
- Karar: Donanım entegrasyonu için runtime’lar hostta, FastAPI tercihen Docker’da.
- Fallback: FastAPI native Windows.

## D-007 — Modüler monolith

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Tek FastAPI application/deployment unit.
- Gerekçe: Mikroservis/message broker dört haftalık proje için gereksiz.

## D-008 — Background job, haricî broker yok

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Sınırlı in-process queue + SQLite state.
- Sonuç: Restart sırasında running jobs interrupted olur.

## D-009 — SQLite + SQLAlchemy 2 + Alembic

- Durum: Accepted
- Tarih: 2026-08-03
- Gerekçe: İlişkili tablolar ve tekrar üretilebilir schema migration.

## D-010 — TF-IDF MVP baseline

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: İlk retrieval TF-IDF + cosine.
- Gerekçe: Küçük koleksiyon, offline taşınabilirlik, açıklanabilirlik.
- Sonuç: Embedding opsiyonel deney.

## D-011 — Haricî vector database yok

- Durum: Accepted
- Tarih: 2026-08-03
- Gerekçe: 5–10 doküman için gereksiz operasyon ve paketleme maliyeti.

## D-012 — Raw log kalıcı saklanmaz

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Varsayılan ve MVP davranışı raw retention yok.
- Sonuç: Hash/metadata ve maskelenmiş sınırlı evidence tutulabilir.

## D-013 — Strict Pydantic validation ve tek repair

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Model çıktısı strict doğrulanır; en fazla bir repair denemesi.
- Sonuç: İkinci hata `invalid_model_output`.

## D-014 — Swagger UI MVP arayüzüdür

- Durum: Accepted
- Tarih: 2026-08-03
- Gerekçe: Ayrı frontend çekirdek değere katkı sağlamadan süre tüketir.

## D-015 — “Air-gapped-ready” terminolojisi

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Ürün gerçek air-gap iddiasını hazırlık sürecinden ayırır.
- Gerekçe: İlk model/runtime/dependency indirmesi internet gerektirir.

## D-016 — İlk Ollama model adayı

- Durum: Proposed, spike bekliyor
- Tarih: 2026-08-03
- Aday: Qwen3 8B 4-bit
- Fallback: Qwen3 4B
- Not: Gerçek RAM, latency, JSON ve Türkçe/İngilizce güvenlik raporu kalitesi ölçülmeden Accepted/default olmaz.

## D-017 — Python sürümü

- Durum: Proposed
- Tarih: 2026-08-03
- Tercih: Python 3.12
- Mevcut: Python 3.13.3
- Karar koşulu: Foundry/Ollama/FastAPI dependency spike.

## D-018 — Güvenlik dokümanı lisans audit

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Redistribution belirsizse doküman repo dışı, link/metadata içi.

## D-019 — Kesin saldırı dili yok

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Model olası yorum ve limitation üretir.
- Gerekçe: SSH log örüntüsü tek başına saldırı/compromise kanıtı değildir.

## D-020 — Projenin değerlendirme çıktısı kısa Türkçe video

- Durum: Accepted
- Tarih: 2026-08-03
- Karar: Mimari, öğrenme ve çalışan ürün 2–5 dakikada anlatılacak.
- Sonuç: Canlı demo ve README video anlatısını desteklemelidir; akademik sunum hazırlanmaz.

## Yeni karar ekleme şablonu

```text
## D-XXX — Başlık

- Durum:
- Tarih:
- Karar:
- Gerekçe:
- Alternatifler:
- Sonuç/Fallback:
```

