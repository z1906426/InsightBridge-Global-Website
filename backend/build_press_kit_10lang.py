"""
build_press_kit_10lang.py — Regenerate the 10 Regional Reprint Kits under
/app/frontend/site/press-kit/{iso}.html.

Each page contains:
  • Localized <title>, meta description, H1, and 2-paragraph body
  • JSON-LD TechArticle schema with translationOfWork + author.alumniOf
  • Full 10-language hreflang matrix + x-default
  • Localized Open Graph + Twitter Card
  • Region-optimized social share bar (button order matches local platform usage)
  • Footer with reprint license + publisher
  • Site-wide ib-image-protect script (matches the main-site pages)

Idempotent — safe to rerun. Overwrites in place.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

BASE = "https://insightbridge.global"
INTEL = "https://intelligence.insightbridge.global"
CANONICAL_ARTICLE = f"{INTEL}/articles/2027-ai-global-hospitality-tourism-whitepaper-frontier-framework-frontier-market"
WHITEPAPER_PDF = f"{INTEL}/insightbridge-ai-hospitality-2027-whitepaper.pdf"
VISION_PDF = f"{INTEL}/yin-vision-2030-predictions-vs-reality-bilingual-archive.pdf"
SERVICES_URL = f"{BASE}/index.html#services"

OUT = Path(__file__).resolve().parent.parent / "frontend/site/press-kit"
OUT.mkdir(parents=True, exist_ok=True)

# ─── Language pack ─────────────────────────────────────────────────────────
# (iso, og_locale, dir, title, description, h1, body_p1, body_p2,
#  cta_wp_download, cta_vision_pdf, cta_services, license_line, share_labels)
LANGS = [
    {
        "iso": "ar", "og": "ar_SA", "dir": "rtl",
        "title": "2027 · الذكاء الاصطناعي × الضيافة والسياحة العالمية",
        "desc": "الورقة البيضاء الاستراتيجية لعام 2027 من InsightBridge Global: إعادة تشكيل السياحة عبر طبقة الوكيل، الطبقة المادية، وطبقة السيادة. تنبؤات رؤية 2030 قد تحققت بأرقام السوق.",
        "h1": "2027 · الذكاء الاصطناعي × الضيافة والسياحة على مستوى العالم",
        "p1": "لن يُذكر عام 2027 على أنه العام الذي «دخل» فيه الذكاء الاصطناعي إلى الفنادق — فقد دخل بالفعل. سيُذكر بأنه العام الذي انفصل فيه الفنادق إلى ثلاث طبقات لا تعود إلى بعضها: طبقة الوكيل الذي يبيع الغرف، الطبقة المادية التي تُشغل المبنى، وطبقة السيادة التي تحدد أي المشاريع تُبنى وأيها يُؤجَّل.",
        "p2": "أطلقت InsightBridge Global تنبؤات رؤية 2030 السعودية خلال الفترة مايو–يوليو 2026، وتم التحقق منها بالبيانات الرسمية خلال أربعة إلى ثمانية أسابيع فقط: تقليص المشاريع العملاقة، ضغط هوامش الفنادق الفاخرة، تأجيلات مسلسلة للافتتاحات الرئيسية. ماذا يعني ذلك للسنة المقبلة؟ الاختصار: تنتهي الحكاية الكبرى — ويبدأ التحوط الاستراتيجي.",
        "cta_wp": "↓ تحميل الورقة البيضاء (34 صفحة · EN/ZH)",
        "cta_vision": "↓ تحميل ملف رؤية 2030 (توقعات مقابل الواقع)",
        "cta_services": "→ خدمات InsightBridge الاستشارية",
        "share_label": "شارك هذا الملخص:",
        "license": "ترخيص: يُسمح بإعادة النشر مجاناً مع الاحتفاظ بتوقيع «د. تونغ ين، مؤسس والرئيس التنفيذي، InsightBridge Global LLC» ورابط المصدر الأصلي، وإرسال إشعار النشر خلال 7 أيام إلى Editor@intelligence.insightbridge.global.",
    },
    {
        "iso": "ru", "og": "ru_RU", "dir": "ltr",
        "title": "2027 · ИИ × Мировая индустрия гостеприимства и туризма",
        "desc": "Стратегическая белая книга InsightBridge Global на 2027 год: переустройство туризма через Agent Layer, Physical Layer и Sovereignty Layer. Прогнозы Vision 2030 подтверждены рыночными данными.",
        "h1": "2027 · ИИ × Мировая индустрия гостеприимства и туризма",
        "p1": "2027 год не запомнится годом, когда ИИ «вошёл» в отельный бизнес — он уже там. Он запомнится годом, в котором отель раскололся на три слоя, больше не собираемые вместе: Agent Layer, продающий номера; Physical Layer, эксплуатирующий здание; и Sovereignty Layer, решающий, какие мегапроекты строятся, а какие откладываются.",
        "p2": "Прогнозы InsightBridge Global относительно Vision 2030 (май–июль 2026) были подтверждены официальными данными за 4–8 недель: сокращение giga-projects, компрессия маржи ультра-люкса PIF, серия отложенных открытий. Итог: время grand-narrative истекло, начинается эпоха стратегического хеджирования.",
        "cta_wp": "↓ Скачать белую книгу (34 стр. · EN/ZH)",
        "cta_vision": "↓ Vision 2030 — Прогнозы vs Реальность (билингва)",
        "cta_services": "→ Консалтинговые услуги InsightBridge",
        "share_label": "Поделиться:",
        "license": "Лицензия: свободно перепечатывать с сохранением подписи «Dr. Tong Yin, Founder & CEO, InsightBridge Global LLC» и оригинальной ссылки, уведомление о публикации в течение 7 дней на Editor@intelligence.insightbridge.global.",
    },
    {
        "iso": "ko", "og": "ko_KR", "dir": "ltr",
        "title": "2027 · AI × 글로벌 호스피탤리티·투어리즘",
        "desc": "InsightBridge Global의 2027 전략 백서: Agent Layer, Physical Layer, Sovereignty Layer를 통해 재구성되는 관광 산업. Vision 2030 예측이 시장 데이터로 검증됨.",
        "h1": "2027 · AI × 글로벌 호스피탤리티·투어리즘 산업",
        "p1": "2027년은 AI가 호텔업에 '진입'한 해로 기억되지 않을 것이다 — 이미 진입해 있다. 대신, 호텔이 세 개의 결합되지 않는 층으로 분리된 해로 기록될 것이다: 객실을 판매하는 Agent Layer, 건물을 운영하는 Physical Layer, 그리고 어떤 프로젝트가 지어지고 어떤 것이 연기되는지 결정하는 Sovereignty Layer.",
        "p2": "InsightBridge Global의 사우디 Vision 2030 예측(2026년 5–7월)은 공식 데이터로 4–8주 만에 검증되었다: 기가프로젝트 축소, PIF 울트라 럭셔리 마진 압박, 주요 개장의 순차적 연기. 요약하자면: grand-narrative의 시대는 끝나고, 전략적 헤징의 시대가 시작된다.",
        "cta_wp": "↓ 백서 다운로드 (34쪽 · EN/ZH)",
        "cta_vision": "↓ Vision 2030 예측 vs 현실 (이중언어)",
        "cta_services": "→ InsightBridge 컨설팅 서비스",
        "share_label": "공유하기:",
        "license": "라이선스: 'Dr. Tong Yin, Founder & CEO, InsightBridge Global LLC'의 저작권 표시와 원본 링크를 유지하면 무료로 재게시 가능. 게시 후 7일 이내에 Editor@intelligence.insightbridge.global 로 게시 통보 발송.",
    },
    {
        "iso": "id", "og": "id_ID", "dir": "ltr",
        "title": "2027 · AI × Industri Hospitality & Pariwisata Global",
        "desc": "Whitepaper strategis 2027 dari InsightBridge Global: restrukturisasi pariwisata melalui Agent Layer, Physical Layer, dan Sovereignty Layer. Prediksi Visi 2030 telah diverifikasi oleh data pasar.",
        "h1": "2027 · AI × Hospitality & Pariwisata Global",
        "p1": "Tahun 2027 tidak akan dikenang sebagai tahun ketika AI 'masuk' ke industri hotel — AI sudah masuk. Ia akan dikenang sebagai tahun di mana hotel terpecah menjadi tiga lapisan yang tidak lagi dapat digabungkan: Agent Layer yang menjual kamar, Physical Layer yang mengoperasikan gedung, dan Sovereignty Layer yang memutuskan proyek mana yang dibangun dan mana yang ditunda.",
        "p2": "Prediksi Visi 2030 Arab Saudi dari InsightBridge Global (Mei–Juli 2026) diverifikasi oleh data resmi dalam 4–8 minggu: pengurangan giga-project, kompresi margin ultra-luxury PIF, penundaan berurutan atas pembukaan unggulan. Ringkasan: era grand narrative berakhir, era lindung nilai strategis dimulai.",
        "cta_wp": "↓ Unduh Whitepaper (34 hlm · EN/ZH)",
        "cta_vision": "↓ Visi 2030 — Prediksi vs Realitas (dwibahasa)",
        "cta_services": "→ Layanan Konsultasi InsightBridge",
        "share_label": "Bagikan ringkasan ini:",
        "license": "Lisensi: bebas dicetak ulang dengan mempertahankan atribusi 'Dr. Tong Yin, Founder & CEO, InsightBridge Global LLC' dan tautan sumber asli, kirim pemberitahuan publikasi dalam 7 hari ke Editor@intelligence.insightbridge.global.",
    },
    {
        "iso": "tr", "og": "tr_TR", "dir": "ltr",
        "title": "2027 · Yapay Zekâ × Küresel Otelcilik ve Turizm",
        "desc": "InsightBridge Global'ın 2027 stratejik beyaz kitabı: Agent Layer, Physical Layer ve Sovereignty Layer üzerinden turizmin yeniden yapılanması. Vision 2030 tahminleri gerçek piyasa verileriyle doğrulandı.",
        "h1": "2027 · Yapay Zekâ × Küresel Otelcilik ve Turizm Endüstrisi",
        "p1": "2027 yılı, yapay zekânın otelcilik sektörüne «girdiği» yıl olarak hatırlanmayacak — zaten girdi. Bunun yerine, otelin bir daha birleştirilemeyecek üç katmana ayrıldığı yıl olarak kaydedilecek: odaları satan Agent Layer, binayı işleten Physical Layer ve hangi projelerin yapıldığını, hangilerinin ertelendiğini belirleyen Sovereignty Layer.",
        "p2": "InsightBridge Global'ın Suudi Vision 2030 tahminleri (Mayıs–Temmuz 2026) resmi verilerle 4–8 hafta içinde doğrulandı: giga-projelerin küçültülmesi, PIF ultra-lüks marj sıkışması, öncü açılışların sıralı ertelenmesi. Kısacası: grand-narrative çağı kapanıyor, stratejik hedge çağı başlıyor.",
        "cta_wp": "↓ Beyaz Kitabı İndir (34 sayfa · EN/ZH)",
        "cta_vision": "↓ Vision 2030 — Tahminler vs Gerçeklik (iki dilli)",
        "cta_services": "→ InsightBridge Danışmanlık Hizmetleri",
        "share_label": "Bu özeti paylaş:",
        "license": "Lisans: 'Dr. Tong Yin, Founder & CEO, InsightBridge Global LLC' imzası ve orijinal kaynak bağlantısı korunarak ücretsiz yeniden yayımlanabilir; yayın bildirimi 7 gün içinde Editor@intelligence.insightbridge.global adresine gönderilmelidir.",
    },
    {
        "iso": "vi", "og": "vi_VN", "dir": "ltr",
        "title": "2027 · AI × Ngành Khách Sạn và Du Lịch Toàn Cầu",
        "desc": "Sách trắng chiến lược 2027 của InsightBridge Global: tái cấu trúc du lịch qua Agent Layer, Physical Layer và Sovereignty Layer. Các dự báo Vision 2030 đã được kiểm chứng bằng dữ liệu thị trường.",
        "h1": "2027 · AI × Ngành Khách Sạn & Du Lịch Toàn Cầu",
        "p1": "Năm 2027 sẽ không được ghi nhớ như năm AI 'bước vào' ngành khách sạn — AI đã ở trong đó rồi. Nó sẽ được ghi nhớ là năm khách sạn tách thành ba tầng không còn có thể ghép lại: Agent Layer bán phòng, Physical Layer vận hành tòa nhà, và Sovereignty Layer quyết định dự án nào được xây và dự án nào bị hoãn.",
        "p2": "Các dự báo về Vision 2030 của Ả Rập Xê Út do InsightBridge Global công bố (tháng 5–7/2026) đã được xác minh bằng dữ liệu chính thức trong vòng 4–8 tuần: cắt giảm siêu dự án, ép biên lợi nhuận khách sạn ultra-luxury của PIF, hoãn liên tiếp các khai trương chủ lực. Tóm lại: kỷ nguyên grand-narrative kết thúc, kỷ nguyên phòng ngừa rủi ro chiến lược bắt đầu.",
        "cta_wp": "↓ Tải Sách trắng (34 trang · EN/ZH)",
        "cta_vision": "↓ Vision 2030 — Dự báo vs Thực tế (song ngữ)",
        "cta_services": "→ Dịch vụ tư vấn InsightBridge",
        "share_label": "Chia sẻ bản tóm tắt:",
        "license": "Giấy phép: tự do đăng lại nếu giữ dòng tác giả 'Dr. Tong Yin, Founder & CEO, InsightBridge Global LLC' và liên kết nguồn, gửi thông báo đăng bài trong 7 ngày đến Editor@intelligence.insightbridge.global.",
    },
    {
        "iso": "zh", "og": "zh_CN", "dir": "ltr",
        "title": "2027 · AI × 全球酒店与旅游业",
        "desc": "InsightBridge Global 2027 战略白皮书：通过 Agent Layer、Physical Layer 与 Sovereignty Layer 重构旅游业。Vision 2030 预测已被市场数据验证。",
        "h1": "2027 · AI × 全球酒店与旅游业",
        "p1": "2027 年不会被记住为 AI「进入」酒店业的一年——它早已进入。这一年将被记住为：酒店从一个整体分裂成三个不再互通的层级——负责卖房的 Agent Layer，负责运营建筑的 Physical Layer，以及决定哪个项目开建、哪个搁置的 Sovereignty Layer。",
        "p2": "InsightBridge Global 于 2026 年 5–7 月发布的沙特 Vision 2030 系列预测，在 4–8 周内被官方数据依次验证：巨型项目收缩、PIF 超豪华酒店利润率压缩、旗舰项目分阶段延期。要点：宏大叙事时代落幕，战略对冲时代开启。",
        "cta_wp": "↓ 下载白皮书（34 页 · 中英双语）",
        "cta_vision": "↓ Vision 2030 · 预测 vs 现实（双语档案）",
        "cta_services": "→ InsightBridge 咨询服务",
        "share_label": "分享本摘要：",
        "license": "许可：自由转载，须保留作者署名「殷彤博士（Dr. Tong Yin），InsightBridge Global LLC 创始人兼首席执行官」及原始链接；请于发表后 7 日内将链接发送至 Editor@intelligence.insightbridge.global。",
    },
    {
        "iso": "de", "og": "de_DE", "dir": "ltr",
        "title": "2027 · KI × Globale Hotellerie und Tourismus",
        "desc": "Das strategische Whitepaper 2027 von InsightBridge Global: Neuordnung des Tourismus über Agent Layer, Physical Layer und Sovereignty Layer. Die Vision-2030-Prognosen wurden durch Marktdaten bestätigt.",
        "h1": "2027 · KI × Globale Hotellerie & Tourismusindustrie",
        "p1": "2027 wird nicht als das Jahr in Erinnerung bleiben, in dem KI in die Hotellerie „eingezogen“ ist — sie ist längst dort. Es wird als das Jahr in Erinnerung bleiben, in dem sich das Hotel in drei nicht mehr zusammenfügbare Schichten spaltete: den Agent Layer, der Zimmer verkauft; den Physical Layer, der das Gebäude betreibt; und den Sovereignty Layer, der entscheidet, welche Projekte gebaut und welche verschoben werden.",
        "p2": "Die Prognosen von InsightBridge Global zu Saudi Vision 2030 (Mai–Juli 2026) wurden innerhalb von 4–8 Wochen durch offizielle Daten bestätigt: Kürzungen bei Giga-Projekten, Margendruck im PIF-Ultra-Luxus, sequenzielle Verschiebungen von Leuchtturm-Eröffnungen. Kurz: Die Grand-Narrative-Ära endet, die Ära des strategischen Hedgings beginnt.",
        "cta_wp": "↓ Whitepaper herunterladen (34 S. · EN/ZH)",
        "cta_vision": "↓ Vision 2030 — Prognose vs. Realität (zweisprachig)",
        "cta_services": "→ InsightBridge Beratungsleistungen",
        "share_label": "Zusammenfassung teilen:",
        "license": "Lizenz: freie Wiederveröffentlichung unter Beibehaltung der Autorenzeile „Dr. Tong Yin, Founder & CEO, InsightBridge Global LLC“ und des Originallinks; Veröffentlichungsmeldung innerhalb von 7 Tagen an Editor@intelligence.insightbridge.global.",
    },
    {
        "iso": "fr", "og": "fr_FR", "dir": "ltr",
        "title": "2027 · IA × Hôtellerie et Tourisme Mondial",
        "desc": "Le livre blanc stratégique 2027 d'InsightBridge Global : la restructuration du tourisme à travers l'Agent Layer, le Physical Layer et le Sovereignty Layer. Les prévisions Vision 2030 vérifiées par les données de marché.",
        "h1": "2027 · IA × Hôtellerie et Tourisme Mondial",
        "p1": "2027 ne sera pas retenu comme l'année où l'IA « est entrée » dans l'hôtellerie — elle y est déjà. Ce sera l'année où l'hôtel s'est scindé en trois couches qui ne se recomposent plus : l'Agent Layer qui vend les chambres, le Physical Layer qui exploite le bâtiment, et le Sovereignty Layer qui décide quels projets seront construits et lesquels seront reportés.",
        "p2": "Les prévisions d'InsightBridge Global sur la Vision 2030 saoudienne (mai–juillet 2026) ont été validées par les données officielles en 4 à 8 semaines : réduction des giga-projets, compression des marges ultra-luxe du PIF, reports séquencés des ouvertures phares. En bref : la fin de l'ère du grand récit, le début de l'ère de la couverture stratégique.",
        "cta_wp": "↓ Télécharger le livre blanc (34 p · EN/ZH)",
        "cta_vision": "↓ Vision 2030 — Prévisions vs Réalité (bilingue)",
        "cta_services": "→ Services de conseil InsightBridge",
        "share_label": "Partager ce résumé :",
        "license": "Licence : libre republication avec mention obligatoire de « Dr. Tong Yin, Founder & CEO, InsightBridge Global LLC » et du lien source ; notification de publication à envoyer sous 7 jours à Editor@intelligence.insightbridge.global.",
    },
    {
        "iso": "es", "og": "es_ES", "dir": "ltr",
        "title": "2027 · IA × Hospitalidad y Turismo Global",
        "desc": "El libro blanco estratégico 2027 de InsightBridge Global: reconfiguración del turismo mediante Agent Layer, Physical Layer y Sovereignty Layer. Los pronósticos de Vision 2030 verificados con datos de mercado.",
        "h1": "2027 · IA × Hospitalidad y Turismo Global",
        "p1": "2027 no será recordado como el año en que la IA «entró» en la hotelería — ya está dentro. Será recordado como el año en que el hotel se dividió en tres capas que ya no se recomponen: la Agent Layer que vende habitaciones, la Physical Layer que opera el edificio y la Sovereignty Layer que decide qué proyectos se construyen y cuáles se aplazan.",
        "p2": "Los pronósticos de InsightBridge Global sobre la Visión 2030 saudí (mayo–julio 2026) se verificaron con datos oficiales en 4–8 semanas: recortes en gigaproyectos, compresión de márgenes ultra-lujo del PIF, aplazamientos escalonados de aperturas emblemáticas. En síntesis: termina la era del gran relato, comienza la del hedging estratégico.",
        "cta_wp": "↓ Descargar el libro blanco (34 pp · EN/ZH)",
        "cta_vision": "↓ Vision 2030 — Pronósticos vs Realidad (bilingüe)",
        "cta_services": "→ Servicios de consultoría InsightBridge",
        "share_label": "Compartir este resumen:",
        "license": "Licencia: libre republicación conservando la firma «Dr. Tong Yin, Founder & CEO, InsightBridge Global LLC» y el enlace original; notificación de publicación dentro de 7 días a Editor@intelligence.insightbridge.global.",
    },
]

ALL_ISO = [x["iso"] for x in LANGS]  # ["ar","ru","ko",...]

# ─── Regional share-bar (button order matches local platform preference) ───
def share_bar(iso, page_url, title):
    """Return list of (label, href) tuples in region-appropriate order."""
    u = quote(page_url, safe="")
    t = quote(title, safe="")
    B = {
        "X":         f"https://twitter.com/intent/tweet?url={u}&text={t}",
        "WhatsApp":  f"https://api.whatsapp.com/send?text={t}%20{u}",
        "LinkedIn":  f"https://www.linkedin.com/sharing/share-offsite/?url={u}",
        "Facebook":  f"https://www.facebook.com/sharer/sharer.php?u={u}",
        "Telegram":  f"https://t.me/share/url?url={u}&text={t}",
        "VK":        f"https://vk.com/share.php?url={u}&title={t}",
        "Weibo":     f"https://service.weibo.com/share/share.php?url={u}&title={t}",
        "LINE":      f"https://social-plugins.line.me/lineit/share?url={u}",
        "Messenger": f"https://www.facebook.com/dialog/send?link={u}&app_id=966242223397117&redirect_uri={u}",
        "Copy Link": f"javascript:void(navigator.clipboard.writeText('{page_url}')||alert('Link copied'))",
    }
    order = {
        "ar": ["WhatsApp", "X",         "LinkedIn", "Telegram"],
        "ru": ["VK",       "Telegram",  "X",        "LinkedIn"],
        "ko": ["LINE",     "X",         "LinkedIn", "Copy Link"],
        "id": ["WhatsApp", "Facebook",  "X",        "LinkedIn"],
        "tr": ["WhatsApp", "X",         "Facebook", "LinkedIn"],
        "vi": ["Facebook", "Messenger", "X",        "LinkedIn"],
        "zh": ["Weibo",    "Copy Link", "LinkedIn", "X"],
        "de": ["X",        "LinkedIn",  "WhatsApp", "Facebook"],
        "fr": ["X",        "LinkedIn",  "WhatsApp", "Facebook"],
        "es": ["WhatsApp", "X",         "Facebook", "LinkedIn"],
    }[iso]
    return [(k, B[k]) for k in order]


def hreflang_matrix(current_iso):
    """Full 10-language cross-matrix + x-default for a given press-kit page."""
    tags = []
    for iso in ALL_ISO:
        hl = "zh-CN" if iso == "zh" else iso
        tags.append(f'<link rel="alternate" hreflang="{hl}" href="{BASE}/press-kit/{iso}.html">')
    tags.append(f'<link rel="alternate" hreflang="x-default" href="{CANONICAL_ARTICLE}">')
    return "\n".join(tags)


IMG_PROTECT = """<!-- ib-image-protect · casual right-click / drag-save / iOS long-press guard -->
<script id="ib-image-protect">
(function(){function isImg(t){return t&&t.tagName==='IMG';}function block(e){if(isImg(e.target)){e.preventDefault();return false;}}document.addEventListener('contextmenu',block,true);document.addEventListener('dragstart',block,true);})();
</script>
<style id="ib-image-protect-css">
img{-webkit-touch-callout:none!important;-webkit-user-drag:none!important;-moz-user-drag:none!important;-o-user-drag:none!important;user-drag:none!important;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;}
</style>"""


CSS = """<style>
:root{--ink:#15171c;--muted:#5c6270;--brand:#7A1F2B;--gold:#DAA54E;--navy:#0A192F;--bg:#FFFDF7;--card:#fff;--rule:rgba(10,25,47,.14);}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:Georgia,'Times New Roman',serif;line-height:1.65;font-size:17px;}
.wrap{max-width:780px;margin:0 auto;padding:56px 22px 88px;}
.eyebrow{font:800 11px/1 'Helvetica',sans-serif;letter-spacing:.22em;text-transform:uppercase;color:var(--brand);margin:0 0 14px}
h1{font-family:'Fraunces','Playfair Display',Georgia,serif;font-weight:700;font-size:clamp(1.85rem,4.2vw,2.7rem);line-height:1.15;letter-spacing:-.012em;margin:0 0 30px;color:var(--navy);}
p{margin:0 0 22px;color:var(--ink);}
p em{color:var(--muted);font-style:italic}
.byline{font-size:14px;color:var(--muted);margin:-14px 0 34px;font-family:'Helvetica',sans-serif;}
.byline a{color:var(--brand);text-decoration:none;border-bottom:1px solid rgba(122,31,43,.35);}
.cta-block{display:flex;flex-direction:column;gap:10px;margin:34px 0 40px;padding:22px 24px;background:var(--card);border:1px solid var(--rule);border-left:4px solid var(--gold);border-radius:6px;}
.cta-block a{color:var(--navy);text-decoration:none;font-family:'Helvetica',sans-serif;font-size:14.5px;font-weight:600;letter-spacing:.01em;transition:color .15s}
.cta-block a:hover{color:var(--brand);}
.share-bar{display:flex;flex-wrap:wrap;gap:8px;margin:32px 0 40px;padding-top:26px;border-top:1px solid var(--rule);}
.share-bar__label{width:100%;font-family:'Helvetica',sans-serif;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:700;margin:0 0 8px;}
.share-bar a{flex:1 1 130px;text-align:center;padding:11px 14px;background:var(--navy);color:#fff;text-decoration:none;font-family:'Helvetica',sans-serif;font-size:13px;font-weight:600;letter-spacing:.03em;border-radius:3px;transition:background .15s,transform .1s;}
.share-bar a:hover{background:var(--brand);transform:translateY(-1px);}
footer{margin-top:56px;padding-top:24px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--muted);font-family:'Helvetica',sans-serif;line-height:1.65;}
footer p{margin:0 0 8px;color:var(--muted);}
footer a{color:var(--brand);text-decoration:none;}
[dir="rtl"] .share-bar{direction:rtl}
[dir="rtl"] h1,[dir="rtl"] p,[dir="rtl"] .cta-block{text-align:right}
[dir="rtl"] .cta-block{border-left:none;border-right:4px solid var(--gold);}
@media (max-width:640px){.wrap{padding:40px 18px 60px;}h1{font-size:1.6rem;}}
</style>"""


def build_page(L):
    iso = L["iso"]
    url = f"{BASE}/press-kit/{iso}.html"
    hreflang = hreflang_matrix(iso)
    shares = share_bar(iso, url, L["title"])
    share_html = "\n    ".join(
        f'<a href="{href}" target="_blank" rel="noopener nofollow" data-testid="share-{iso}-{label.lower().replace(" ","-")}">{label}</a>'
        for label, href in shares
    )
    schema = f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": {L['title']!r},
  "inLanguage": "{iso}",
  "isBasedOn": "{WHITEPAPER_PDF}",
  "translationOfWork": {{
    "@type": "Article",
    "name": "2027 AI × Global Hospitality & Tourism Whitepaper",
    "url": "{CANONICAL_ARTICLE}",
    "inLanguage": ["en", "zh"]
  }},
  "author": {{
    "@type": "Person",
    "name": "Dr. Tong Yin",
    "jobTitle": "Founder & CEO",
    "worksFor": {{"@type": "Organization", "name": "InsightBridge Global LLC"}},
    "alumniOf": [
      {{"@type": "EducationalOrganization", "name": "Auburn University", "award": "Ph.D."}},
      {{"@type": "EducationalOrganization", "name": "Eastern Illinois University", "award": "MBA"}}
    ]
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "InsightBridge Global LLC",
    "url": "{BASE}"
  }},
  "datePublished": "2026-07-17",
  "license": "{BASE}/press-kit/",
  "isAccessibleForFree": true
}}
</script>""".replace("'", '"')

    html = f"""<!doctype html>
<html lang="{iso}" dir="{L['dir']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{L['title']} — Dr. Tong Yin · InsightBridge Global</title>
<meta name="description" content="{L['desc']}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<meta name="author" content="Dr. Tong Yin, InsightBridge Global LLC">
<meta name="publisher" content="InsightBridge Global LLC">
<meta name="keywords" content="AI, Hospitality, Tourism, Vision 2030, Agent Layer, Physical Layer, Sovereignty Layer, InsightBridge, Tong Yin">

<meta property="og:type" content="article">
<meta property="og:title" content="{L['title']}">
<meta property="og:description" content="{L['desc']}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="{L['og']}">
<meta property="og:site_name" content="InsightBridge Global">
<meta property="og:image" content="{BASE}/assets/hero-main.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{L['title']}">
<meta name="twitter:description" content="{L['desc']}">
<meta name="twitter:image" content="{BASE}/assets/hero-main.jpg">

<link rel="canonical" href="{url}">
{hreflang}

{schema}
{IMG_PROTECT}
{CSS}
</head>
<body data-testid="press-kit-{iso}">
<div class="wrap">
  <p class="eyebrow">◇ InsightBridge Global · Regional Reprint Kit · {iso.upper()}</p>
  <h1>{L['h1']}</h1>
  <p class="byline">Dr. Tong Yin · Founder &amp; CEO, <a href="{BASE}">InsightBridge Global LLC</a> · Auburn, Alabama, USA · 2026-07-17</p>

  <p>{L['p1']}</p>
  <p>{L['p2']}</p>

  <div class="cta-block" data-testid="cta-block">
    <a href="{WHITEPAPER_PDF}" target="_blank" rel="noopener" data-testid="cta-whitepaper">{L['cta_wp']}</a>
    <a href="{VISION_PDF}" target="_blank" rel="noopener" data-testid="cta-vision-pdf">{L['cta_vision']}</a>
    <a href="{SERVICES_URL}" data-testid="cta-services">{L['cta_services']}</a>
  </div>

  <div class="share-bar" data-testid="share-bar-{iso}">
    <p class="share-bar__label">{L['share_label']}</p>
    {share_html}
  </div>

  <footer>
    <p><strong>License:</strong> {L['license']}</p>
    <p><strong>Publisher:</strong> InsightBridge Global LLC · 1001 N Donahue Dr, E2, Auburn, AL 36832, USA · D-U-N-S ® 14-455-6174 · <a href="{BASE}">insightbridge.global</a></p>
    <p><strong>Editor:</strong> <a href="mailto:Editor@intelligence.insightbridge.global">Editor@intelligence.insightbridge.global</a></p>
  </footer>
</div>
</body>
</html>
"""
    return html


def main():
    for L in LANGS:
        out = OUT / f"{L['iso']}.html"
        out.write_text(build_page(L), encoding="utf-8")
        print(f"OK  {out.relative_to(OUT.parent.parent.parent)}  ({len(out.read_text())} bytes)")

if __name__ == "__main__":
    main()
