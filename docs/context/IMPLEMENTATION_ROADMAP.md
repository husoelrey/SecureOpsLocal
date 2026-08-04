# SecureOps Local — Implementation Roadmap

## 1. Yürütme ilkesi

Her görev küçük, tek amaçlı ve test edilebilir olmalıdır. Bir phase gate tamamlanmadan sonraki faza geçilmez. Her günün sonunda çalışan veya açıkça teşhis edilmiş bir durum bırakılır.

## 2. Phase gate’ler

### G0 — Repository ve bağlam

Başarı:

- Git repository hazır
- `AGENTS.md` ve bağlam belgeleri tutarlı
- Mevcut ortam envanteri kayıtlı

### G1 — Runtime smoke testleri

Başarı:

- Foundry Local kurulu
- Bir Foundry modeli terminal/native spike üzerinden yanıt veriyor
- Ollama kurulu
- Bir Ollama modeli yanıt veriyor
- Model/runtime/provider metadata kaydedilmiş
- İnternetin ilk indirmede nerede gerektiği biliniyor

### G2 — Deterministik parser

Başarı:

- SSH parser interface
- Ana SSH olay formatları
- Aggregate statistics
- Edge-case testleri
- LLM bağımlılığı olmadan doğru JSON

### G3 — Bilgi tabanı ve retrieval

Başarı:

- Lisans manifesti
- PDF/MD/TXT ingestion
- Chunk metadata
- TF-IDF top-k retrieval
- Beklenen konuyu bulan testler

### G4 — Uçtan uca tek profil

Başarı:

- Güvenli upload
- Job akışı
- Provider çağrısı
- Prompt/validation
- Citation’lı incident report
- SQLite persistence

### G5 — İki provider benchmark

Başarı:

- Aynı evidence paketi
- En az 10 etiketli vaka
- Foundry + Ollama profile run
- Deterministic scores
- Timing/token/RAM raporu

### G6 — Offline ve teslim

Başarı:

- Model cache sonrası ağ kapalı demo
- Docker veya native fallback
- CI
- README
- Video senaryosu
- MVP acceptance checklist

## 3. Dört haftalık plan

## Hafta 1 — Risk kapatma ve temel

### Gün 1: Ortam teşhisi

Amaç:

- Python, Docker, winget/App Installer, WSL ve sürücü durumunu doğrulamak.

Dosyalar:

- `docs/context/CURRENT_STATUS.md`
- Gerekirse `docs/adr/0001-development-environment.md`

Komutlar:

- `git status --short --branch`
- `py -0p`
- `python --version`
- `docker version`
- `docker compose version`
- `wsl --version`
- `wsl --list --verbose`

Başarı:

- Her aracın gerçek durumu ve eksikleri kaydedilmiş.

Hata/fallback:

- Araç yoksa ana uygulama yazılmaz; resmî kurulum yolu doğrulanır.

### Gün 2: Foundry CLI ve katalog spike

Amaç:

- Foundry kurmak, katalog ve provider’ları görmek.

Dosyalar:

- `docs/spikes/foundry-environment.md`
- `CURRENT_STATUS.md`

Doğrulama:

- `foundry --version`
- `foundry service status`
- `foundry model list`
- Provider/device filtreleri

Başarı:

- En az bir küçük chat model adayı, dosya boyutu ve provider bilgisi.

Hata/fallback:

- Service restart ve resmî troubleshooting.
- CLI çalışıp SDK uymazsa ayrı kaydet.

### Gün 3: Foundry native inference spike

Amaç:

- Windows SDK ile model lifecycle ve streaming’i doğrulamak.

Dosyalar:

- `spikes/foundry_native/`
- `docs/spikes/foundry-native-results.md`

Başarı:

- Model indirilir/yüklenir, kısa response alınır, provider ve süre kaydedilir.

Hata/fallback:

- Python 3.13 uymazsa Python 3.12 venv.
- WinML başarısızsa CPU/cross-platform kontrolü.

### Gün 4: Ollama ve model kapasite spike

Amaç:

- Ollama API ve Intel Arc/Vulkan/CPU davranışını doğrulamak.

Dosyalar:

- `docs/spikes/ollama-results.md`

Model sırası:

1. Küçük smoke-test modeli
2. Qwen3 8B 4-bit
3. Yetersizse Qwen3 4B

Başarı:

- `/v1/chat/completions` streaming response, model digest ve bellek/süre gözlemi.

Hata/fallback:

- Vulkan kararsızsa CPU.
- 8B yavaş/ağırsa 4B.

### Gün 5: Docker-host bridge ve ADR

Amaç:

- Container’dan iki host runtime’a erişimi kanıtlamak.

Dosyalar:

- `spikes/runtime_bridge/`
- `docs/adr/0002-runtime-deployment.md`

