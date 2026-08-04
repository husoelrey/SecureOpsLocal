# SecureOps Local — Project Specification

## 1. Proje adı

**SecureOps Local: Air-Gapped-Ready Incident Response Assistant with Multi-Runtime Local LLM Evaluation**

Kısa ad: **SecureOps Local**

## 2. Arka plan

Proje, Microsoft Türkiye AI Innovators çevrimiçi staj programı bağlamında geliştirilmektedir. Programın örnek projesi, Microsoft Foundry Local kullanan bir aylık Local RAG asistanıdır:

- [Building Your First Local RAG Application with Foundry Local](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-your-first-local-rag-application-with-foundry-local/4501968)

SecureOps Local, örneği farklı PDF’lerle tekrar etmeyecektir. Genel amaçlı chatbot yerine gerçek güvenlik girdisi işler, deterministik parser kullanır, kaynaklı incident-review raporu üretir ve iki yerel inference runtime profilini karşılaştırır.

Program açısından Foundry Local kullanmak değerlidir fakat ürün Foundry’ye kilitlenmeyecektir. Ortaya güçlü ve açıklanabilir bir proje çıkarmak, tek vendor teknolojisine bağlı kalmaktan daha önemlidir.

## 3. Problem tanımı

SSH/authentication logları aşağıdaki hassas bilgileri içerebilir:

- İç veya dış IP adresleri
- Kullanıcı adları
- Sunucu isimleri
- Authentication yöntemi
- Servis ve sistem davranışı
- Olası olay zaman çizelgesi

Bu bilgilerin cloud LLM’e gönderilmesi gizlilik, uyumluluk veya kurum politikası açısından istenmeyebilir. Küçük ekipler ve junior analistler ise ham loglardan hızlı bir ilk inceleme çıkarmakta zorlanabilir.

SecureOps Local şu ihtiyacı karşılar:

> Ham güvenlik loglarını cihaz dışına çıkarmadan deterministik olarak özetleyen, güvenilir yerel dokümanlardan ilgili bölümleri bulan ve temkinli bir ilk inceleme raporu oluşturan yerel karar destek aracı.

## 4. Hedef kullanıcılar

### Birincil

- Junior SOC analisti
- Sistem yöneticisi
- Siber güvenlik öğrencisi
- Küçük ekipte ilk incelemeyi yapan teknik personel

### İkincil

- Yerel LLM ve RAG sistemlerini değerlendiren geliştirici
- Air-gapped-ready deployment yaklaşımını inceleyen ekip

## 5. Ürün konumlandırması

Ürün şunlardan biridir:

- İlk olay inceleme yardımcısı
- Log özetleme ve kanıt yapılandırma aracı
- Doküman destekli karar destek prototipi
- Yerel LLM deployment profile evaluation platformu

Ürün şunlardan biri değildir:

- SIEM
- IDS/IPS
- Antivirüs
- SOC otomasyon platformu
- Otomatik saldırı engelleme sistemi
- Forensic doğruluk garantisi veren ürün
- Üretim sınıfı çok kullanıcılı SaaS

## 6. Ana kullanıcı akışı

1. Kullanıcı Swagger UI veya API üzerinden SSH/authentication logu yükler.
2. Dosya boyut, uzantı, MIME, içerik ve güvenli işleme kontrollerinden geçer.
3. Uygun parser seçilir.
4. Parser olayları ve deterministik istatistikleri çıkarır.
5. Bulgulardan hassas veriyi gereksiz yere taşımayan retrieval sorgusu oluşturulur.
6. Yerel bilgi tabanından ilgili document chunk’ları getirilir.
7. Parser bulguları, sınırlı/maskelenmiş evidence ve aynı retrieved context seçilen yerel LLM provider’ına verilir.
8. Model yapılandırılmış JSON raporu üretir.
9. Çıktı Pydantic ile doğrulanır.
10. Geçerli sonuç ve gerekli metadata SQLite’a kaydedilir.
11. Kullanıcı job durumu ve raporu API üzerinden görür.

## 7. Deterministik parser çıktıları

MVP parser aşağıdakileri hesaplamalıdır:

- Toplam ilgili olay sayısı
- Başarısız giriş sayısı
- Başarılı giriş sayısı
- Benzersiz kaynak IP sayısı ve listesi
- En aktif kaynak IP ve olay sayısı
- Hedef kullanıcı hesapları
- Root/privileged hesap denemeleri
- İlk ve son olay zamanı
- Analiz zaman aralığı
- Kısa sürede tekrar eden giriş denemeleri
- Geçersiz kullanıcı girişimleri
- Authentication yöntemleri
- Çok sayıda başarısızlıktan sonra başarılı giriş örüntüsü
- Parse edilemeyen satır sayısı
- Timestamp/timezone sınırlamaları

Parser temel gerçeklere saldırı etiketi eklemez. Örneğin `repeated_authentication_attempts=true` bir saldırı hükmü değildir.

## 8. Incident report response modeli

Üst düzey alanlar:

- `incident_id`
- `status`
- `summary`
- `observed_findings`
- `possible_interpretations`
- `risk_level`
- `risk_reasoning`
- `recommended_actions`
- `citations`
- `limitations`
- `parser_statistics`
- `model_information`
- `performance_metrics`

### Observed findings

- Yalnızca log/parser tarafından doğrulanmış gerçekler
- Her finding için tür, ifade, yapılandırılmış değer ve evidence reference
- Yorum veya saldırı atfı içermez

### Possible interpretations

- Kesinlik iddiası taşımaz
- Kanıtlarla uyumlu olası açıklamalar verir
- Alternatif benign açıklamaları dışlamaz
- İlgili citation’lara bağlanır

### Risk level

- `low`, `medium`, `high`
- “Critical” MVP’de yoktur; örnek logdan kesin kurum etkisi çıkarılamaz
- Gerekçe gözlenen gerçeklere dayanır
- Risk, saldırı kesinliği anlamına gelmez

### Recommended actions

İzin verilen kategoriler:

- Daha fazla log ve zaman çizelgesi inceleme
- Authentication kaynağını doğrulama
- İlgili hesap sahibini veya sistem sahibini doğrulama
- Log bütünlüğünü ve retention’ı koruma
- SSH hardening değerlendirmesi
- MFA/key-based authentication değerlendirmesi
- Yetkili kurum prosedürüne göre escalation
- İlgili host ve komşu sistem loglarını korele etme

Yasak davranışlar:

- Otomatik engelleme
- Otomatik hesap kapatma
- Komut çalıştırma
- Aktif tarama veya exploitation
- Credential deneme

## 9. Runtime ve model kapsamı

MVP iki provider içerir:

### Foundry Local

- Windows host üzerinde çalışır.
- Uygun WinML/execution provider hızlandırmasını kullanması hedeflenir.
- Model kataloğu ve model alias’ları uygulama sırasında cihazda doğrulanır.
- REST veya native SDK entegrasyon yolu spike sonucu seçilir.

### Ollama

- Windows host üzerinde çalışır.
- OpenAI-compatible endpoint üzerinden erişilir.
- İlk model adayı Qwen3 8B 4-bit’tir.
- Donanım veya latency uygun değilse Qwen3 4B fallback’tir.

Ürünün varsayılan provider/model profili ölçümden önce belirlenmez.

## 10. RAG kapsamı

İlk bilgi tabanı yaklaşık 5–10 kaynak içerir:

- NIST incident response
- CISA incident response
- MITRE ATT&CK brute-force/credential access ve savunma bilgileri
- OWASP logging rehberleri
- Microsoft güvenlik dokümanları
- SSH authentication monitoring/hardening kaynakları

MVP retrieval:

- PDF, Markdown ve plain text ingestion
- Başlık/bölüm koruyan chunking
- Chunk overlap
- SQLite metadata
- TF-IDF + cosine similarity
- Top-k citation

Opsiyonel:

- Yerel embedding modeli
- NumPy cosine similarity
- TF-IDF/embedding karşılaştırması

## 11. API kapsamı

Planlanan endpoint’ler:

- `GET /health`
- `GET /models`
- `POST /v1/knowledge/ingest`
- `GET /v1/knowledge/sources`
- `POST /v1/incidents/analyze`
- `GET /v1/incidents/{incident_id}`
- `POST /v1/benchmarks/run`
- `GET /v1/benchmarks/{benchmark_id}`

Analyze ve benchmark uzun sürebileceğinden job tabanlı yürür. POST `202 Accepted`, GET durum/sonuç döndürür.

## 12. Veritabanı kapsamı

Planlanan tablolar:

- `documents`
- `document_chunks`
- `incidents`
- `incident_findings`
- `model_runs`
- `benchmark_runs`
- `benchmark_results`

Ham log varsayılan olarak saklanmaz. Dosya hash’i, boyut, parser metadata’sı ve gerektiğinde maskelenmiş kısa evidence tutulabilir.

## 13. Benchmark amacı

Amaç:

> Bu cihazda ve tamamen yerel kullanımda hangi deployment profilinin güvenlik raporu kalitesi, hız ve bellek açısından en uygun dengeyi sunduğunu ölçmek.

Karşılaştırma profilleri en az:

- Bir Foundry Local model profili
- Bir Ollama model profili

Metrikler:

- Load time
- Time to first token
- Total response time
- Tokens/second
- Peak/average RAM
- Schema compliance
- Expected finding recall
- Unsupported claim count
- Citation validity/correctness
- Groundedness
- Recommendation completeness
- Risk consistency
- Tekrarlar arası tutarlılık

## 14. Güvenlik ve gizlilik hedefleri

- Yüklenen dosya güvenilmeyen veridir.
- Raw log application loguna yazılmaz.
- Prompt injection’a karşı system/data ayrımı vardır.
- Knowledge dokümanındaki talimatlar yürütülmez.
- Model tool veya shell erişimi alamaz.
- Dosya limitleri ve timeout uygulanır.
- Geçici dosya temizlenir.
- Secret/personal data repository’ye girmez.
- API varsayılan olarak local erişimle sınırlıdır.

Ayrıntılı model: `SECURITY_AND_PRIVACY.md`.

## 15. Non-functional gereksinimler

### Güvenilirlik

- Parser aynı input için aynı output’u üretir.
- Job ve hata durumları açıkça kaydedilir.
- Geçersiz LLM çıktısı başarılı kabul edilmez.

### Tekrar üretilebilirlik

- Dependency’ler exact sürümlerle kilitlenir.
- Model ID/digest ve quantization kaydedilir.
- Prompt ve schema sürümlendirilir.
- Sentetik benchmark vakaları repository’de tutulur.

### Taşınabilirlik

- Windows native fallback belgelenir.
- Docker, host runtime’lara erişebildiği ölçüde desteklenir.
- Bilgi tabanı ve DB tek makinede çalışır.

### Gözlemlenebilirlik

- Correlation ID
- Structured logs
- Stage duration
- Güvenli hata kodları
- Raw log/prompt olmadan teşhis edilebilirlik

## 16. MVP kabul kriterleri

1. Foundry Local’da en az bir model çalışır.
2. Ollama’da en az bir model çalışır.
3. FastAPI her iki provider’a erişebilir.
4. Güvenli SSH log upload çalışır.
5. Parser belirlenen gerçekleri doğru çıkarır.
6. En az 5 lisansı denetlenmiş kaynak ingest edilir.
7. Retrieval ilgili chunk’ları getirir.
8. İki provider da geçerli yapılandırılmış rapor üretebilir veya kontrollü hata verir.
9. Citation’lar gerçek chunk’lara bağlanır.
10. En az 10 etiketli vaka vardır.
11. İki deployment profili aynı vakalarla karşılaştırılır.
12. Latency, token/s ve RAM kaydedilir.
13. Deterministik test suite geçer.
14. Docker veya native fallback belgelenmiş ve çalışırdır.
15. Model cache sonrası internet kapalı örnek analiz tamamlanır.
16. README ile başka biri kurulumu ve demoyu tekrar edebilir.

## 17. Stretch goals

Öncelik sırası:

1. IP/kullanıcı maskeleme
2. Basit web UI
3. MITRE ATT&CK teknik eşleştirme
4. Nmap parser
5. Nginx parser
6. TF-IDF/embedding karşılaştırması
7. RAG açık/kapalı deneyi
8. PDF incident raporu
9. Analiz geçmişi
10. İmzalı offline bundle tasarımı

## 18. Teslim biçimi

- Açık GitHub repository
- Kurulum ve kullanım README’si
- Sentetik demo verisi
- Testler ve benchmark sonuçları
- Türkçe yaklaşık 2–5 dakikalık tanıtım videosu

Video bir akademik savunma değildir. Problem, yapılan ürün, öğrenilen teknik konular ve somut çıktı kısa biçimde gösterilecektir.

