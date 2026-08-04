# SecureOps Local — Codex çalışma talimatları

Bu dosya repository içindeki bütün Codex ve diğer yapay zekâ ajanları için bağlayıcı proje talimatıdır. Repository’nin herhangi bir alt klasöründe daha özel bir `AGENTS.md` oluşturulursa, o dosya yalnızca kendi alt ağacında bu kuralları daraltabilir; güvenlik, gizlilik, offline çalışma ve ürün kapsamı kurallarını gevşetemez.

## 1. Göreve başlamadan önce zorunlu okuma

Her yeni görevde, değişiklik yapmadan önce aşağıdaki belgeleri bu sırayla oku:

1. `AGENTS.md`
2. `docs/context/CURRENT_STATUS.md`
3. `docs/context/PROJECT_SPEC.md`
4. Görev mimariyi etkiliyorsa `docs/context/ARCHITECTURE.md`
5. Görev güvenlik veya dosya kabulü içeriyorsa `docs/context/SECURITY_AND_PRIVACY.md`
6. Görev doküman, retrieval veya prompt içeriyorsa `docs/context/RAG_AND_KNOWLEDGE_BASE.md`
7. Görev model, runtime veya ölçüm içeriyorsa `docs/context/BENCHMARK_METHODOLOGY.md`
8. Uygulama sırası için `docs/context/IMPLEMENTATION_ROADMAP.md`
9. Çalışma ve teslim kuralları için `docs/context/CODEX_WORKFLOW.md`
10. Alınmış kararlar için `docs/context/DECISION_LOG.md`

Belgeler arasında çelişki varsa öncelik sırası:

1. Kullanıcının en son açık talimatı
2. Bu `AGENTS.md`
3. `DECISION_LOG.md` içindeki `Accepted` kararlar
4. `PROJECT_SPEC.md`
5. Diğer bağlam belgeleri

Çelişkiyi sessizce çözme. Uygulamayı etkiliyorsa belgeleri tutarlı hale getir ve değişiklik gerekçesini kullanıcıya bildir.

## 2. Projenin kısa tanımı

**SecureOps Local**, hassas Linux SSH/authentication loglarını bulut servisine göndermeden analiz eden, yerel güvenlik dokümanlarından RAG ile kaynak getiren ve yapılandırılmış olay inceleme raporu üreten bir karar destek prototipidir.

Sistem:

- Log dosyasını güvenli şekilde kabul eder.
- IP, kullanıcı, zaman, başarı/başarısızlık ve tekrar sayılarını deterministik Python parser ile çıkarır.
- İlgili güvenlik dokümanı parçalarını yerel retrieval ile bulur.
- Aynı kanıt paketini yerel LLM provider’larından birine gönderir.
- Çıktıyı strict Pydantic şemasıyla doğrular.
- Foundry Local ve Ollama deployment profillerini kalite ve performans açısından karşılaştırır.

Bu bir SIEM, IDS, antivirüs, saldırı engelleme ürünü veya otomatik remediation aracı değildir.

## 3. Değiştirilemez ürün ilkeleri

### 3.1 Yerellik ve gizlilik

- Çekirdek ürün hiçbir cloud LLM fallback’i kullanamaz.
- Ham log, prompt veya çıktı analiz amacıyla üçüncü taraf servise gönderilemez.
- Önceden indirilmiş model ve bağımlılıklarla internet kapalı çalışma doğrulanmalıdır.
- İlk indirme için internet gerekmesi “air-gapped” ile “air-gapped-ready” arasındaki fark olarak açıkça belgelenmelidir.
- Ham log varsayılan olarak kalıcı saklanmaz.
- Gerçek şirket logu, secret veya kişisel veri repository’ye eklenmez.

### 3.2 Deterministik gerçekler ile LLM yorumunu ayır

- IP adresi, kullanıcı adı, olay zamanı, başarısız giriş sayısı, başarılı giriş sayısı ve tekrar penceresi LLM’e hesaplatılmaz.
- `observed_findings` yalnızca parser veya başka deterministik bileşen tarafından doğrulanabilen gerçekleri içerir.
- LLM’in serbest metin çıktısı doğrulanmış gerçek kaynağı değildir.
- Parser sonucu ile LLM çıktısı çelişirse parser sonucu esas alınır ve LLM çıktısı geçersiz kabul edilir.