Başarı:

- Docker’dan iki runtime health/chat çağrısı veya native Windows fallback kararı.

Milestone:

- `v0.1-runtime-spikes` için commit-ready durum.

## Hafta 2 — Deterministik çekirdek

### Gün 6: Python proje bootstrap

Dosyalar:

- `pyproject.toml`
- Dependency input/lock dosyaları
- `src/secureops_local/`
- `tests/`
- `.gitignore`

Başarı:

- Empty app import, Ruff, mypy ve Pytest çalışır.

### Gün 7: Domain/Pydantic şemaları

Amaç:

- Parser, incident report, citation ve model metadata sözleşmeleri.

Başarı:

- Geçerli fixture kabul edilir; yanlış enum/extra alan reddedilir.

### Gün 8: Parser line normalization

Kapsam:

- Failed/accepted password
- Accepted publickey
- Invalid user
- IPv4/IPv6

Başarı:

- Fixture satırları beklenen normalized events’e dönüşür.

### Gün 9: Aggregation ve edge cases

Kapsam:

- Count, unique, top source, privileged attempt
- Time window
- Repeated attempts
- Failure then success
- Unknown year/timezone limitation

Başarı:

- Tamamen deterministic parser result.

### Gün 10: DB ve güvenli upload

Kapsam:

- SQLAlchemy/Alembic
- Upload stream limit
- Hash
- MIME/content
- Temp cleanup

Başarı:

- Migration çalışır; kötü dosya testleri geçer; raw log persist edilmez.

Milestone:

- `v0.2-deterministic-core` için commit-ready durum.

## Hafta 3 — Knowledge ve incident analysis

### Gün 11: Source manifest ve lisans audit

Başarı:

- En az 5 aday kaynak metadata’sı ve redistribution kararı.

### Gün 12: Ingestion ve chunking

Başarı:

- PDF/MD/TXT’den başlık/sayfa metadata’lı chunk’lar.

### Gün 13: TF-IDF retrieval

Başarı:

- Test sorgularında beklenen source topic top-k içinde.

### Gün 14: Provider contract ve adaptörler

Başarı:

- Fake provider ile unit test.
- Foundry ve Ollama normalize GenerationResult döndürür.

### Gün 15: Prompt, validation ve incident service

Başarı:

- Tek provider ile upload → parse → retrieve → generate → validate → persist.

Milestone:

- `v0.3-local-incident-analysis` için commit-ready durum.

## Hafta 4 — Benchmark, offline ve teslim

### Gün 16: Benchmark vaka seti

Başarı:

- En az 10 sentetik vaka, expected findings ve forbidden claims.

### Gün 17: Deterministic scoring

Başarı:

- Known outputs expected recall, unsupported claims, citation validity ve recommendation scores verir.

### Gün 18: Runtime metrics ve iki profil run

Başarı:

- Cold/warm, TTFT, total, token/s, RAM ve schema metrics kaydedilir.

### Gün 19: Docker/native packaging ve offline test

Başarı:

- Seçilen deployment ile internet kapalı örnek analiz.
- Offline manifest.

### Gün 20: CI, README ve video provası

Başarı:

- CI deterministic suite geçer.
- README sıfırdan kurulumu anlatır.
- 2–5 dakikalık video akışı prova edilir.

Milestone:

- `v1.0-mvp` için commit-ready durum.

## 4. Görev başına Definition of Done

- Sadece görev kapsamındaki dosyalar değişti.
- Happy path ve ilgili failure path test edildi.
- Test komutu ve sonucu kaydedildi.
- Yeni dependency gerekçelendirildi ve kilitlendi.
- Güvenlik/gizlilik etkisi değerlendirildi.
- Current status güncellendi.
- İlgili phase gate kanıtı oluştu.

## 5. Zaman sıkışırsa kapsam azaltma sırası

Önce ertelenecekler:

1. Embedding retrieval
2. Basit frontend
3. Üçüncü model
4. PDF rapor
5. Nmap/Nginx parser
6. Prometheus
7. Advanced GPU telemetry

Asla kesilmeyecek çekirdek:

- Güvenli upload
- Deterministik parser
- En az 5 kaynaklı TF-IDF RAG
- Foundry + Ollama provider
- Strict output validation
- En az 10 benchmark vakası
- Offline smoke test

## 6. Geri dönüş politikası

- Test başarısızken yeni faza geçme.
- Son başarılı commit’i tespit et.
- Kullanıcı değişikliklerini silme.
- Commit geri alınacaksa `git revert` tercih et.
- Preview SDK sorunu ürün kodunu kirletiyorsa adapter/fallback kullan.
- Başarısız spike sonucunu silme; ADR’da neden çalışmadığını kaydet.

