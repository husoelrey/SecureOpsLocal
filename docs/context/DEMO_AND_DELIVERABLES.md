# SecureOps Local — Demo and Deliverables

## 1. Teslim bağlamı

Proje Microsoft Türkiye AI Innovators çevrimiçi staj programı kapsamında geliştirilmektedir. Ana teslim, GitHub repository ve projeyi/öğrenilenleri tanıtan kısa Türkçe videodur.

Video uzun teknik savunma veya canlı jüri sunumu değildir. Buna rağmen repository ve demo, otomatik veya manuel kod incelemesine dayanabilecek kalitede olmalıdır.

## 2. Teslim paketleri

- Public GitHub repository veya erişilebilir proje linki
- Açık ve tekrar üretilebilir README
- Sentetik örnek SSH logları
- Bilgi tabanı kaynak/lisans manifesti
- Unit/integration/security testleri
- Benchmark vaka seti ve sonuçları
- Docker veya native Windows çalışma yöntemi
- Offline hazırlık/doğrulama rehberi
- Türkçe 2–5 dakikalık video

Repository’ye eklenmeyecekler:

- Model ağırlıkları, lisans/dağıtım gerekçesi olmadan
- Foundry/Ollama cache
- Gerçek loglar
- Secret/token
- Çalışma SQLite DB’si
- Redistribution izni olmayan tam doküman

## 3. Video ana mesajı

> SecureOps Local, hassas SSH loglarını buluta göndermeden analiz eden yerel olay inceleme yardımcısıdır. Temel güvenlik gerçeklerini LLM’e hesaplatmak yerine deterministik Python parser kullanır; RAG ile güvenilir kaynakları getirir; Foundry Local ve Ollama deployment profillerini kalite, hız ve RAM açısından karşılaştırır.

## 4. Beş dakikalık akış

### 0:00–0:35 — Problem

- Güvenlik logları hassas olabilir.
- Cloud LLM’e göndermek her zaman uygun değildir.
- Junior analistin ilk incelemesi zaman alabilir.

### 0:35–1:10 — Çözüm ve fark

- Genel chatbot değil.
- SSH logunu deterministik parser işler.
- RAG kaynak getirir.
- Local LLM temkinli rapor yazar.

### 1:10–2:30 — Demo

1. Swagger’da sentetik log yükle.
2. Provider/model profile seç.
3. Incident job oluştur.
4. Sonuçta parser statistics göster.
5. Observed findings ile possible interpretations farkını göster.
6. Citation’ı kaynak chunk’a bağla.

### 2:30–3:25 — Multi-runtime benchmark

- Aynı vaka/evidence Foundry ve Ollama’ya veriliyor.
- Latency, TTFT, token/s, RAM, schema ve quality metrikleri.
- Sonucu önceden iddia etme; gerçek tabloyu göster.

### 3:25–4:10 — Güvenlik ve offline

- Ham log saklanmıyor.
- Cloud fallback yok.
- Model önceden indirildikten sonra internet kapalı demo.
- Sistem otomatik engelleme/komut çalıştırmıyor.

### 4:10–5:00 — Öğrenilenler

- RAG’in model eğitimi olmadığı
- Parser ile LLM sorumluluğunu ayırma
- Local inference runtime’ları
- Structured output validation
- Güvenli file upload
- Reproducible benchmark

## 5. İki dakikalık kısa akış

### 0:00–0:20

Problem ve local privacy.

### 0:20–0:55

Mimari: parser → RAG → local LLM → Pydantic report.

### 0:55–1:30

Tek canlı incident sonucu ve citation.

### 1:30–1:50

Foundry/Ollama benchmark tablosu.

### 1:50–2:00

Öğrenme ve GitHub linki.

## 6. Demo için seçilecek vaka

Tek vaka şunları göstermeli:

- Bir kaynak IP
- Birden fazla başarısız giriş
- Invalid user
- Root denemesi
- Başarısızlıklardan sonra başarılı giriş
- Açık ama kesin saldırı olmayan yorum alanı

Vaka sentetik olmalı ve dokümantasyon IP blokları kullanmalı.

## 7. README başarı kriterleri

README okuyucusu şu sorulara cevap bulmalı:

- Bu proje ne yapıyor/ne yapmıyor?
- Neden local?
- RAG burada ne demek?
- Foundry ve Ollama neden birlikte?
- Sistem gereksinimleri nedir?
- Model ve dependency nasıl hazırlanır?
- Nasıl çalıştırılır?
- Swagger ile nasıl analiz yapılır?
- Test ve benchmark nasıl çalıştırılır?
- Offline çalışma nasıl doğrulanır?
- Veriler/lisanslar nasıl yönetilir?
- Bilinen sınırlamalar nelerdir?

## 8. Video öncesi final checklist

- Clean clone veya temiz ortamdan kurulum denendi.
- Demo logu repository’de.
- Demo knowledge snapshot hazır.
- İki runtime health check çalışıyor.
- Model cache hazır.
- İnternet kapalı test sonucu kayıtlı.
- Swagger response beklenen ve okunabilir.
- Benchmark tablosu gerçek sonuçlardan.
- Ekranda secret/gerçek kullanıcı/path görünmüyor.
- Video süresi prova edildi.
- Ses ve terminal fontu okunabilir.

## 9. LinkedIn/GitHub anlatım sınırı

- Program bağlamı dürüst biçimde belirtilebilir.
- Microsoft çalışanı veya Microsoft ürünü olduğu izlenimi yaratılmaz.
- “Microsoft AI Innovators programı kapsamında geliştirildi” gibi ifade kullanılabilir.
- Benchmark sonucu abartılmaz.
- “Air-gapped-ready” kullanılır; koşulsuz “tam air-gapped” denmez.