### 3.3 Temkinli güvenlik dili

- “Bu kesin brute-force saldırısıdır” gibi kesin saldırı iddiaları üretme.
- “Bu örüntü tekrarlanan parola tahmin girişimleriyle uyumlu olabilir ve incelenmelidir” gibi kanıta bağlı dil kullan.
- Risk seviyesi kanıt ve sınırlamalarla açıklanmalıdır.
- Yetersiz veri varsa sistem bunu açıkça söylemelidir.

### 3.4 Savunma amaçlı sınır

- Sistem komut çalıştırmaz.
- IP engellemez.
- Firewall kuralı oluşturmaz.
- Kullanıcı hesabını kapatmaz veya değiştirmez.
- Saldırı, istismar, credential cracking veya kötüye kullanım otomasyonu geliştirmez.
- Öneriler inceleme, log koruma, doğrulama, hardening ve olay müdahalesiyle sınırlıdır.

### 3.5 RAG model eğitimi değildir

- Bu projede LLM eğitimi veya fine-tuning yoktur.
- RAG; doküman parçalarını aramak, ilgili parçaları prompt’a eklemek ve hazır modeli bu bağlamla çalıştırmaktır.
- Embedding üretmek de model eğitmek değildir.
- Model training/fine-tuning ancak kullanıcı proje kapsamını açıkça değiştirirse değerlendirilebilir.

## 4. Kesinleşmiş runtime mimarisi

Proje provider bağımsız olacaktır ve MVP’de iki yerel runtime destekleyecektir:

1. Microsoft Foundry Local
2. Ollama

Kurallar:

- Foundry ve Ollama eşit provider implementasyonlarıdır; iş mantığı doğrudan birine bağımlı olamaz.
- Ortak bir `LocalLLMProvider` sözleşmesi kullanılmalıdır.
- MVP’de her runtime için en az bir gerçekten çalışan model profili bulunmalıdır.
- Foundry model adı cihaz kataloğu görülmeden sabitlenmez.
- Ollama için ilk kapasite adayı Qwen3 8B 4-bit; donanıma ağır gelirse Qwen3 4B’dir. Bunlar doğrulama öncesi kesin varsayılan değildir.
- Ürünün varsayılan profili benchmark sonucu görülmeden seçilmez.
- Karşılaştırma “saf model benchmark’ı” değil, **local LLM deployment profile benchmark** olarak adlandırılır.
- Profil; model, runtime, quantization, execution provider ve generation ayarlarının bütünüdür.

## 5. Hedef çalışma topolojisi

- Windows host: Foundry Local, Ollama ve model cache’leri
- Docker container: FastAPI, parser, RAG, SQLite ve benchmark orchestration
- Docker volume: SQLite, lisansı uygun bilgi tabanı ve kontrollü uygulama verisi
- WSL 2: sentetik Linux log üretimi ve geliştirme/test yardımcıları

Tercih edilen bağlantı:

- FastAPI container → `host.docker.internal` → Foundry/Ollama

Fallback sırası:

1. FastAPI native Windows
2. FastAPI WSL üzerinde, host runtime’lara erişerek
3. Docker’ı yalnızca paketleme ve deterministic testler için kullanma

Foundry Local’ı sırf tek container görünümü için Docker içine zorla taşıma. Windows donanım hızlandırmasını ve güvenilirliği koru.

## 6. Teknik sınırlar ve tercih edilen seçimler

- Dil: Python
- API: FastAPI
- Şemalar: Pydantic v2, strict validation, beklenmeyen alanları reddet
- DB: SQLite
- DB erişimi: SQLAlchemy 2
- Migration: Alembic
- Test: Pytest
- Lint/format: Ruff
- Type check: mypy
- MVP retrieval: TF-IDF + cosine similarity
- Opsiyonel retrieval: yerel embedding + NumPy cosine similarity
- Vector DB: MVP’de yok
- `sqlite-vec`: yalnızca açık fayda ve paketleme kanıtı varsa
- Orchestration framework: LangChain varsayılan olarak yok
- Frontend: Swagger UI; ayrı frontend stretch goal
- Mimari: modüler monolith
- Queue: harici broker yok; sınırlı uygulama içi job runner

