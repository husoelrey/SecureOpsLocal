# SecureOps Local — Codex Workflow

## 1. Amaç

Kullanıcı uygulama kodunu manuel yazmayacaktır. Kod, test, dokümantasyon ve teşhis Codex tarafından küçük adımlarla yürütülecektir. Bu nedenle her Codex görevi hem teknik sonuç üretmeli hem de kullanıcının ne yapıldığını anlayabileceği bir iz bırakmalıdır.

## 2. Her görev öncesi zorunlu preflight

1. `AGENTS.md` ve `CURRENT_STATUS.md` oku.
2. `git status --short --branch` çalıştır.
3. İlgili mevcut dosyaları ve testleri oku.
4. Görevin bağlı olduğu phase gate’i belirle.
5. Değişiklik yetkisinin kullanıcı talebinden çıktığını doğrula.
6. Resmî API/paket/model bilgisi gerekiyorsa güncel resmî kaynağı doğrula.
7. En küçük uygulanabilir değişikliği tanımla.

Preflight’ı kullanıcıdan tekrar onay almak için kullanma; bloklayıcı olmayan yerde makul varsayımla ilerle.

## 3. Görev sözleşmesi

Uygulamadan önce içsel olarak şu sözleşmeyi kur:

- Amaç
- Kapsam dışı
- Değişecek dosyalar
- Başarı kriteri
- Çalıştırılacak testler
- Güvenlik/gizlilik etkisi
- Fallback

Görev genişse uygulamadan önce küçük parçalara böl. Tek adımda bütün projeyi yazma.

## 4. Dosya oluşturma politikası

- Repository-native düzeni takip et.
- Yeni modül yalnızca açık sorumluluğu varsa oluştur.
- `utils.py` benzeri belirsiz çöp çekmecelerinden kaçın.
- Domain modellerini API request modelleriyle gereksiz yere birleştirme.
- Runtime’a özgü kod `llm/foundry.py` ve `llm/ollama.py` gibi adaptörlerde kalmalı.
- Test fixture’ları sentetik ve okunabilir olmalı.
- Generated/cache/runtime dosyaları `.gitignore` kapsamına alınmalı.

## 5. Dependency politikası

Yeni dependency eklemeden önce:

1. Standart kütüphane yeterli mi?
2. Dependency gerçek karmaşıklığı azaltıyor mu?
3. Windows ve Docker’da çalışıyor mu?
4. Offline wheel olarak paketlenebilir mi?
5. Lisansı uygun mu?
6. Bakımı aktif mi?
7. Başka runtime dependency’siyle çakışıyor mu?

Foundry Windows SDK dependency’si container ortak dependency setine zorla eklenmez. Native Windows gereksinimleri ayrı lock/extra içinde tutulur.

## 6. Uygulama döngüsü

1. Önce failing/contract test veya fixture oluştur.
2. En küçük implementasyonu yaz.
3. Hedef testi çalıştır.
4. Failure path testini çalıştır.
5. İlgili daha geniş test grubunu çalıştır.
6. Ruff/mypy kontrolü yap.
7. Diff’i oku; görev dışı değişiklik var mı kontrol et.
8. Belgeleri ve current status’u güncelle.
9. Kullanıcıya sonuç odaklı rapor ver.

## 7. Test kademeleri

Hızlı sıra:

1. Tek test dosyası
2. İlgili unit klasörü
3. Deterministic test suite
4. Ruff
5. mypy
6. Gerekirse integration
7. Açıkça gerekiyorsa local LLM/slow/offline

Gerçek model testini her küçük değişiklikte çalıştırma. Model testi zaman ve kaynak tüketir; contract/fake testleri normal geliştirmede esas olmalıdır.

## 8. Güncel dokümantasyon doğrulaması

Aşağıdaki konular değişken kabul edilir ve uygulamadan önce resmî kaynakla kontrol edilir:

- Foundry Local paket isimleri ve API metotları
- Foundry CLI komutları
- Foundry model alias/catalog
- Ollama API alanları ve runtime davranışı
- Model tag/digest/quantization
- FastAPI/Pydantic/SQLAlchemy güncel uyumluluğu
- Güvenlik advisories ve dependency sürümleri

Teknik cevaplarda birincil kaynak kullan. Blogdaki eski kodu güncel SDK gerçeği gibi kopyalama.

## 9. Hata teşhis protokolü

Bir komut veya test başarısızsa:

1. Tam hata ve exit code’u kaydet.
2. Aynı hatayı minimum komutla tekrar et.
3. Ortam, kod, dependency veya external runtime ayrımını yap.
4. Varsayım yerine kanıt topla: version, status, health, minimal request.
5. Birden çok rastgele değişiklik yapma.
6. Fix sonrası failure testini tekrar çalıştır.
7. Çözülmezse fallback’i uygula ve decision/current status’a yaz.

## 10. Kullanıcıya ara güncelleme

Tool kullanılan uzun görevlerde kullanıcı 60 saniyeden uzun sessiz bırakılmamalıdır. Güncellemeler:

- Ne doğrulandı?
- Hangi risk kapandı?
- Şimdi hangi küçük adım yürütülüyor?

Gereksiz terminal ayrıntısını kullanıcıya yığma.

## 11. Görev sonu raporu

Önerilen format:

1. Sonuç
2. Değişen dosyalar
3. Doğrulama/test
4. Sınırlamalar veya açık karar
5. Sıradaki küçük görev

Kullanıcı daha kısa cevap istemişse aynı bilgiyi kompakt ver.

## 12. Commit-ready kontrolü

- `git diff --check`
- `git status --short`
- Beklenmeyen generated file yok
- Testler geçiyor
- Documentation güncel
- Secret scan gözlemi
- Commit mesajı önerisi tek amacı anlatıyor

Örnek commit mesajları:

- `docs: establish SecureOps Local project context`
- `chore: bootstrap Python quality tooling`
- `feat(parser): parse failed SSH authentication events`
- `feat(rag): add TF-IDF chunk retrieval`
- `feat(llm): add Ollama provider adapter`
- `test(benchmark): add labeled SSH incident cases`

## 13. Kullanıcının öğrenmesini destekleme

Her mimari kararda sade gerekçe ver:

- Ne seçildi?
- Hangi problemi çözüyor?
- Daha basit alternatif neydi?
- Neden şimdi bu seçim yapıldı?
- Sunumda tek cümlede nasıl anlatılır?

Kullanıcının kod yazması beklenmez; ancak ortaya çıkan mimariyi açıklayabilmesi hedeflenir.

## 14. Yasak çalışma biçimleri

- Bütün projeyi tek promptta üretmek
- Test yazmadan geniş implementasyon
- Katalog görmeden model adı sabitlemek
- Başarısız model çıktısını sessizce string olarak döndürmek
- Raw logu debug loguna basmak
- Cloud fallback eklemek
- Gerçek saldırı/şirket logu kullanmak
- Kullanıcı değişikliklerini silmek
- Başarısız phase gate’i görmezden gelmek
- Sırf etkileyici görünsün diye altyapı eklemek

