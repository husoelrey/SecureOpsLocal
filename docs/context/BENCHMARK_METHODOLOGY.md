# SecureOps Local — Benchmark Methodology

## 1. Amaç

Benchmark ana ürün değildir. Amaç, bu cihazda ve bu güvenlik kullanımında hangi yerel deployment profilinin kalite, hız ve bellek bakımından en iyi dengeyi sunduğunu ölçmektir.

## 2. Doğru karşılaştırma birimi

Karşılaştırma birimi yalnızca model adı değildir.

**Deployment profile**:

- Model ailesi ve exact model ID/digest
- Parametre sınıfı
- Quantization
- Runtime ve sürümü
- Execution provider/backend
- Prompt template sürümü
- Generation ayarları
- Context uzunluğu

Örnek profiller:

- `foundry-<resolved-model>-<provider>`
- `ollama-qwen3-8b-q4-<backend>`

Bu nedenle sonuç:

- “Qwen her koşulda Phi’dan iyidir” demez.
- “Bu cihazda bu iki deployment profilinden X, tanımlı vakalarda şu trade-off’u verdi” der.

## 3. MVP profilleri

En az iki profil:

1. Foundry Local üzerinde gerçekten çalışan küçük/orta chat modeli
2. Ollama üzerinde Qwen3 8B 4-bit veya donanım gerekirse Qwen3 4B

Üçüncü profil ancak ana iki profil ve scoring tamamlandıysa.

## 4. Benchmark case şeması

Her vaka:

- `case_id`
- `title`
- `log_type`
- `input_file`
- `input_sha256`
- `expected_findings`
- `forbidden_or_unsupported_claims`
- `expected_recommendation_categories`
- `expected_source_topics`
- `acceptable_risk_levels`
- `notes`

Vakalar sentetik ve version-controlled olur.

## 5. İlk 10–20 vaka

Zorunlu minimum:

1. Normal tek başarılı giriş
2. Tek başarısız giriş
3. Aynı IP’den tekrarlanan başarısız giriş
4. Bir IP’den çok kullanıcı denemesi
5. Root hesabına denemeler
6. Invalid user denemeleri
7. Çok başarısızlıktan sonra başarılı giriş
8. Birden fazla kaynak IP
9. IPv6 kaynağı
10. SSH olayı içermeyen/bozuk log

Genişleme:

- Public-key normal giriş
- Low-and-slow örüntü
- Timestamp/year belirsizliği
- Duplicate satırlar
- Prompt injection satırı
- Benign admin automation benzeri örüntü
- Başarılı giriş olmadan yüksek hacim
- Farklı host/PID formatları

## 6. Sabit input paketi

Her profil aynı:

- Raw test fixture
- Parser version/result
- Retrieved top-k chunk IDs ve content
- Knowledge snapshot hash
- System prompt version
- Output schema version
- Temperature/top_p
- Seed, desteklendiği ölçüde
- Max output token
- Timeout

Retrieval her model için tekrar çalıştırılıp farklı sonuç üretmez. Bir kez üretilen evidence pack iki profile verilir.

## 7. Performans metrikleri

### Cold load time

Model cache’teyken fakat memory’de değilken load başlangıcından hazır duruma kadar.

İlk indirme süresi ayrı onboarding metriğidir; inference performansına karıştırılmaz.

### Time to first token

Request gönderiminden ilk içerik token/chunk’ına kadar. Streaming gerektirir.

### Total response time

Request başlangıcından response completion’a kadar.

### Tokens per second

Tercih edilen formül:

`completion_tokens / (completion_end - first_token_time)`

Provider token sayısı vermiyorsa kullanılan tokenizer/metot kaydedilir; tahminse `estimated=true`.

### RAM

- Ortalama process RSS
- Peak process RSS
- Gerekirse system used-memory delta
- Ölçülen process kapsamı açıkça yazılır

Host runtime ve Docker app ayrı process olduğundan yalnızca FastAPI RAM’i model RAM’i diye sunma.

### CPU/GPU

- Güvenilir ve tekrarlanabilir sayaç varsa
- Backend/device açıkça kaydedilir
- Intel GPU telemetry belirsizse metrik boş bırakılır

TOPS doğrudan uygulama metriği değildir.

## 8. Deterministik kalite metrikleri

### Expected finding recall