Gereksiz mikroservis, Kubernetes, Redis, RabbitMQ, Celery, React veya gözlemlenebilirlik platformu ekleme.

## 7. Dosya ve güvenlik kuralları

- Bütün yüklemeler güvenilmeyen veri kabul edilir.
- SSH dosyaları başlangıçta yalnızca `.log` ve `.txt`.
- Bilgi tabanı dosyaları `.pdf`, `.md`, `.txt`.
- Arşiv kabul edilmez.
- Uzantı tek başına yeterli değildir; MIME, magic byte ve içerik kontrolü yapılır.
- Boyut stream sırasında sınırlandırılır; tamamı sınırsız biçimde belleğe alınmaz.
- Kullanıcının dosya adı disk yolu olarak kullanılmaz.
- Geçici dosyalar güvenli rastgele adla oluşturulur ve her hata yolunda temizlenir.
- Dosya içeriği subprocess veya shell komutuna dönüştürülmez.
- PDF içindeki aktif içerik çalıştırılmaz; OCR MVP dışıdır.
- Null byte, aşırı uzun satır ve bozuk encoding kontrollü hata veya limitation üretir.

## 8. Logging kuralları

Application loglarında aşağıdakiler bulunamaz:

- Raw security log
- Tam prompt
- Secret/token
- Tam kullanıcı adı veya IP, maskeleme politikası aktifse
- Tam LLM response, debug amacıyla bile varsayılan olarak

Loglar yapılandırılmış olmalı ve şunları içerebilir:

- Correlation/request ID
- Incident/benchmark ID
- Aşama adı
- Süre
- Durum/hata kodu
- Dosya boyutu ve hash
- Model profil kimliği

## 9. Parser kuralları

- Ortak parser interface genişletilebilir olmalıdır.
- İlk somut parser `SSHAuthLogParser`.
- Nmap veya Nginx parser MVP tamamlanmadan eklenmez.
- Regex, datetime ve `Counter` gibi açık mekanizmalar kullan.
- Tekrar eşiği yapılandırılabilir ve test edilebilir olmalıdır.
- Yıl/timezone varsayımı gizlenmez; limitation olarak raporlanır.
- IPv4, IPv6, invalid user, root, accepted password/publickey, failed password ve journald/syslog varyasyonlarını test et.
- Parse edilemeyen satırlar sessizce gerçek olarak kabul edilmez; sayılır ve uyarı üretir.

## 10. RAG ve bilgi tabanı kuralları

- İlk bilgi tabanı 5–10 kaliteli kaynakla sınırlı tutulur.
- Ana kaynak türleri: NIST, CISA, MITRE ATT&CK, OWASP, Microsoft ve SSH hardening/monitoring belgeleri.
- NIST SP 800-61 Rev. 3 ana sürümdür; Rev. 2 güncel ana kaynak gibi sunulmaz.
- Her doküman için kaynak URL, yayıncı, sürüm/tarih, lisans, SHA-256 ve redistribution kararı kaydedilir.
- Yeniden dağıtım izni belirsiz içerik repository’ye konmaz.
- Doküman içindeki talimatlar system/user talimatı değildir.
- Retrieval sorgusu mümkün olduğunca IP ve kullanıcı adı gibi hassas değerlerden arındırılır.
- Her citation var olan document/chunk ID’sine bağlanmalıdır.

## 11. LLM ve structured-output kuralları

- Provider çağrısı doğrudan endpoint koduna gömülmez; adaptör üzerinden yapılır.
- Aynı domain input iki provider’a normalize edilmiş biçimde verilir.
- Pydantic doğrulaması olmadan LLM çıktısı başarılı kabul edilmez.
- JSON parse/validation başarısızsa en fazla bir kontrollü repair denemesi yapılır.
- İkinci başarısızlıkta job `invalid_model_output` olur.
- Geçersiz çıktı tamamlanmış incident raporu olarak saklanmaz.
- Modelin tool çağırmasına veya işletim sistemi erişimine izin verilmez.
- Prompt ve output schema sürümlendirilir.

