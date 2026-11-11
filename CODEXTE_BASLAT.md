# Codex'te KUZUCU ERP v0.14.0 ile devam etme

1. Aynı Codex hesabında bu sohbete devam ediyorsanız önce mevcut çalışma alanının durumunu kontrol ettirin. Kaynaklar burada zaten varsa eski paketi yeniden uygulamayın.
2. Yeni bir görevde bu ZIP'i ekleyin. Codex kaynakları **PROJE_KODU/KUZUCU_ERP** altında bulsun; paket kökündeki `KUZUCU_ERP_PROJE_DEVIR_NOTLARI.md`, `GELISTIRME_LISTESI.md` ve `SURUM_DOGRULAMA.md` belgelerini birlikte okusun. iPad için `IPAD_ILE_DEVAM.md` dosyasını izleyin.
3. Codex'e şu ilk mesajı yaz:

   > KUZUCU ERP v0.14.0 ön test ve geliştirme projesine devam edeceğiz. `AGENTS.md`, `KUZUCU_ERP_PROJE_DEVIR_NOTLARI.md`, `GELISTIRME_LISTESI.md`, `MAC_GUNCELLEME_V14.md` ve `SURUM_DOGRULAMA.md` dosyalarını oku. Önce mevcut kaynakları ve test durumunu kontrol et. Eski değişiklikleri yeniden uygulama. Yeni taleplerimi listele; **ben yeniden “Son sürümü hazırla” demeden yeni sürüm oluşturma.** Hiçbir şey yayımlama. Tüm kullanıcı metinleri sade Türkçe olsun. iPad'de yalnızca Codex üzerinden geliştirmeye devam edeceğim.

4. Kayıtlarınız Mac'te `ciftlik.db` içinde olabilir. Bu aktarım ZIP'ine **özel işletme verilerini koymadık**. Dosyayı güvenli yedeklemeden paylaşmayın; kaynak kod deposuna veya kamuya açık bir yere yüklemeyin.

Codex'in sohbet geçmişine doğrudan eriştiğini varsaymayın: devir notları konuşmadaki gereksinimleri taşır, fakat konuşmadaki her mesajın birebir dökümü değildir.

## Geliştirme komutları

Python 3.11–3.13 ile uygulama klasöründe sanal ortam oluşturun; `python -m pip install -r requirements.txt -c requirements.constraints.txt` kullanın. Testlerde gerçek veritabanını kullanmayın: her çalışma için ayrı geçici SQLite yolu, `KUZUCU_BACKUP_DIR` ve `KUZUCU_REPORT_DIR` seçin. Ardından uygulama klasöründe `python -m pytest -q` çalıştırın.

Bu sohbette hazırlanan bulut ortamında `/workspace/kuzucu-cloud/test.sh` ve `start.sh` yardımcıları vardır; yeni göreve taşındıklarını varsaymayın. Uygulama, veritabanı ve bu süreçler ayrı ayrı kontrol edilmelidir. Her bulut görevi zaten izoledir; açıkça istenmedikçe Git worktree oluşturmayın.

İsteğe bağlı gerçek tarayıcı kontrolü: Node.js, Playwright ve Chromium kuruluysa, **yalnızca yeni/boş bir yerel test sunucusunda** `node tools/ui_smoke.cjs YEREL_DENEME_ADRESI CIKTI_KLASORU` çalıştırılabilir. Bu kontrol parsel/görsel, ajanda silme, stok miktarı ve farklı ekran boyutlarını dener. Mevcut hesaplı veritabanında çalışmayı reddeder. `CHROMIUM_PATH` ile sistem Chromium yolu seçilebilir. Python testlerinin çalışması için Node.js gerekmez.