Beklenen yapılandırılmış finding’lerin rapor/observed findings içinde doğru değerle bulunma oranı.

### Unsupported claim count

Observed findings içinde parser truth ile desteklenmeyen yapılandırılmış iddia sayısı.

Serbest interpretation metni için tam otomatik entailment iddiası yapılmaz; belirli forbidden claim pattern’leri sayılır.

### Schema compliance

- İlk denemede geçerli
- Bir repair sonrası geçerli
- Geçersiz

### Citation validity

- Citation ID retrieved context içinde mi?
- DB’de gerçek mi?

### Citation coverage

- Yorum ve önerilerin kaçında citation var?

### Recommendation completeness

Vakadaki beklenen savunma kategorilerinin karşılanma oranı.

### Risk consistency

Risk seviyesi acceptable set içinde mi?

### Terminology safety

Kesin saldırı iddiası veya otomatik remediation dili var mı?

## 9. Manuel değerlendirme

Manuel rubric, 0–2:

- Groundedness
- Citation’ın iddiayı gerçekten desteklemesi
- Açıklamanın temkinli olması
- Önerinin uygulanabilirliği
- Raporun okunabilirliği

Puan açıklamaları:

- 0: başarısız/yanlış
- 1: kısmen doğru veya eksik
- 2: açıkça yeterli

Manuel değerlendiren kişi ve tarih kaydedilir. Sadece başka bir LLM judge’a güvenilmez.

## 10. Tekrar ve tutarlılık

- Bütün vakalarda en az bir run.
- Seçilen 3–5 temsili vakada üç tekrar.
- Seed destekleniyorsa sabitlenir.
- Aynı risk kategorisi oranı.
- Finding set Jaccard veya exact match.
- Schema success varyansı.

## 11. Cold ve warm senaryolar

Cold benchmark:

- Model memory’de değil
- Cache hazır
- Load time dahil/ayrı rapor

Warm benchmark:

- Model loaded
- Aynı koşullarda arka arkaya inference
- Isınma run’ı sonuçlara dahil edilip edilmediği açıklanır

İki profil benchmark sırasında aynı anda memory’de tutulmaz; 16 GB RAM nedeniyle sırayla çalıştırılır.

## 12. Thinking/reasoning kontrolü

Qwen gibi thinking mode destekleyen modellerde:

- Ana structured report benchmark’ında thinking ayarı açıkça sabitlenir.
- Foundry profiliyle karşılaştırmayı bozacak gizli token/uzun reasoning farkı kaydedilir.
- Gerekirse `thinking off` ana profil, `thinking on` opsiyonel deney olur.

## 13. Benchmark sonucu tablosu

Her profil için:

- Profil metadata
- Başarılı vaka sayısı
- First-attempt schema rate
- Finding recall ortalama
- Unsupported claim toplam/ortalama
- Citation validity/coverage
- Recommendation completeness
- Risk consistency
- Median/P95 total latency
- Median TTFT
- Median token/s
- Peak RAM
- Manuel rubric ortalama

Tek birleşik “magic score” ana sonuç yapılmaz. İstenirse açık ağırlıklı yardımcı skor verilir, fakat ham metrikler görünür kalır.

## 14. Opsiyonel deneyler

Ana benchmark bittikten sonra:

- RAG açık/kapalı
- TF-IDF/embedding retrieval
- Qwen 4B/8B
- Foundry alternatif model
- Thinking on/off
- Farklı context top-k

Bu deneyler ana iki profil karşılaştırmasını gölgelememelidir.

## 15. Reproducibility manifesti

- App commit SHA
- OS/build
- CPU/RAM/GPU ve driver
- Runtime sürümleri
- Model ID/digest/quantization
- Execution backend
- Prompt/schema version
- Knowledge snapshot hash
- Case dataset version
- Generation config
- Benchmark timestamp
- İnternet açık/kapalı durumu

## 16. Başarı kriteri

Benchmark başarılıdır eğer:

- En az 10 vaka iki profilde tamamlanmıştır.
- Aynı evidence paketleri kullanılmıştır.
- Deterministic scoring testleri geçmektedir.
- Performans formülleri açıktır.
- Başarısız/timeout vakaları gizlenmemiştir.
- Sonuçlar profil trade-off’u olarak yorumlanmıştır.