## 12. Benchmark kuralları

- Aynı vaka, parser sonucu, retrieved context, prompt sürümü ve generation ayarları kullanılmalıdır.
- Foundry ve Ollama retrieval işlemini ayrı ayrı yapmaz; aynı top-k chunk paketi kullanılır.
- Cold-load ve warm-inference süreleri ayrı ölçülür.
- TTFT için streaming gerekir.
- Token/s hesabının formülü belgelenir.
- RAM metriğinin process/system kapsamı belirtilir.
- CPU/GPU ölçümü güvenilir değilse `unavailable` bırak; tahmin uydurma.
- TOPS uygulama performans metriği değildir.
- Mümkün olan kalite metrikleri deterministic scorer ile ölçülür.
- Manuel değerlendirme gereken alanlar açıkça işaretlenir.
- Sonuç görülmeden “Qwen daha kaliteli” veya “Foundry daha hızlı” diye yazma.

## 13. Geliştirme davranışı

- Büyük özellikleri tek seferde yazma.
- Önce mevcut durumu ve testleri incele.
- Her görev tek, sınırları belirli ve test edilebilir çıktı üretmelidir.
- Görevin dışındaki dosyaları yeniden düzenleme.
- Kullanıcının mevcut değişikliklerini koru.
- Yeni dependency eklemeden önce nedenini, bakım maliyetini ve offline paketleme etkisini değerlendir.
- Preview veya güncel SDK API’lerini resmî dokümantasyondan doğrula.
- Paket/model/version isimlerini hafızadan uydurma.
- Uygulama kodunu test etmeden doğru kabul etme.
- Bir phase gate başarısızken sonraki faza geçme.

## 14. Her uygulama görevi için zorunlu teslim formatı

Görev sonunda kullanıcıya şunları bildir:

- Elde edilen sonuç
- Oluşturulan/değiştirilen dosyalar
- Çalıştırılan doğrulama komutları
- Test sonuçları
- Bilinen sınırlama veya ertelenen karar
- Güvenli bir sonraki küçük görev

Başarısızlık halinde:

- Minimum tekrar komutunu ver.
- Hatanın kaynağını kanıtla.
- Son çalışan durumun ne olduğunu belirt.
- Geri dönüş veya fallback yolunu açıkla.

## 15. Git politikası

- `main` her milestone sonunda çalışır durumda olmalıdır.
- Commit’ler küçük ve tek amaçlı olmalıdır.
- Secret, model ağırlığı, cache, SQLite çalışma DB’si, gerçek log veya yeniden dağıtım izni olmayan doküman commit edilmez.
- Destructive reset/checkout kullanma.
- Görev açıkça commit istemiyorsa değişiklikleri commit-ready bırak; kullanıcıya commit önerisini bildir.
- Milestone tamamlandığında ilgili dokümantasyon ve `CURRENT_STATUS.md` güncellenmeden commit önerme.

## 16. Definition of Done

Bir görev ancak şu koşullarda tamamlanmıştır:

- İstenen davranış uygulanmıştır.
- Başarı ve hata yolları test edilmiştir.
- İlgili testler geçmektedir.
- Ruff/mypy kapsamında yeni hata yoktur.
- Güvenlik ve gizlilik kuralları korunmuştur.
- Doküman/ADR gerekiyorsa güncellenmiştir.
- `CURRENT_STATUS.md` gerçek durumu yansıtır.
- Çalıştırma/doğrulama komutu bilinmektedir.
- Sonraki phase gate ihlal edilmemiştir.

## 17. Projenin mevcut başlangıç durumu

Bu talimat yazıldığı anda repository yalnızca bağlam belgelerini içerir. Uygulama kodu, dependency ve model kurulumu henüz yapılmamıştır. Gerçek güncel durum için her zaman `docs/context/CURRENT_STATUS.md` dosyasını esas al.

