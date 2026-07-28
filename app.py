from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import streamlit as st
import tensorflow as tf
import numpy as np
import json
import cv2
import re
from PIL import Image
import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# PROJECT PATHS & CONFIGURATION
# ─────────────────────────────────────────────
from modules.evidence_knowledge_base import (
    DISEASE_INFO as EVIDENCE_DISEASE_INFO,
    REFERENCES as EVIDENCE_REFERENCES,
    GENERAL_DISCLAIMER,
    get_items as get_evidence_items,
    get_weather_advice as get_evidence_weather_advice,
)

from modules.report_pdf import (
    build_disease_report,
    build_ripeness_report,
)

from config import (
    ASSETS_DIR,
    MODELS_DIR,
    LOGO_PATH,
    TITLE_PATH,
    BACKGROUND_PATH,
    CSS_PATH,
    OPENWEATHER_API_KEY,
)
from modules.ui import apply_theme

WEATHER_API_KEY = OPENWEATHER_API_KEY

st.set_page_config(
    page_title="BananaChain AI",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🍌",
    layout="wide",
    initial_sidebar_state="expanded",
)

def get_weather(city="Kuala Lumpur"):
    try:
        from urllib.parse import quote
        if not WEATHER_API_KEY:
            st.warning("OpenWeather API key is missing. Add OPENWEATHER_API_KEY to .streamlit/secrets.toml or Streamlit Cloud Secrets.")
            return None
        city_encoded = quote(city.strip())
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city_encoded},MY&appid={WEATHER_API_KEY}&units=metric"
        r = requests.get(url, timeout=5)
        data = r.json()
        if r.status_code == 200:
            return {
                'temp': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'],
                'city': data['name'],
                'icon': data['weather'][0]['icon'],
                'rain': 'rain' in data.get('weather', [{}])[0].get('main', '').lower()
            }
        else:
            st.warning(f"Weather API error: {data.get('message', 'Unknown error')}. Check your API key or city name.")
    except Exception as e:
        st.warning(f"Could not fetch weather: {e}")
    return None


REFERENCES = {
    'healthy': [
        {'short': 'FAO — Quality declared planting material: protocols and standards for vegetatively propagated crops', 'url': 'https://www.fao.org/4/i1195e/i1195e00.htm'},
    ],
    'black sigatoka': [
        {'short': 'ProMusa — Black leaf streak: integrated management, deleafing and fungicide use', 'url': 'https://www.promusa.org/Black%2Bleaf%2Bstreak'},
        {'short': 'FRAC Banana Working Group — fungicide resistance-management guidelines', 'url': 'https://www.frac.info/frac-teams/working-groups/banana-group/'},
        {'short': 'Jacome & Schuh (1992) — leaf wetness and temperature effects on black Sigatoka', 'url': 'https://doi.org/10.1094/Phyto-82-515'},
    ],
    'yellow sigatoka': [
        {'short': 'ProMusa — Sigatoka leaf spot: monitoring and chemical-control principles', 'url': 'https://www.promusa.org/Sigatoka%2Bleaf%2Bspot'},
        {'short': 'ProMusa — Biological forecasting system for Sigatoka leaf spot', 'url': 'https://www.promusa.org/Biological%2Bforecasting%2Bsystem%2Bfor%2BSigatoka%2Bleaf%2Bspot'},
        {'short': 'FRAC Banana Working Group — fungicide resistance-management guidelines', 'url': 'https://www.frac.info/frac-teams/working-groups/banana-group/'},
    ],
    'fusarium wilt': [
        {'short': 'ProMusa — Fusarium wilt of banana: soil-borne spread and management', 'url': 'https://www.promusa.org/Fusarium%2Bwilt'},
        {'short': 'ProMusa — Tropical race 4: fungicides do not control TR4', 'url': 'https://www.promusa.org/Tropical%2Brace%2B4%2B-%2BTR4'},
        {'short': 'FAO TR4 Global Network — official Fusarium wilt publications and technical manuals', 'url': 'https://www.fao.org/tr4gn/fao-in-action/fao-publications/en/'},
    ],
    'banana moko disease': [
        {'short': 'EPPO Global Database — Ralstonia solanacearum species complex datasheet', 'url': 'https://gd.eppo.int/taxon/RALSSO/datasheet'},
        {'short': 'IPPC — phytosanitary measures for banana pests including Moko disease', 'url': 'https://www.ippc.int/en/news/technical-panel-on-commodity-standards-advances-international-standards-for-citrus-banana-and-taro-trade/'},
        {'short': 'CAHFSA — Moko disease of bananas fact sheet', 'url': 'https://cahfsa.org/wp-content/uploads/2022/09/Moko-disease-of-bananas.pdf'},
    ],
    'cordana': [
        {'short': 'ProMusa — Cordana leaf spot', 'url': 'https://www.promusa.org/Cordana%2Bleaf%2Bspot'},
        {'short': 'CABI Compendium — Musa crop datasheet (includes Neocordana musae)', 'url': 'https://www.cabi.org/isc/datasheet/35127'},
    ],
    'ripeness_storage': [
        {'short': 'UC Davis Postharvest Center — Banana (Cavendish): 13–14°C transport/storage; 15–20°C ripening', 'url': 'https://postharvest.ucdavis.edu/produce-facts-sheets/banana'},
        {'short': 'FAO — Storage of horticultural crops and chilling-sensitive commodities', 'url': 'https://www.fao.org/4/x5403e/x5403e09.htm'},
        {'short': 'UC Davis Postharvest Center — banana ripening temperature guidance', 'url': 'https://postharvest.ucdavis.edu/ask-produce-docs/do-bananas-respond-ethylene-when-they-are-below-16-deg-c'},
    ],
    'market_price': [
        {'short': 'KPDN PriceCatcher / ManaMurah — observed retail price data; not a guaranteed selling price', 'url': 'https://manamurah.com/'},
    ],
}

def _collect_reference_sources(value):
    """Recursively collect source dictionaries from local and audited reference stores."""
    collected = []
    if isinstance(value, dict):
        if value.get("url") and (value.get("short") or value.get("title") or value.get("apa")):
            collected.append(value)
        else:
            for child in value.values():
                collected.extend(_collect_reference_sources(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            collected.extend(_collect_reference_sources(child))
    return collected


def _deduplicate_sources(sources):
    ordered = []
    seen = set()
    for source in sources:
        sid = source.get("url") or source.get("apa") or str(source)
        if sid not in seen:
            seen.add(sid)
            ordered.append(source)
    return ordered


ALL_REFERENCE_SOURCES = _deduplicate_sources(
    _collect_reference_sources(REFERENCES) + _collect_reference_sources(EVIDENCE_REFERENCES)
)
GLOBAL_REFERENCE_NUMBERS = {
    (source.get("url") or f"{source.get('organisation','')}|{source.get('title','')}"): index
    for index, source in enumerate(ALL_REFERENCE_SOURCES, start=1)
}


def clean_display_text(text):
    """Remove decorative emoji while preserving normal punctuation and citation text."""
    if not isinstance(text, str):
        return text
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002700-\U000027BF"
        "\U00002600-\U000026FF"
        "]+",
        flags=re.UNICODE,
    )
    return re.sub(r"\s{2,}", " ", emoji_pattern.sub("", text)).strip()


SOURCE_TITLES = {
    'EN': 'Evidence Sources',
    'BM': 'Sumber Bukti',
    'ZH': '证据来源',
}

EVIDENCE_NOTE = {
    'EN': 'Recommendations are general decision-support information. Follow registered product labels and local Department of Agriculture instructions.',
    'BM': 'Cadangan ialah maklumat sokongan keputusan umum. Ikuti label produk berdaftar dan arahan Jabatan Pertanian tempatan.',
    'ZH': '建议仅用于一般决策支持。农药与检疫措施须遵循当地农业部门及已登记产品标签。',
}

DISCLAIMER = {
    'disease': {
        'EN': 'This AI prediction is for decision support only and is not a confirmed diagnosis.',
        'BM': 'Ramalan AI ini hanya untuk sokongan keputusan dan bukan diagnosis yang disahkan.',
        'ZH': '此AI预测仅用于决策支持，不代表正式确诊。',
    },
    'weather': {
        'EN': 'Weather advice uses current API data and published guidance; actual field conditions may differ.',
        'BM': 'Nasihat cuaca menggunakan data API semasa dan panduan diterbitkan; keadaan sebenar di ladang mungkin berbeza.',
        'ZH': '天气建议依据当前API数据与已发布指南；实际田间条件可能不同。',
    },
    'ripeness': {
        'EN': 'AI recommendations are for decision support only. Actual fruit quality and market suitability may vary.',
        'BM': 'Cadangan AI hanya untuk sokongan keputusan. Kualiti buah dan kesesuaian pasaran sebenar mungkin berbeza.',
        'ZH': 'AI建议仅用于决策支持；实际果实品质与市场适用性可能不同。',
    },
}

CONFIDENCE_NOTE = {
    'EN': 'Confidence reflects the model’s certainty, not the actual probability that the diagnosis is correct.',
    'BM': 'Nilai keyakinan menunjukkan kepastian model, bukan kebarangkalian sebenar bahawa diagnosis itu betul.',
    'ZH': '置信度表示模型对预测的把握，并不等于诊断正确的实际概率。',
}



def _apa_reference(source):
    """Return a clean APA-style web reference for a source record."""
    if source.get("apa"):
        return source["apa"]
    organisation = source.get("organisation") or source.get("author") or source.get("short", "Source").split(" — ")[0]
    title = source.get("title") or source.get("short", "Untitled source").split(" — ")[-1]
    year = source.get("year", "n.d.")
    return f"{organisation}. ({year}). *{title}*. {source.get('url', '')}"


def _source_identity(source):
    return source.get("url") or f"{source.get('organisation','')}|{source.get('title','')}"


def _build_reference_index(entries):
    """Assign stable citation numbers in first-use order."""
    ordered = []
    number_by_id = {}
    for entry in entries:
        for source in entry.get("sources", []):
            sid = _source_identity(source)
            if sid not in number_by_id:
                number_by_id[sid] = len(ordered) + 1
                ordered.append(source)
    return ordered, number_by_id


def _citation_badges(sources, number_by_id):
    numbers = [number_by_id[_source_identity(source)] for source in sources if _source_identity(source) in number_by_id]
    return " ".join(f"<sup class='citation-badge'>[{number}]</sup>" for number in numbers)


def render_reference_list(sources, lang, title=None):
    labels = {
        "EN": "Reference List (APA Style)",
        "BM": "Senarai Rujukan (Gaya APA)",
        "ZH": "参考文献（APA格式）",
    }
    with st.expander(title or labels[lang], expanded=False):
        for idx, source in enumerate(sources, start=1):
            st.markdown(f"**[{idx}]** {_apa_reference(source)}")
        st.caption(EVIDENCE_NOTE[lang])

def render_sources(source_key, lang):
    """Display user-visible evidence sources for a recommendation section."""
    sources = REFERENCES.get(source_key, [])
    if not sources:
        return
    with st.expander(SOURCE_TITLES[lang], expanded=False):
        for idx, source in enumerate(sources, start=1):
            st.markdown(f"{idx}. [{source['short']}]({source['url']})")
        st.caption(EVIDENCE_NOTE[lang])



def get_weather_advice(weather, disease_name, lang):
    if not weather:
        return None

    humidity = weather['humidity']
    rain = weather['rain']
    temp = weather['temp']
    desc = weather['description'].lower()
    cloudy = any(w in desc for w in ['cloud', 'overcast', 'mist', 'fog', 'haze'])

    advice = {'EN': [], 'BM': [], 'ZH': []}

    # Normalise disease name (handle both 'black sigatoka' and 'black_sigatoka')
    dn = disease_name.replace('_', ' ').lower().strip()

    # ── HEALTHY ──────────────────────────────────────────────
    if dn == 'healthy':
        if humidity > 80 and rain:
            advice['EN'].append("🌧️ Heavy rain + high humidity today. Even though your plant is healthy, these are ideal conditions for fungal infection to begin. Inspect leaves closely every 2–3 days this week.")
            advice['BM'].append("🌧️ Hujan lebat + kelembapan tinggi hari ini. Walaupun pokok anda sihat, ini adalah keadaan ideal untuk jangkitan kulat bermula. Periksa daun dengan teliti setiap 2–3 hari minggu ini.")
            advice['ZH'].append("🌧️ 今日大雨且湿度高。即使植株健康，这是真菌感染开始的理想条件。本周每2-3天仔细检查叶片。")
        elif humidity > 80:
            advice['EN'].append(f"Humidity: Humidity is very high today at {humidity}%. Your plant is healthy but fungal spores thrive in these conditions. Increase inspection and keep foliage as dry and well-ventilated as practical. Use a registered preventive treatment only when recommended by a local crop adviser and the product label.")
            advice['BM'].append(f"Humidity: Kelembapan sangat tinggi hari ini pada {humidity}%. Pokok anda sihat tetapi spora kulat berkembang dalam keadaan ini. Tingkatkan pemeriksaan dan pastikan kanopi kering serta berpengudaraan baik. Gunakan rawatan pencegahan berdaftar hanya mengikut nasihat pegawai pertanian dan label produk.")
            advice['ZH'].append(f"Humidity: 今日湿度非常高，达{humidity}%。植株虽健康，但真菌孢子在此条件下大量繁殖。加强检查，并尽量保持叶片干燥和通风。仅在当地农业顾问及登记产品标签建议下使用预防性药剂。")
        elif temp > 32 and not rain:
            advice['EN'].append(f"☀️ Hot and dry today ({temp}°C). Low disease risk. Ensure adequate irrigation — heat stress weakens plant immunity over time.")
            advice['BM'].append(f"☀️ Panas dan kering hari ini ({temp}°C). Risiko penyakit rendah. Pastikan pengairan mencukupi — tekanan haba melemahkan imuniti pokok.")
            advice['ZH'].append(f"☀️ 今日炎热干燥（{temp}°C）。病害风险低。确保充分灌溉——持续热应激会削弱植株免疫力。")
        else:
            advice['EN'].append("✅ Weather conditions are currently low-risk for disease. Maintain your regular weekly inspection schedule.")
            advice['BM'].append("✅ Keadaan cuaca kini berisiko rendah untuk penyakit. Kekalkan jadual pemeriksaan mingguan anda.")
            advice['ZH'].append("✅ 当前天气条件病害风险低。保持您的每周定期检查计划。")

    # ── BLACK SIGATOKA ────────────────────────────────────────
    # Humidity >80% / rain-splash spread: see REFERENCES['black_sigatoka']
    elif dn == 'black sigatoka':
        if rain:
            advice['EN'].append("🚨 URGENT: It is raining now — Black Sigatoka spores are actively spreading via water droplets at this moment. Do NOT spray fungicide. Prioritise removing infected leaves immediately before more spores spread.")
            advice['BM'].append("🚨 MENDESAK: Sedang hujan — spora Sigatoka Hitam sedang merebak melalui titisan air sekarang. JANGAN sembur fungisid. Utamakan penyingkiran daun yang dijangkiti segera.")
            advice['ZH'].append("🚨 紧急：正在下雨——黑条叶斑病孢子正通过水滴积极传播。切勿喷洒杀菌剂。立即优先移除感染叶片，防止更多孢子扩散。")
        elif humidity > 80:
            advice['EN'].append(f"Humidity is {humidity}% — critically high for Black Sigatoka. High humidity and leaf wetness favour disease development. Avoid spraying during rain; use only a locally registered product according to its label and resistance-management guidance.")
            advice['BM'].append(f"Kelembapan {humidity}% — sangat kritikal untuk Sigatoka Hitam. Kelembapan tinggi dan daun basah menggalakkan perkembangan penyakit. Elakkan semburan ketika hujan; gunakan hanya produk berdaftar mengikut label dan panduan pengurusan rintangan.")
            advice['ZH'].append(f"湿度{humidity}%——对黑条叶斑病极为危险。高湿度和叶面湿润有利于病害发展。避免雨中施药；仅按登记产品标签和抗药性管理指南使用药剂。")
        elif cloudy and not rain:
            advice['EN'].append("🌥️ Overcast/cloudy today — no direct sun means fungicide evaporates slower and stays effective longer. Dry, low-wind conditions may be more suitable than rain, but spray only when the registered product label and local forecast allow it.")
            advice['BM'].append("🌥️ Berawan hari ini — tiada cahaya matahari terus bermakna fungisid meruap lebih perlahan dan kekal berkesan lebih lama. Keadaan kering dan kurang angin mungkin lebih sesuai berbanding hujan, tetapi sembur hanya apabila label produk berdaftar dan ramalan tempatan membenarkannya.")
            advice['ZH'].append("🌥️ 今日阴天——无直射阳光意味着杀菌剂蒸发更慢、药效更持久。干燥、低风速通常比雨天更适合施药，但必须同时符合登记产品标签和当地天气预报。")
        elif temp > 32:
            advice['EN'].append(f"Temperature: Temperature is {temp}°C — too hot to spray now. Fungicide will evaporate before taking effect. Wait for cooler, dry, low-wind conditions and follow the registered product label.")
            advice['BM'].append(f"Temperature: Suhu {temp}°C — terlalu panas untuk sembur sekarang. Fungisid akan sejat sebelum berkesan. Tunggu keadaan yang lebih sejuk, kering dan kurang angin serta ikut label produk berdaftar.")
            advice['ZH'].append(f"Temperature: 气温{temp}°C——现在喷药太热。杀菌剂会在发挥效果前蒸发。等待较凉爽、干燥且低风速的条件，并遵循登记产品标签。")
        else:
            advice['EN'].append("☀️ Good weather for treatment today. Where chemical control is justified, apply a locally registered fungicide under suitable dry, low-wind conditions and follow FRAC resistance-management guidance.")
            advice['BM'].append("☀️ Cuaca baik untuk rawatan hari ini. Jika kawalan kimia diperlukan, gunakan fungisid berdaftar tempatan dalam keadaan kering dan kurang angin serta ikuti panduan pengurusan rintangan FRAC.")
            advice['ZH'].append("☀️ 今日天气适合防治。如确需化学防治，应在干燥、低风速条件下使用当地登记杀菌剂，并遵循FRAC抗药性管理指南。")

    # ── YELLOW SIGATOKA ───────────────────────────────────────
    # Water-borne spread, less aggressive than black sigatoka: see REFERENCES['yellow_sigatoka']
    elif dn == 'yellow sigatoka':
        if rain:
            advice['EN'].append("🌧️ Raining now — do NOT spray. Yellow Sigatoka spores also spread through water. Focus on removing spotted leaves today instead.")
            advice['BM'].append("🌧️ Sedang hujan — JANGAN sembur. Spora Sigatoka Kuning juga merebak melalui air. Fokus pada penyingkiran daun berbintik hari ini.")
            advice['ZH'].append("🌧️ 正在下雨——请勿喷药。黄条叶斑病孢子也通过水传播。今天专注于移除有斑点的叶片。")
        elif humidity > 80:
            advice['EN'].append(f"Humidity: Humidity at {humidity}% is accelerating Yellow Sigatoka spread. Less aggressive than Black Sigatoka but still needs treatment soon. Plan treatment when conditions are dry, using only registered products according to the label and local advice.")
            advice['BM'].append(f"Humidity: Kelembapan {humidity}% mempercepatkan penyebaran Sigatoka Kuning. Kurang agresif daripada Sigatoka Hitam tetapi masih perlu rawatan segera. Rancang rawatan apabila cuaca kering, menggunakan hanya produk berdaftar mengikut label dan nasihat tempatan.")
            advice['ZH'].append(f"Humidity: 湿度{humidity}%正在加速黄条叶斑病扩散。虽不如黑条叶斑病严重，但仍需尽快治疗。在天气干燥时安排处理，仅依照登记产品标签和当地建议使用药剂。")
        elif cloudy and not rain:
            advice['EN'].append("🌥️ Cloudy but dry — suitable for spraying. No direct sun means better fungicide absorption. Good time to treat Yellow Sigatoka today.")
            advice['BM'].append("🌥️ Berawan tetapi kering — sesuai untuk semburan. Tiada cahaya matahari terus bermakna penyerapan fungisid yang lebih baik. Masa yang baik untuk rawatan Sigatoka Kuning hari ini.")
            advice['ZH'].append("🌥️ 阴天但干燥——适合喷药。无直射阳光意味着杀菌剂吸收更好。今天是防治黄条叶斑病的好时机。")
        else:
            advice['EN'].append("☀️ Weather is suitable for Yellow Sigatoka treatment. If fungicide treatment is needed, select a locally registered product and follow its label and resistance-management programme.")
            advice['BM'].append("☀️ Cuaca sesuai untuk rawatan Sigatoka Kuning. Jika rawatan fungisid diperlukan, pilih produk berdaftar tempatan dan ikuti label serta program pengurusan rintangan.")
            advice['ZH'].append("☀️ 天气适合防治黄条叶斑病。如需杀菌剂处理，应选择当地登记产品，并遵循标签和抗药性管理方案。")

    # ── FUSARIUM WILT ─────────────────────────────────────────
    # Soil-borne, leaf-spray ineffective: see REFERENCES['fusarium_wilt']
    elif dn == 'fusarium wilt':
        if rain:
            advice['EN'].append("🌧️ It is raining. Important: Fusarium Wilt is a SOIL-BORNE fungus — spraying leaves will NOT help. Rainwater runoff can spread it to nearby plants via soil. Block water flow between plants if possible.")
            advice['BM'].append("🌧️ Sedang hujan. Penting: Fusarium Wilt adalah kulat BAWAH TANAH — semburan daun TIDAK akan membantu. Aliran air hujan boleh menyebarkannya ke pokok berdekatan melalui tanah. Halang aliran air antara pokok jika boleh.")
            advice['ZH'].append("🌧️ 正在下雨。重要：镰刀菌枯萎病是土传真菌——叶面喷药无济于事。雨水径流可能通过土壤传播到附近植株。尽可能阻止植株间的水流。")
        elif humidity > 80:
            advice['EN'].append(f"Humidity: Humidity is {humidity}%. For Fusarium Wilt, humidity does NOT affect treatment — the fungus lives in the soil, not the air. Focus on soil treatment and removing the infected plant, not spraying leaves.")
            advice['BM'].append(f"Humidity: Kelembapan {humidity}%. Untuk Fusarium Wilt, kelembapan TIDAK mempengaruhi rawatan — kulat hidup dalam tanah, bukan udara. Fokus pada rawatan tanah dan penyingkiran pokok yang dijangkiti.")
            advice['ZH'].append(f"Humidity: 湿度{humidity}%。对于镰刀菌枯萎病，湿度不影响治疗——真菌生活在土壤中，而非空气中。专注于土壤处理和移除感染植株。")
        else:
            advice['EN'].append("Weather does NOT affect Fusarium Wilt treatment. This is a soil-borne disease — fungicide sprays on leaves are useless. Focus entirely on removing the infected plant and preventing movement of contaminated soil, water, tools and planting material, and obtaining official diagnostic advice.")
            advice['BM'].append("Cuaca TIDAK mempengaruhi rawatan Fusarium Wilt. Ini adalah penyakit bawah tanah — semburan fungisid pada daun adalah sia-sia. Fokus sepenuhnya pada penyingkiran pokok yang dijangkiti dan mencegah pergerakan tanah, air, alatan dan bahan tanaman tercemar serta mendapatkan nasihat diagnosis rasmi.")
            advice['ZH'].append("天气对镰刀菌枯萎病治疗没有影响。这是土传病害——叶面喷药无效。完全专注于移除感染植株并防止受污染土壤、水、工具和种植材料移动，并寻求官方诊断建议。")

    # ── BANANA MOKO DISEASE ───────────────────────────────────
    # Insect/tool/soil-water transmission, warm temp -> more insect activity:
    # see REFERENCES['moko']. NOTE: the "rain reduces insect activity, slows
    # spread" line is a reasonable general entomological inference, not
    # directly stated in the sources above — flagged here for transparency.
    elif dn == 'banana moko disease':
        if rain:
            advice['EN'].append("🌧️ Raining now. Moko Disease is spread by insects — rain temporarily reduces insect activity, slightly slowing spread. However, rainwater runoff through soil can still carry bacteria between plants. Maintain quarantine zone strictly.")
            advice['BM'].append("🌧️ Sedang hujan. Penyakit Moko disebarkan oleh serangga — hujan mengurangkan aktiviti serangga buat sementara, sedikit melambatkan penyebaran. Walau bagaimanapun, aliran air hujan melalui tanah masih boleh membawa bakteria. Kekalkan zon kuarantin dengan ketat.")
            advice['ZH'].append("🌧️ 正在下雨。摩哥病由昆虫传播——雨水暂时减少昆虫活动，略微减缓传播。但土壤中的雨水径流仍可在植株间携带细菌。严格维持隔离区。")
        elif temp > 30:
            advice['EN'].append(f"Temperature: Temperature is {temp}°C — warm weather increases insect activity, which ACCELERATES Moko Disease spread between plants via flowers. Cover all cut flower buds with plastic bags immediately and set up insect traps around the quarantine zone.")
            advice['BM'].append(f"Temperature: Suhu {temp}°C — cuaca panas meningkatkan aktiviti serangga, yang MEMPERCEPATKAN penyebaran Penyakit Moko melalui bunga. Tutup semua kuntum bunga yang dipotong dengan beg plastik segera dan pasang perangkap serangga di sekitar zon kuarantin.")
            advice['ZH'].append(f"Temperature: 气温{temp}°C——温暖天气增加昆虫活动，通过花朵在植株间加速摩哥病传播。立即用塑料袋覆盖所有切割花蕾，并在隔离区周围设置捕虫器。")
        elif humidity > 80:
            advice['EN'].append(f"Humidity: High humidity ({humidity}%) promotes insect breeding near your farm. More insects = faster Moko spread. Spray insecticide around the quarantine perimeter — NOT on the infected plant itself.")
            advice['BM'].append(f"Humidity: Kelembapan tinggi ({humidity}%) menggalakkan pembiakan serangga berhampiran ladang. Lebih banyak serangga = penyebaran Moko lebih cepat. Sembur racun serangga di sekitar perimeter kuarantin — BUKAN pada pokok yang dijangkiti.")
            advice['ZH'].append(f"Humidity: 高湿度（{humidity}%）促进农场附近昆虫繁殖。昆虫越多=摩哥病传播越快。在隔离区周边喷洒杀虫剂——而非感染植株本身。")
        else:
            advice['EN'].append("Weather is moderate but Moko Disease requires immediate action regardless of weather. Quarantine and removal cannot wait — act now. Weather only affects insect vector control, not the core treatment.")
            advice['BM'].append("Cuaca sederhana tetapi Penyakit Moko memerlukan tindakan segera tanpa mengira cuaca. Kuarantin dan penyingkiran tidak boleh menunggu — bertindak sekarang.")
            advice['ZH'].append("天气适中，但摩哥病无论天气如何都需要立即采取行动。隔离和移除不能等待天气——立即行动。")

    # ── CORDANA ───────────────────────────────────────────────
    # Rain + hot/humid accelerates spread, wind/splash dispersal: see REFERENCES['cordana']
    elif dn == 'cordana':
        if rain:
            advice['EN'].append("🌧️ Raining now — Cordana Leaf Spot spreads through water splash. Avoid walking through the plantation during rain as your boots can carry spores between plants. Do NOT spray today.")
            advice['BM'].append("🌧️ Sedang hujan — Bintik Daun Cordana merebak melalui percikan air. Elak berjalan melalui ladang semasa hujan kerana but anda boleh membawa spora antara pokok. JANGAN sembur hari ini.")
            advice['ZH'].append("🌧️ 正在下雨——科达纳叶斑病通过水溅传播。下雨时避免在种植园行走，靴子可能在植株间携带孢子。今天不要喷药。")
        elif humidity > 80:
            advice['EN'].append(f"Humidity: Humidity at {humidity}% is high but Cordana is a low-severity disease — no emergency. Improve drainage around affected plants first. Apply copper fungicide this week when weather dries.")
            advice['BM'].append(f"Humidity: Kelembapan {humidity}% adalah tinggi tetapi Cordana adalah penyakit keterukan rendah — tiada kecemasan. Perbaiki saliran di sekitar pokok yang terjejas dahulu. Gunakan fungisid kuprum minggu ini apabila cuaca kering.")
            advice['ZH'].append(f"Humidity: 湿度{humidity}%偏高，但科达纳病严重程度低——无需紧急处理。先改善受影响植株周围的排水，待天气干燥后本周施用铜基杀菌剂。")
        elif cloudy and not rain:
            advice['EN'].append("🌥️ Cloudy and dry — suitable for copper fungicide application if Cordana is spreading. Low urgency, but good weather conditions to treat if you planned to spray this week.")
            advice['BM'].append("🌥️ Berawan dan kering — sesuai untuk penggunaan fungisid kuprum jika Cordana sedang merebak. Keutamaan rendah, tetapi cuaca baik untuk rawatan jika anda merancang untuk membuat semburan minggu ini.")
            advice['ZH'].append("🌥️ 阴天干燥——如科达纳病正在扩散，适合施用铜基杀菌剂。紧迫性低，但如本周计划喷药，天气条件不错。")
        elif temp > 32:
            advice['EN'].append(f"Temperature: Hot today ({temp}°C). Cordana is low-severity — no need to rush spraying in this heat. Wait for cooler weather (below 30°C) or spray early morning tomorrow.")
            advice['BM'].append(f"Temperature: Panas hari ini ({temp}°C). Cordana adalah keterukan rendah — tidak perlu tergesa-gesa membuat semburan dalam panas ini. Tunggu cuaca lebih sejuk (bawah 30°C) atau awal pagi esok.")
            advice['ZH'].append(f"Temperature: 今日炎热（{temp}°C）。科达纳病严重程度低——无需在高温下急于喷药。等待天气凉爽（低于30°C）或明天清晨处理。")
        else:
            advice['EN'].append("☀️ Good weather today. Cordana is low priority — if you choose to spray copper fungicide, early morning is best. Otherwise maintain regular inspections.")
            advice['BM'].append("☀️ Cuaca baik hari ini. Cordana adalah keutamaan rendah — jika anda memilih untuk sembur fungisid kuprum, awal pagi adalah terbaik. Jika tidak, kekalkan pemeriksaan berkala.")
            advice['ZH'].append("☀️ 今日天气良好。科达纳病优先级低——如计划喷洒铜基杀菌剂，清晨最佳。否则保持定期检查即可。")

    return advice

# ─────────────────────────────────────────────
# LANGUAGE CONTENT
# ─────────────────────────────────────────────
LANG_CONTENT = {
    'EN': {
        'app_title': 'BananaChain AI',
        'app_sub': "AI-Powered Banana Disease Detection & Decision Support",
        'mode1_tab': '🌿 Disease Detection',
        'mode2_tab': '📦 Ripeness & Supply Chain',
        'mode1_title': '🌿 Banana Disease Detection',
        'mode1_desc': 'Upload a photo of a banana **leaf** to detect disease and receive step-by-step treatment advice.',
        'upload_leaf': 'Upload Leaf Image',
        'show_gradcam': 'Show Grad-CAM Heatmap',
        'analyse_disease': 'Analyse Disease',
        'analysing': 'Analysing leaf...',
        'upload_prompt': 'Upload a banana leaf image and click **Analyse Disease** to get results.',
        'what_is_it': 'What Is This Disease?',
        'treatment': 'Step-by-Step Treatment',
        'prevention': 'Prevention Tips',
        'monitoring': 'Monitoring Schedule',
        'economic': 'Economic Impact',
        'get_help': 'Get Help',
        'weather_title': '🌤️ Current Weather',
        'spraying_advice': 'Spraying Advice',
        'weather_city': 'Enter your city/district',
        'get_weather_btn': 'Get Weather',
        'ref_images': 'Reference Images',
        'ref_images_desc': 'Compare your leaf with these reference images',
        'your_image': 'Your Image',
        'gradcam_overlay': 'Grad-CAM Overlay',
        'confidence': 'Confidence',
        'severity': 'Severity',
        'probabilities': 'Prediction Probabilities',
        'mode2_title': '📦 Ripeness & Supply Chain Decision',
        'mode2_desc': 'Upload a photo of **banana fruit** to assess ripeness and get supply chain recommendations.',
        'upload_banana': 'Upload Banana Image',
        'user_type': 'I am a...',
        'quantity': 'Estimated Quantity (kg)',
        'variety': 'Banana Variety',
        'analyse_ripeness': 'Analyse Ripeness',
        'analysing_ripeness': 'Analysing ripeness...',
        'upload_prompt2': 'Upload a banana image and click **Analyse Ripeness** to get results.',
        'what_it_means': 'What Does This Mean?',
        'actions': 'Recommended Actions',
        'storage': 'Temperature: Storage & Handling',
        'channels': 'Market Channels',
        'financial': 'Scenario Estimate (Not a Guaranteed Market Value)',
        'full_value': 'Full Market Value',
        'recoverable': 'Recoverable Value',
        'potential_loss': 'Potential Loss',
        'shelf_life': 'Shelf Life',
        'est_value': 'Est. Value',
        'ripeness': 'Ripeness',
        'urgency': 'Urgency',
        'footer': 'Mode 1: MobileNetV2 Disease Detection (95.19% accuracy) | Mode 2: MobileNetV2 Ripeness Classification (98.41% accuracy)',
    },
    'BM': {
        'app_title': 'BananaChain AI',
        'app_sub': "Pengesanan Penyakit Pisang & Sokongan Keputusan Berkuasa AI",
        'mode1_tab': '🌿 Pengesanan Penyakit',
        'mode2_tab': '📦 Kematangan & Rantaian Bekalan',
        'mode1_title': '🌿 Pengesanan Penyakit Pisang',
        'mode1_desc': 'Muat naik foto **daun** pisang untuk mengesan penyakit dan mendapat nasihat rawatan langkah demi langkah.',
        'upload_leaf': 'Muat Naik Gambar Daun',
        'show_gradcam': 'Tunjukkan Peta Haba Grad-CAM',
        'analyse_disease': 'Analisis Penyakit',
        'analysing': 'Menganalisis daun...',
        'upload_prompt': 'Muat naik gambar daun pisang dan klik **Analisis Penyakit** untuk mendapat keputusan.',
        'what_is_it': 'Apakah Penyakit Ini?',
        'treatment': 'Rawatan Langkah demi Langkah',
        'prevention': 'Tips Pencegahan',
        'monitoring': 'Jadual Pemantauan',
        'economic': 'Kesan Ekonomi',
        'get_help': 'Dapatkan Bantuan',
        'weather_title': '🌤️ Cuaca Semasa',
        'spraying_advice': 'Nasihat Semburan',
        'weather_city': 'Masukkan bandar/daerah anda',
        'get_weather_btn': 'Dapatkan Cuaca',
        'ref_images': 'Gambar Rujukan',
        'ref_images_desc': 'Bandingkan daun anda dengan gambar rujukan ini',
        'your_image': 'Gambar Anda',
        'gradcam_overlay': 'Hamparan Grad-CAM',
        'confidence': 'Keyakinan',
        'severity': 'Keterukan',
        'probabilities': 'Kebarangkalian Ramalan',
        'mode2_title': '📦 Keputusan Kematangan & Rantaian Bekalan',
        'mode2_desc': 'Muat naik foto **buah pisang** untuk menilai kematangan dan mendapat cadangan rantaian bekalan.',
        'upload_banana': 'Muat Naik Gambar Pisang',
        'user_type': 'Saya adalah...',
        'quantity': 'Anggaran Kuantiti (kg)',
        'variety': 'Jenis Pisang',
        'analyse_ripeness': 'Analisis Kematangan',
        'analysing_ripeness': 'Menganalisis kematangan...',
        'upload_prompt2': 'Muat naik gambar pisang dan klik **Analisis Kematangan** untuk mendapat keputusan.',
        'what_it_means': 'Apakah Maksudnya?',
        'actions': 'Tindakan Yang Disyorkan',
        'storage': 'Temperature: Penyimpanan & Pengendalian',
        'channels': 'Saluran Pasaran',
        'financial': 'Anggaran Senario (Bukan Nilai Pasaran Dijamin)',
        'full_value': 'Nilai Pasaran Penuh',
        'recoverable': 'Nilai Boleh Dipulihkan',
        'potential_loss': 'Kerugian Berpotensi',
        'shelf_life': 'Jangka Hayat',
        'est_value': 'Anggaran Nilai',
        'ripeness': 'Kematangan',
        'urgency': 'Keutamaan',
        'footer': 'Mod 1: Pengesanan Penyakit MobileNetV2 (ketepatan 95.19%) | Mod 2: Klasifikasi Kematangan MobileNetV2 (ketepatan 98.41%)',
    },
    'ZH': {
        'app_title': 'BananaChain AI',
        'app_sub': "AI驱动的香蕉病害检测与决策支持",
        'mode1_tab': '🌿 病害检测',
        'mode2_tab': '📦 成熟度与供应链',
        'mode1_title': '🌿 香蕉病害检测',
        'mode1_desc': '上传香蕉**叶片**照片，检测病害并获取逐步治疗建议。',
        'upload_leaf': '上传叶片图片',
        'show_gradcam': '显示 Grad-CAM 热力图',
        'analyse_disease': '分析病害',
        'analysing': '正在分析叶片...',
        'upload_prompt': '上传香蕉叶片图片并点击**分析病害**获取结果。',
        'what_is_it': '这是什么病？',
        'treatment': '逐步治疗方案',
        'prevention': '预防建议',
        'monitoring': '监测计划',
        'economic': '经济损失影响',
        'get_help': '获取帮助',
        'weather_title': '🌤️ 当前天气',
        'spraying_advice': '施药建议',
        'weather_city': '输入您的城市/地区',
        'get_weather_btn': '获取天气',
        'ref_images': '参考图片',
        'ref_images_desc': '将您的叶片与以下参考图片对比',
        'your_image': '您的图片',
        'gradcam_overlay': 'Grad-CAM 叠加图',
        'confidence': '置信度',
        'severity': '严重程度',
        'probabilities': '预测概率',
        'mode2_title': '📦 成熟度与供应链决策',
        'mode2_desc': '上传**香蕉果实**照片，评估成熟度并获取供应链建议。',
        'upload_banana': '上传香蕉图片',
        'user_type': '我的身份是...',
        'quantity': '估计数量（公斤）',
        'variety': '香蕉品种',
        'analyse_ripeness': '分析成熟度',
        'analysing_ripeness': '正在分析成熟度...',
        'upload_prompt2': '上传香蕉图片并点击**分析成熟度**获取结果。',
        'what_it_means': '这意味着什么？',
        'actions': '建议操作步骤',
        'storage': 'Temperature: 储存与处理',
        'channels': '市场渠道',
        'financial': '情景估算（非保证市场价值）',
        'full_value': '完整市场价值',
        'recoverable': '可挽救价值',
        'potential_loss': '潜在损失',
        'shelf_life': '保质期',
        'est_value': '估计价值',
        'ripeness': '成熟度',
        'urgency': '紧急程度',
        'footer': '模式一：MobileNetV2 病害检测（准确率 95.19%）| 模式二：MobileNetV2 成熟度分类（准确率 98.41%）',
    }
}

# ─────────────────────────────────────────────
# DISEASE DATABASE
# ─────────────────────────────────────────────
REFERENCE_IMAGE_DIR = ASSETS_DIR / "reference_images"

DISEASE_REF_IMAGES = {
    "healthy": REFERENCE_IMAGE_DIR / "healthy.png",
    "black sigatoka": REFERENCE_IMAGE_DIR / "black_sigatoka.png",
    "fusarium wilt": REFERENCE_IMAGE_DIR / "fusarium_wilt.png",
    "yellow sigatoka": REFERENCE_IMAGE_DIR / "yellow_sigatoka.png",
    "banana moko disease": REFERENCE_IMAGE_DIR / "banana_moko_disease.png",
    "cordana": REFERENCE_IMAGE_DIR / "cordana.png",
}

# Fallback text descriptions if images fail to load
DISEASE_REF_DESC = {
    'healthy': "Look for: deep green colour, smooth leaf surface, no spots or streaks, firm leaf edges.",
    'black sigatoka': "Look for: narrow dark brown/black streaks parallel to leaf veins, yellow halo around streaks, leaves turning brown and dying from tip.",
    'fusarium wilt': "Look for: yellowing starting from oldest leaves, wilting despite watering, brown/purple discolouration inside the stem when cut open.",
    'yellow sigatoka': "Look for: pale yellow-green streaks turning brown, less severe than black sigatoka, spots mainly on older lower leaves.",
    'banana moko disease': "Look for: sudden wilting of all leaves, brown rotting inside fruit when cut, bacterial ooze from cut stem.",
    'cordana': "Look for: oval light brown spots with distinct yellow border/halo, mainly on leaf tips and edges, spots rarely exceed 3cm.",
}

DISEASE_INFO = {
    'healthy': {
        'severity': {'EN': 'None', 'BM': 'Tiada', 'ZH': '无'},
        'color': '🟢', 'box_class': 'green-box',
        'what_is_it': {
            'EN': 'Your banana plant shows no signs of disease. It appears healthy and well-maintained.',
            'BM': 'Pokok pisang anda tidak menunjukkan tanda-tanda penyakit. Ia kelihatan sihat dan terjaga.',
            'ZH': '您的香蕉植株没有病害迹象，看起来健康且管理良好。'
        },
        'immediate_actions': {
            'EN': ['✅ No treatment needed.','🔍 Continue weekly visual inspections.','Humidity: Maintain consistent watering — avoid waterlogging.','✂️ Remove any dead or yellowing leaves.'],
            'BM': ['✅ Tiada rawatan diperlukan.','🔍 Teruskan pemeriksaan mingguan.','Humidity: Kekalkan pengairan yang konsisten.','✂️ Buang daun yang mati atau menguning.'],
            'ZH': ['✅ 无需任何治疗。','🔍 继续每周目视检查。','Humidity: 保持稳定浇水，避免积水。','✂️ 及时移除枯死或变黄的叶片。']
        },
        'prevention_tips': {
            'EN': ['🌱 Use certified disease-free planting material.','🚜 Disinfect all farming tools after each use.','🌿 Base fertiliser choice and timing on soil or leaf analysis and local agronomic guidance.'],
            'BM': ['🌱 Gunakan bahan tanaman bersijil bebas penyakit.','🚜 Nyahkuman semua alatan pertanian selepas digunakan.','🌿 Tentukan baja dan masa penggunaan berdasarkan analisis tanah/daun serta panduan agronomi tempatan.'],
            'ZH': ['🌱 使用经认证的无病种植材料。','🚜 每次使用后对所有农具消毒。','🌿 根据土壤或叶片分析及当地农艺建议确定肥料种类和施用时间。']
        },
        'monitoring_schedule': {
            'EN': 'Inspect every 7 days.',
            'BM': 'Periksa setiap 7 hari.',
            'ZH': '每7天检查一次。'
        },
        'contact': None,
        'estimated_loss': None,
    },
    'black sigatoka': {
        'severity': {'EN': 'High', 'BM': 'Tinggi', 'ZH': '高'},
        'color': '🔴', 'box_class': 'red-box',
        'what_is_it': {
            'EN': 'Black Sigatoka (Mycosphaerella fijiensis) is a serious fungal leaf disease causing dark streaks and spots on leaves, reducing photosynthesis and potentially cutting yield by up to 50%.',
            'BM': 'Sigatoka Hitam (Mycosphaerella fijiensis) adalah penyakit kulat daun yang serius menyebabkan jalur dan bintik gelap pada daun, mengurangkan fotosintesis dan berpotensi mengurangkan hasil sehingga 50%.',
            'ZH': '黑条叶斑病（Mycosphaerella fijiensis）是一种严重的真菌性叶片病害，导致叶片出现黑色条纹和斑点，减少光合作用，可能使产量降低高达50%。'
        },
        'immediate_actions': {
            'EN': [
                '🍃 Step 1: Remove ALL visibly infected leaves. Cut at the base — do NOT shake (spores will spread).',
                '🗑️ Step 2: Seal removed leaves in plastic bags. Burn or bury them far from the farm.',
                '💊 Step 3: If chemical control is justified, use only a fungicide registered for banana and the target disease in Malaysia. Follow the product label for rate, interval, PPE and pre-harvest interval.',
                '🌧️ Step 4: Do NOT spray before rain. Best time: early morning or late afternoon.',
                '🔄 Step 5: Follow FRAC guidance: alternate or mix non-cross-resistant modes of action as permitted by the product labels; avoid repeated consecutive applications of the same mode of action.',
            ],
            'BM': [
                '🍃 Langkah 1: Buang SEMUA daun yang dijangkiti. Potong di pangkal — JANGAN goncang (spora akan merebak).',
                '🗑️ Langkah 2: Masukkan daun yang dibuang dalam beg plastik. Bakar atau tanam jauh dari ladang.',
                '💊 Langkah 3: Jika kawalan kimia diperlukan, gunakan hanya fungisid berdaftar untuk pisang dan penyakit sasaran di Malaysia. Ikuti label untuk kadar, selang, PPE dan tempoh pra-tuaian.',
                '🌧️ Langkah 4: JANGAN sembur sebelum hujan. Masa terbaik: awal pagi atau lewat petang.',
                '🔄 Langkah 5: Ikuti panduan FRAC: selang-seli atau campurkan mod tindakan yang tidak rintang silang seperti dibenarkan label; elakkan penggunaan berturut-turut mod tindakan yang sama.',
            ],
            'ZH': [
                '🍃 第一步：立即移除所有可见感染叶片。从基部剪断，切勿摇晃（孢子会扩散）。',
                '🗑️ 第二步：将移除的叶片装入密封塑料袋，在远离农场处烧毁或掩埋。',
                '💊 第三步：在48小时内施用杀菌剂：\n   • 代森锰锌80% WP（Dithane M-45）：每升2克，每3周喷一次\n   • 百菌清（Daconil）：每升2毫升，每2-3周喷一次\n   • 丙环唑（Tilt 250EC）：每升0.5毫升，每3-4周喷一次',
                '🌧️ 第四步：雨前不要喷药。最佳时间：清晨或傍晚。',
                '🔄 第五步：遵循FRAC指南，在标签允许范围内轮换或混配无交互抗性的作用机制，避免连续重复使用同一作用机制。',
            ]
        },
        'prevention_tips': {
            'EN': ['✂️ Prune lower leaves regularly to improve air flow.','📏 Maintain spacing and canopy ventilation appropriate to the cultivar and local production system.','🚜 Clean soil and plant debris from tools, then disinfect them between fields/plants using an officially recommended method and concentration.'],
            'BM': ['✂️ Pangkas daun bawah secara berkala untuk meningkatkan aliran udara.','📏 Kekalkan jarak dan pengudaraan kanopi yang sesuai dengan kultivar serta sistem pengeluaran tempatan.','🚜 Bersihkan tanah dan sisa tumbuhan pada alatan, kemudian nyahkuman antara ladang/pokok menggunakan kaedah dan kepekatan yang disyorkan pihak berkuasa.'],
            'ZH': ['✂️ 定期修剪下部叶片以改善通风。','📏 根据品种和当地生产系统保持适当株距与冠层通风。','🚜 先清除工具上的土壤和植物残体，再按官方建议的方法与浓度在田块/植株间消毒。']
        },
        'monitoring_schedule': {
            'EN': 'Inspect every 3 days for 2 weeks after treatment.',
            'BM': 'Periksa setiap 3 hari selama 2 minggu selepas rawatan.',
            'ZH': '治疗后2周内每3天检查一次。'
        },
        'contact': '📞 Jabatan Pertanian Malaysia: 03-8870 1000 | www.doa.gov.my',
        'estimated_loss': {
            'EN': 'Black Sigatoka can cause serious yield and fruit-quality losses when poorly managed. Confirm the diagnosis and begin an integrated management plan promptly.',
            'BM': 'Sigatoka Hitam boleh menyebabkan kehilangan hasil dan kualiti buah yang serius jika tidak diurus. Sahkan diagnosis dan mulakan pelan pengurusan bersepadu dengan segera.',
            'ZH': '黑条叶斑病管理不当可造成严重产量与果实品质损失。请确认诊断并尽快启动综合管理方案。'
        },
    },
    'fusarium wilt': {
        'severity': {'EN': 'Critical', 'BM': 'Kritikal', 'ZH': '极严重'},
        'color': '🚨', 'box_class': 'red-box',
        'what_is_it': {
            'EN': 'Fusarium Wilt (Fusarium oxysporum f.sp. cubense) is the most devastating banana disease in Malaysia. It lives in soil for 30+ years and has NO chemical cure.',
            'BM': 'Layu Fusarium adalah penyakit pisang yang paling merosakkan di Malaysia. Ia hidup dalam tanah lebih 30 tahun dan TIADA ubat kimia.',
            'ZH': '镰刀菌枯萎病是马来西亚最具破坏性的香蕉病害，在土壤中可存活30年以上，且没有化学治疗方法。'
        },
        'immediate_actions': {
            'EN': [
                '🚫 STOP all movement of plant material from this area immediately.',
                '🪓 Step 1: Uproot the ENTIRE infected plant — stem, leaves, and ALL roots.',
                '🔥 Step 2: Burn the uprooted plant on-site. Do NOT move it.',
                '🧼 Step 3: Do not prescribe a soil disinfectant yourself. Restrict access and obtain official instructions for containment, destruction and site sanitation.',
                '⛔ Step 4: Isolate the affected area and follow the quarantine boundary specified by the plant-health authority.',
                '📋 Step 5: Report to Jabatan Pertanian immediately.',
            ],
            'BM': [
                '🚫 HENTIKAN semua pergerakan bahan tanaman dari kawasan ini.',
                '🪓 Langkah 1: Cabut KESELURUHAN pokok yang dijangkiti — batang, daun, dan SEMUA akar.',
                '🔥 Langkah 2: Bakar pokok yang dicabut di tempat. JANGAN pindah.',
                '🧼 Langkah 3: Jangan tentukan sendiri bahan nyahkuman tanah. Hadkan akses dan dapatkan arahan rasmi untuk pembendungan, pelupusan dan sanitasi tapak.',
                '⛔ Langkah 4: Asingkan kawasan terjejas dan ikuti sempadan kuarantin yang ditetapkan pihak berkuasa kesihatan tumbuhan.',
                '📋 Langkah 5: Laporkan kepada Jabatan Pertanian dengan segera.',
            ],
            'ZH': [
                '🚫 立即停止该区域所有植物材料的移动。',
                '🪓 第一步：拔除整株感染植株，包括茎、叶和所有根系。',
                '🔥 第二步：就地焚烧拔除的植株，切勿转移。',
                '🧼 第三步：不要自行指定土壤消毒剂。限制人员进入，并向农业部门获取封锁、销毁与场地消毒指示。',
                '⛔ 第四步：隔离受影响区域，并遵循植物卫生主管部门规定的检疫范围。',
                '📋 第五步：立即向农业局报告。',
            ]
        },
        'prevention_tips': {
            'EN': ['🌱 Replant only after official diagnosis and with cultivars verified as suitable/resistant to the confirmed pathogen race in your location.','⏳ Do not replant banana in a confirmed infested site unless the plant-health authority provides a validated management plan.','🛡️ Do not rely on unverified biological products as a cure; use only products registered for the intended use and within an official integrated management plan.'],
            'BM': ['🌱 Tanam semula hanya selepas diagnosis rasmi dan dengan kultivar yang disahkan sesuai/tahan terhadap ras patogen di lokasi anda.','⏳ Jangan tanam semula pisang di tapak yang disahkan tercemar melainkan pihak berkuasa menyediakan pelan pengurusan yang disahkan.','🛡️ Jangan anggap produk biologi yang tidak disahkan sebagai penawar; gunakan hanya produk berdaftar dalam pelan pengurusan bersepadu rasmi.'],
            'ZH': ['🌱 仅在官方确诊后，选用经确认适合当地病原小种的抗性/适宜品种重新种植。','⏳ 在确认为污染的地块，不应重新种植香蕉，除非植物卫生主管部门提供经验证的管理方案。','🛡️ 不要把未经验证的生物产品当作治疗方法；仅在官方综合管理计划中使用已登记产品。']
        },
        'monitoring_schedule': {
            'EN': 'Check surrounding plants daily for 30 days after removing infected plant.',
            'BM': 'Semak pokok sekitar setiap hari selama 30 hari selepas membuang pokok yang dijangkiti.',
            'ZH': '移除感染植株后30天内每天检查周围植株。'
        },
        'contact': '🚨 Jabatan Pertanian: 03-8870 1000 | MARDI: 03-8953 7601',
        'estimated_loss': {
            'EN': 'One infected plant can spread to entire plantation. Potential total crop loss.',
            'BM': 'Satu pokok yang dijangkiti boleh merebak ke seluruh ladang. Berpotensi kehilangan hasil sepenuhnya.',
            'ZH': '一株感染植株可扩散至整个种植园，可能导致全部绝收。'
        },
    },
    'yellow sigatoka': {
        'severity': {'EN': 'Medium', 'BM': 'Sederhana', 'ZH': '中等'},
        'color': '🟡', 'box_class': 'yellow-box',
        'what_is_it': {
            'EN': 'Yellow Sigatoka (Mycosphaerella musicola) causes yellow streaks and spots on banana leaves. Less aggressive than Black Sigatoka but still weakens the plant.',
            'BM': 'Sigatoka Kuning menyebabkan jalur dan bintik kuning pada daun pisang. Kurang agresif daripada Sigatoka Hitam tetapi masih melemahkan pokok.',
            'ZH': '黄条叶斑病导致香蕉叶片出现黄色条纹和斑点，危害程度低于黑条叶斑病，但仍会使植株衰弱。'
        },
        'immediate_actions': {
            'EN': [
                '🍃 Step 1: Remove leaves with more than 50% spotting.',
                '💊 Step 2: If fungicide is needed, use a locally registered product according to its label and a resistance-management programme.',
                '🌧️ Step 3: Spray in dry weather only.',
                '🔄 Step 4: Alternate fungicides every 2–3 sprays.',
            ],
            'BM': [
                '🍃 Langkah 1: Buang daun dengan lebih 50% bintik.',
                '💊 Langkah 2: Jika fungisid diperlukan, gunakan produk berdaftar tempatan mengikut label dan program pengurusan rintangan.',
                '🌧️ Langkah 3: Sembur hanya dalam cuaca kering.',
                '🔄 Langkah 4: Tukar fungisid setiap 2–3 semburan.',
            ],
            'ZH': [
                '🍃 第一步：移除斑点超过50%的叶片。',
                '💊 第二步：如需使用杀菌剂，应选择当地登记产品，并遵循标签及抗药性管理方案。',
                '🌧️ 第三步：仅在干燥天气喷药。',
                '🔄 第四步：每2-3次喷药后轮换杀菌剂。',
            ]
        },
        'prevention_tips': {
            'EN': ['Humidity: Avoid overhead irrigation.','✂️ Remove lower leaves touching soil regularly.','📏 Ensure adequate plant spacing.'],
            'BM': ['Humidity: Elak pengairan dari atas.','✂️ Buang daun bawah yang menyentuh tanah secara berkala.','📏 Pastikan jarak tanaman yang mencukupi.'],
            'ZH': ['Humidity: 避免头顶灌溉。','✂️ 定期移除接触土壤的下部叶片。','📏 确保充足的株间距。']
        },
        'monitoring_schedule': {
            'EN': 'Inspect every 5 days. Disease should slow within 2–3 weeks of treatment.',
            'BM': 'Periksa setiap 5 hari. Penyakit sepatutnya perlahan dalam 2–3 minggu rawatan.',
            'ZH': '每5天检查一次，治疗后2-3周内病情应有所缓解。'
        },
        'contact': '📞 Jabatan Pertanian Malaysia: 03-8870 1000',
        'estimated_loss': {
            'EN': 'Yellow Sigatoka can reduce yield by 10–30% if left untreated.',
            'BM': 'Sigatoka Kuning boleh mengurangkan hasil 10–30% jika tidak dirawat.',
            'ZH': '黄条叶斑病若不治疗可使产量减少10-30%。'
        },
    },
    'banana moko disease': {
        'severity': {'EN': 'Critical', 'BM': 'Kritikal', 'ZH': '极严重'},
        'color': '🚨', 'box_class': 'red-box',
        'what_is_it': {
            'EN': 'Moko Disease (Ralstonia solanacearum) is a deadly bacterial wilt. It spreads through soil, water, insects, and tools. Once infected, the plant dies within days.',
            'BM': 'Penyakit Moko adalah layu bakteria maut. Ia merebak melalui tanah, air, serangga, dan alatan. Pokok yang dijangkiti mati dalam beberapa hari.',
            'ZH': '摩哥病（Ralstonia solanacearum）是一种致命的细菌性枯萎病，通过土壤、水、昆虫和工具传播，感染后植株在数天内死亡。'
        },
        'immediate_actions': {
            'EN': [
                '🚫 STOP all farming activities in the affected area.',
                '🪓 Step 1: Put on gloves before touching the plant.',
                '🔥 Step 2: Uproot entire plant. Burn immediately on-site.',
                '🧼 Step 3: Do not prescribe a soil disinfectant yourself; obtain official containment and sanitation instructions.',
                '⛔ Step 4: Isolate the affected area and follow the quarantine boundary specified by the plant-health authority.',
                '🐝 Step 5: Control insects in the area — they spread bacteria between flowers.',
                '📋 Step 6: Report to Jabatan Pertanian IMMEDIATELY.',
            ],
            'BM': [
                '🚫 HENTIKAN semua aktiviti pertanian di kawasan yang terjejas.',
                '🪓 Langkah 1: Pakai sarung tangan sebelum menyentuh pokok.',
                '🔥 Langkah 2: Cabut keseluruhan pokok. Bakar segera di tempat.',
                '🧪 Langkah 3: Rendam lubang tanaman dengan larutan bleach 10%.',
                '⛔ Langkah 4: Asingkan kawasan terjejas dan ikut sempadan kuarantin yang ditetapkan pihak berkuasa kesihatan tumbuhan.',
                '🐝 Langkah 5: Kawal serangga di kawasan — ia merebak bakteria antara bunga.',
                '📋 Langkah 6: Laporkan kepada Jabatan Pertanian SEGERA.',
            ],
            'ZH': [
                '🚫 立即停止受影响区域的所有农业活动。',
                '🪓 第一步：接触植株前先戴上手套。',
                '🔥 第二步：拔除整株植株，就地立即焚烧。',
                '🧪 第三步：向种植坑中灌入10%漂白水溶液。',
                '⛔ 第四步：隔离最少10米半径区域。',
                '🐝 第五步：控制该区域昆虫，它们会在花朵间传播细菌。',
                '📋 第六步：立即向农业局报告。',
            ]
        },
        'prevention_tips': {
            'EN': ['✂️ Cover all cut flower buds with plastic bags.','🛡️ Use only certified disease-free suckers.','🚜 NEVER share tools between farms without disinfection.'],
            'BM': ['✂️ Tutup semua kuntum bunga yang dipotong dengan beg plastik.','🛡️ Gunakan hanya anak benih bebas penyakit yang bersijil.','🚜 JANGAN kongsi alatan antara ladang tanpa nyahkuman.'],
            'ZH': ['✂️ 用塑料袋覆盖所有切割后的花蕾。','🛡️ 仅使用经认证的无病吸芽。','🚜 农具未消毒前切勿在农场间共用。']
        },
        'monitoring_schedule': {
            'EN': 'Inspect all plants within 20-metre radius daily for 60 days.',
            'BM': 'Periksa semua pokok dalam radius 20 meter setiap hari selama 60 hari.',
            'ZH': '60天内每天检查20米半径内的所有植株。'
        },
        'contact': '🚨 Jabatan Pertanian: 03-8870 1000 | Hotline: 1-800-88-0200 (Toll Free)',
        'estimated_loss': {
            'EN': 'Entire plantation at risk if not contained within 24 hours.',
            'BM': 'Seluruh ladang berisiko jika tidak dibendung dalam 24 jam.',
            'ZH': '若不在24小时内控制，整个种植园都面临风险。'
        },
    },
    'cordana': {
        'severity': {'EN': 'Low', 'BM': 'Rendah', 'ZH': '低'},
        'color': '🟠', 'box_class': 'orange-box',
        'what_is_it': {
            'EN': 'Cordana Leaf Spot (Cordana musae) causes oval brown spots with yellow halos on leaves. It mainly affects weakened plants and rarely causes serious yield loss.',
            'BM': 'Bintik Daun Cordana menyebabkan bintik coklat bujur dengan halo kuning pada daun. Ia terutamanya menjejaskan pokok yang lemah dan jarang menyebabkan kehilangan hasil yang serius.',
            'ZH': '科达纳叶斑病在叶片上产生带黄晕的椭圆形褐色斑点，主要影响衰弱的植株，很少造成严重的产量损失。'
        },
        'immediate_actions': {
            'EN': [
                '✂️ Step 1: Trim affected leaf tips or remove severely spotted leaves.',
                '🗑️ Step 2: Collect removed leaves and compost away from plantation.',
                '💊 Step 3: Apply copper-based fungicide if spreading:\n   • Copper Oxychloride (Kocide): 3g/L, every 3–4 weeks',
                'Humidity: Step 4: Improve drainage around plants.',
            ],
            'BM': [
                '✂️ Langkah 1: Trim hujung daun yang terjejas atau buang daun yang teruk.',
                '🗑️ Langkah 2: Kumpulkan daun yang dibuang dan kompos jauh dari ladang.',
                '💊 Langkah 3: Sembur fungisid berasaskan kuprum jika merebak:\n   • Copper Oxychloride (Kocide): 3g/L, setiap 3–4 minggu',
                'Humidity: Langkah 4: Tingkatkan saliran di sekeliling pokok.',
            ],
            'ZH': [
                '✂️ 第一步：修剪受影响的叶尖或移除严重斑点的叶片。',
                '🗑️ 第二步：收集移除的叶片，在远离种植园处堆肥。',
                '💊 第三步：若扩散，施用铜基杀菌剂：\n   • 氯氧化铜（Kocide）：每升3克，每3-4周一次',
                'Humidity: 第四步：改善植株周围的排水。',
            ]
        },
        'prevention_tips': {
            'EN': ['🌿 Fertilise regularly — Cordana attacks nutrient-deficient plants.','Humidity: Improve soil drainage.','☀️ Ensure adequate sunlight.'],
            'BM': ['🌿 Baja secara berkala — Cordana menyerang pokok kekurangan nutrien.','Humidity: Tingkatkan saliran tanah.','☀️ Pastikan cahaya matahari yang mencukupi.'],
            'ZH': ['🌿 定期施肥，科达纳主要侵害营养缺乏的植株。','Humidity: 改善土壤排水。','☀️ 确保充足的光照。']
        },
        'monitoring_schedule': {
            'EN': 'Inspect every 10 days. Rarely urgent.',
            'BM': 'Periksa setiap 10 hari. Jarang mendesak.',
            'ZH': '每10天检查一次，很少需要紧急处理。'
        },
        'contact': '📞 Jabatan Pertanian Malaysia: 03-8870 1000',
        'estimated_loss': {
            'EN': 'Minimal yield impact (less than 10%) if managed early.',
            'BM': 'Kesan hasil yang minimum (kurang 10%) jika diuruskan awal.',
            'ZH': '若早期管理，产量影响最小（不超过10%）。'
        },
    },
}

# ─────────────────────────────────────────────
# SUPPLY CHAIN DATABASE
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# LIVE PRICE SCRAPING (manamurah.com)
# Source: PriceCatcher KPDN via manamurah.com
# Updated weekly
# ─────────────────────────────────────────────
VARIETY_URLS = {
    'Pisang Berangan':  'https://manamurah.com/barang/pisang_berangan-18',
    'Pisang Mas':       'https://manamurah.com/barang/pisang_emas-19',
    'Pisang Cavendish': 'https://manamurah.com/barang/pisang_cavendish-20',
}

# Fallback prices if scraping fails
FAMA_PRICE_FALLBACK = {
    'Pisang Berangan':  7.29,
    'Pisang Mas':       6.68,
    'Pisang Cavendish': 5.50,
}

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_banana_price(variety):
    """Scrape live banana price from manamurah.com (PriceCatcher KPDN data)."""
    try:
        url = VARIETY_URLS.get(variety)
        if not url:
            return FAMA_PRICE_FALLBACK.get(variety, 6.00), None, None
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        import re
        # Match "Harga purata RM X.XX kebangsaan"
        match = re.search(r'Harga purata RM\s*([\d.]+)\s*kebangsaan', text)
        if match:
            price = float(match.group(1))
            # Match date "22 Jun 2026"
            date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', text)
            date_str = date_match.group(1) if date_match else 'N/A'
            # Match range "RM X.XX – RM X.XX"
            range_match = re.search(r'Termurah RM\s*([\d.]+).*?Termahal RM\s*([\d.]+)', text, re.DOTALL)
            price_range = f"RM {range_match.group(1)} – RM {range_match.group(2)}" if range_match else None
            return price, date_str, price_range
    except Exception:
        pass
    return FAMA_PRICE_FALLBACK.get(variety, 6.00), None, None

@st.cache_data(ttl=3600)
def get_all_prices():
    """Fetch prices for all varieties."""
    prices = {}
    for variety in VARIETY_URLS:
        price, date, price_range = fetch_banana_price(variety)
        prices[variety] = {'price': price, 'date': date, 'range': price_range}
    return prices

def get_fama_price(variety):
    """Get price for a specific variety."""
    price, _, _ = fetch_banana_price(variety)
    return price

# Keep FAMA_PRICE as dict for backwards compatibility (populated dynamically)
FAMA_PRICE = FAMA_PRICE_FALLBACK.copy()

USER_TYPES = {
    'EN': ['🧑‍🌾 Farmer (Selling harvest)', '🚛 Wholesaler / Distributor', '🏬 Supermarket / Retailer'],
    'BM': ['🧑‍🌾 Petani (Jual hasil tuaian)', '🚛 Pemborong / Pengedar', '🏬 Pasaraya / Peruncit'],
    'ZH': ['🧑‍🌾 农夫（出售收成）', '🚛 批发商/分销商', '🏬 超市/零售商']
}

# 13–15°C storage / <13°C chilling injury thresholds below: see REFERENCES['ripeness_storage']
def get_supply_chain_decision(ripeness_label, quantity_kg, variety, user_type_idx, lang):
    base_price = get_fama_price(variety)
    L = lang

    decisions = {
        'unripe': {
            'status': {'EN': '🟢 Unripe', 'BM': '🟢 Mentah', 'ZH': '🟢 未成熟'},
            'shelf_life': '7–10 days / hari / 天',
            'urgency': {'EN': 'LOW', 'BM': 'RENDAH', 'ZH': '低'},
            'box_class': 'green-box',
            'what_it_means': {
                'EN': 'Banana is in early ripening stage. Firm flesh, high starch. Ideal for long-distance transport.',
                'BM': 'Pisang dalam peringkat awal masak. Isi keras, kanji tinggi. Sesuai untuk pengangkutan jarak jauh.',
                'ZH': '香蕉处于早期成熟阶段，果肉硬实，淀粉含量高，适合长途运输。'
            },
            'actions': {
                0: {  # Farmer
                    'EN': [f'📦 Pack into 13kg cartons with ventilation holes.',f'🚛 Contact interstate wholesalers or cold chain distributors.',f'💰 FAMA reference price: RM {base_price:.2f}/kg',f'Temperature: Transport at 13–15°C (do NOT go below 13°C — causes cold injury).'],
                    'BM': [f'📦 Pak dalam karton 13kg dengan lubang pengudaraan.',f'🚛 Hubungi pemborong antara negeri atau pengedar rantaian sejuk.',f'💰 Harga rujukan FAMA: RM {base_price:.2f}/kg',f'Temperature: Pengangkutan pada 13–15°C (JANGAN bawah 13°C — menyebabkan kecederaan sejuk).'],
                    'ZH': [f'📦 装入带通风孔的13公斤纸箱。',f'🚛 联系跨州批发商或冷链分销商。',f'💰 FAMA参考价格：RM {base_price:.2f}/公斤',f'Temperature: 在13-15°C运输（切勿低于13°C，否则会造成冷害）。'],
                },
                1: {  # Wholesaler
                    'EN': [f'🏪 Store at 13–15°C in cold storage.',f'📋 Label: harvest date, variety, origin, expected ripeness date.',f'🚛 Route to Klang Valley, JB, or Penang pasar borong.',f'💰 Wholesale margin: aim for RM {base_price+0.5:.2f}–{base_price+1.0:.2f}/kg'],
                    'BM': [f'🏪 Simpan pada 13–15°C dalam stor sejuk.',f'📋 Label: tarikh tuai, jenis, asal, tarikh masak dijangka.',f'🚛 Hantar ke Lembah Klang, JB, atau pasar borong Penang.',f'💰 Margin borong: sasaran RM {base_price+0.5:.2f}–{base_price+1.0:.2f}/kg'],
                    'ZH': [f'🏪 在冷藏库中13-15°C储存。',f'📋 标签注明：采收日期、品种、产地、预计成熟日期。',f'🚛 路由至巴生谷、新山或槟城批发市场。',f'💰 批发利润：目标RM {base_price+0.5:.2f}–{base_price+1.0:.2f}/公斤'],
                },
                2: {  # Supermarket
                    'EN': [f'✅ SUITABLE for receiving — good shelf life ahead.',f'🔍 Inspect for physical damage before accepting.',f'🏪 Route to back storage, schedule display in 5–7 days.',f'💰 Suggested retail price: RM {base_price*1.8:.2f}–{base_price*2.2:.2f}/kg'],
                    'BM': [f'✅ SESUAI untuk diterima — jangka hayat yang baik.',f'🔍 Periksa kerosakan fizikal sebelum menerima.',f'🏪 Simpan di belakang, jadualkan paparan dalam 5–7 hari.',f'💰 Harga runcit yang dicadangkan: RM {base_price*1.8:.2f}–{base_price*2.2:.2f}/kg'],
                    'ZH': [f'✅ 适合接收，保质期充足。',f'🔍 接收前检查物理损伤。',f'🏪 存入后仓，安排5-7天后上架。',f'💰 建议零售价：RM {base_price*1.8:.2f}–{base_price*2.2:.2f}/公斤'],
                },
            },
            'storage': {
                'EN': ['Temperature: Optimal: 13–15°C', 'Humidity: Humidity: 90–95%', '⏰ Ripens in 7–10 days at room temp', '❌ Do NOT store with apples/tomatoes (ethylene gas)'],
                'BM': ['Temperature: Optimum: 13–15°C', 'Humidity: Kelembapan: 90–95%', '⏰ Masak dalam 7–10 hari pada suhu bilik', '❌ JANGAN simpan bersama epal/tomato (gas etilena)'],
                'ZH': ['Temperature: 最佳温度：13-15°C', 'Humidity: 湿度：90-95%', '⏰ 室温下7-10天成熟', '❌ 切勿与苹果/番茄同储（乙烯气体）'],
            },
            'estimated_value': round(quantity_kg * base_price, 2),
            'salvage_value': round(quantity_kg * base_price, 2),
        },
        'freshripe': {
            'status': {'EN': '🟡 Fresh Ripe', 'BM': '🟡 Masak Segar', 'ZH': '🟡 新鲜成熟'},
            'shelf_life': '2–4 days / hari / 天',
            'urgency': {'EN': 'MEDIUM', 'BM': 'SEDERHANA', 'ZH': '中'},
            'box_class': 'yellow-box',
            'what_it_means': {
                'EN': 'Peak ripeness — maximum sweetness. Golden selling window. Every day of delay reduces value.',
                'BM': 'Kematangan puncak — kemanisan maksimum. Tetingkap jualan keemasan. Setiap hari kelewatan mengurangkan nilai.',
                'ZH': '最佳成熟度，甜度最高，是黄金销售窗口期，每延误一天价值都会降低。'
            },
            'actions': {
                0: {  # Farmer
                    'EN': [f'⚡ Move to market IMMEDIATELY — do not delay more than 24 hours.',f'📞 Call local wholesalers now: Pasar Borong Selayang: 03-6136 4888',f'💰 Full FAMA rate: RM {base_price:.2f}/kg — do not accept below this.',f'🚛 Standard lorry sufficient — no refrigeration needed.'],
                    'BM': [f'⚡ Bawa ke pasaran SEGERA — jangan lewat lebih 24 jam.',f'📞 Hubungi pemborong tempatan sekarang: Pasar Borong Selayang: 03-6136 4888',f'💰 Kadar FAMA penuh: RM {base_price:.2f}/kg — jangan terima di bawah ini.',f'🚛 Lori biasa sudah mencukupi — tiada penyejukan diperlukan.'],
                    'ZH': [f'⚡ 立即送往市场，不要延误超过24小时。',f'📞 立即联系当地批发商：Pasar Borong Selayang：03-6136 4888',f'💰 完整FAMA价格：RM {base_price:.2f}/公斤，不要低价接受。',f'🚛 普通卡车即可，无需冷藏。'],
                },
                1: {  # Wholesaler
                    'EN': [f'⚡ Distribute within 24 hours.',f'🏪 Priority: Local supermarkets and wet markets.',f'💰 Sell at RM {base_price+0.5:.2f}–{base_price+0.8:.2f}/kg.',f'📦 Do NOT refrigerate — room temperature 18–20°C.'],
                    'BM': [f'⚡ Edar dalam 24 jam.',f'🏪 Keutamaan: Pasaraya tempatan dan pasar basah.',f'💰 Jual pada RM {base_price+0.5:.2f}–{base_price+0.8:.2f}/kg.',f'📦 JANGAN sejukkan — suhu bilik 18–20°C.'],
                    'ZH': [f'⚡ 24小时内分销。',f'🏪 优先：本地超市和湿巴刹。',f'💰 以RM {base_price+0.5:.2f}–{base_price+0.8:.2f}/公斤出售。',f'📦 切勿冷藏，室温18-20°C存放。'],
                },
                2: {  # Supermarket
                    'EN': [f'🛒 List IMMEDIATELY on shelves — front placement recommended.',f'🏷️ Full retail price: RM {base_price*1.8:.2f}–{base_price*2.0:.2f}/kg',f'⏰ Mark with "Best Before" date: {2}–{4} days from today.',f'📣 Feature in promotions to drive quick turnover.'],
                    'BM': [f'🛒 Letak di rak SEGERA — penempatan hadapan disyorkan.',f'🏷️ Harga runcit penuh: RM {base_price*1.8:.2f}–{base_price*2.0:.2f}/kg',f'⏰ Tandakan tarikh "Terbaik Sebelum": {2}–{4} hari dari hari ini.',f'📣 Tampilkan dalam promosi untuk pusing ganti cepat.'],
                    'ZH': [f'🛒 立即上架，建议放置在显眼位置。',f'🏷️ 全价零售：RM {base_price*1.8:.2f}–{base_price*2.0:.2f}/公斤',f'⏰ 标注"最佳食用期"：今天起{2}-{4}天内。',f'📣 纳入促销活动以加快周转。'],
                },
            },
            'storage': {
                'EN': ['Temperature: Room temperature: 18–20°C', '❌ Do NOT refrigerate — cold blackens skin', '🍌 Minimise compression and bruising; use ventilated packaging and gentle handling', '⏰ Shelf life: 2–4 days'],
                'BM': ['Temperature: Suhu bilik: 18–20°C', '❌ JANGAN sejukkan — sejuk menghitamkan kulit', '🍌 Kurangkan tekanan dan lebam; gunakan pembungkusan berpengudaraan dan pengendalian lembut', '⏰ Jangka hayat: 2–4 hari'],
                'ZH': ['Temperature: 室温：18-20°C', '❌ 切勿冷藏，低温会使果皮变黑', '🍌 减少挤压和碰伤，采用通风包装并轻柔搬运', '⏰ 保质期：2-4天'],
            },
            'estimated_value': round(quantity_kg * base_price, 2),
            'salvage_value': round(quantity_kg * base_price, 2),
        },
        'rotten': {
            'status': {'EN': '🔴 Overripe / Rotten', 'BM': '🔴 Terlalu Masak / Busuk', 'ZH': '🔴 过熟/腐烂'},
            'shelf_life': '1–2 days / hari / 天',
            'urgency': {'EN': 'HIGH', 'BM': 'TINGGI', 'ZH': '高'},
            'box_class': 'red-box',
            'what_it_means': {
                'EN': 'Past peak ripeness. Cannot sell at full price but still has significant salvage value through alternative channels.',
                'BM': 'Telah lepasi kematangan puncak. Tidak boleh dijual pada harga penuh tetapi masih mempunyai nilai penyelamatan yang ketara.',
                'ZH': '已过最佳成熟期，不能以全价出售，但通过替代渠道仍有显著的可挽救价值。'
            },
            'actions': {
                0: {  # Farmer
                    'EN': [f'🚨 Do NOT attempt full-price sale — it harms your reputation.',f'🔀 Sort: separate brown (edible) from black (discard).',f'🏭 Contact food processors immediately:\n   • Cekodok/Goreng Pisang stalls: visit pasar malam vendors\n   • Banana cake factories: search "kilang kek pisang" locally',f'🤝 If no buyer in 12 hours: FoodBank Malaysia: 03-2788 1000',f'💰 Sell overripe at RM {base_price*0.5:.2f}/kg (50% discount).'],
                    'BM': [f'🚨 JANGAN cuba jual pada harga penuh — merosakkan reputasi anda.',f'🔀 Isih: asingkan coklat (boleh makan) dari hitam (buang).',f'🏭 Hubungi pemproses makanan segera:\n   • Gerai Cekodok/Goreng Pisang: lawati peniaga pasar malam\n   • Kilang kek pisang: cari "kilang kek pisang" tempatan',f'🤝 Jika tiada pembeli dalam 12 jam: FoodBank Malaysia: 03-2788 1000',f'💰 Jual terlalu masak pada RM {base_price*0.5:.2f}/kg (diskaun 50%).'],
                    'ZH': [f'🚨 切勿尝试全价出售，这会损害您的声誉。',f'🔀 分类：将棕色（可食）与黑色（丢弃）分开。',f'🏭 立即联系食品加工商：\n   • Cekodok/炸香蕉摊：拜访夜市摊贩\n   • 香蕉蛋糕工厂：本地搜索"kilang kek pisang"',f'🤝 12小时内无买家：FoodBank Malaysia：03-2788 1000',f'💰 过熟品以RM {base_price*0.5:.2f}/公斤出售（5折）。'],
                },
                1: {  # Wholesaler
                    'EN': [f'Regrade the lot and set any markdown using current observed prices, quality condition and your organisation’s policy.',f'📞 Call downstream food processors now.',f'🧊 Peel and freeze pulp — sells to bakeries at RM 1.50–2.00/kg.',f'🤝 Unsold stock: donate to FoodBank Malaysia: 03-2788 1000'],
                    'BM': [f'Gred semula lot dan tetapkan pengurangan harga berdasarkan harga semasa, keadaan kualiti dan polisi organisasi.',f'📞 Hubungi pemproses makanan hiliran sekarang.',f'🧊 Kupas dan bekukan isi — dijual kepada bakeri pada RM 1.50–2.00/kg.',f'🤝 Stok yang tidak terjual: derma kepada FoodBank Malaysia: 03-2788 1000'],
                    'ZH': [f'重新分级，并依据当前参考价格、品质状况及机构政策决定是否降价。',f'📞 立即联系下游食品加工商。',f'🧊 去皮冷冻果肉，以RM 1.50-2.00/公斤售给面包店。',f'🤝 未售出库存：捐赠给FoodBank Malaysia：03-2788 1000'],
                },
                2: {  # Supermarket
                    'EN': [f'❌ DO NOT put on shelves at full price.',f'🏷️ Regrade and price according to current reference data and store policy; do not use a fixed discount without evidence',f'📦 Package as "Ripe & Ready" bundles for baking customers.',f'🤝 End of day: donate unsold stock to FoodBank Malaysia: 03-2788 1000'],
                    'BM': [f'❌ JANGAN letak di rak pada harga penuh.',f'🏷️ Gred semula dan tetapkan harga berdasarkan data rujukan semasa serta polisi kedai; jangan gunakan diskaun tetap tanpa bukti',f'📦 Bungkus sebagai bundle "Masak & Sedia" untuk pelanggan bakar.',f'🤝 Hujung hari: derma stok yang tidak terjual ke FoodBank Malaysia: 03-2788 1000'],
                    'ZH': [f'❌ 切勿以全价上架。',f'🏷️ 依据当前参考数据与门店政策重新分级和定价；没有证据时不要使用固定折扣',f'📦 打包为"熟透即食"套餐面向烘焙顾客。',f'🤝 当天结束：将未售出库存捐赠给FoodBank Malaysia：03-2788 1000'],
                },
            },
            'storage': {
                'EN': ['❄️ Do not use a fixed low-temperature rule for damaged fruit; assess food safety and follow validated postharvest guidance', '🧊 Freeze peeled pulp for bakery sales', '📦 Package in 1kg bags for food processors', '⏰ Separate damaged fruit promptly and follow your organisation’s food-safety and quality procedure'],
                'BM': ['❄️ Jangan gunakan peraturan suhu rendah tetap untuk buah rosak; nilai keselamatan makanan dan ikut panduan pascatuai yang disahkan', '🧊 Bekukan isi yang dikupas untuk jualan bakeri', '📦 Bungkus dalam beg 1kg untuk pemproses makanan', '⏰ Asingkan buah rosak dengan segera dan ikut prosedur keselamatan makanan serta kualiti organisasi'],
                'ZH': ['❄️ 不要对受损果实使用固定低温规则；应评估食品安全并遵循经验证的采后指南', '🧊 冷冻去皮果肉用于面包店销售', '📦 装入1公斤袋供食品加工商使用', '⏰ 尽快分离受损果实，并遵循机构的食品安全与质量程序'],
            },
            'estimated_value': round(quantity_kg * base_price * 0.5, 2),
            'salvage_value': round(quantity_kg * base_price * 0.5, 2),
        },
    }
    d = decisions.get(ripeness_label, decisions['freshripe'])
    d['actions_for_user'] = d['actions'][user_type_idx]
    return d

# ─────────────────────────────────────────────
# LOAD MODELS
# ─────────────────────────────────────────────
@st.cache_resource
def load_disease_model():
    model = tf.keras.models.load_model(MODELS_DIR / 'banana_disease_model.keras')
    with open(MODELS_DIR / 'disease_class_info.json', encoding='utf-8') as f:
        info = json.load(f)
    return model, info

@st.cache_resource
def load_ripeness_model():
    model = tf.keras.models.load_model(MODELS_DIR / 'banana_ripeness_model.h5')
    with open(MODELS_DIR / 'ripeness_class_info.json', encoding='utf-8') as f:
        info = json.load(f)
    return model, info

def preprocess_image(image):
    img = image.convert('RGB').resize((224, 224))
    arr = np.array(img) / 255.0
    return np.expand_dims(arr, axis=0), np.array(img)

def get_gradcam(model, img_array):
    """Generate Grad-CAM for a model containing a nested CNN such as MobileNetV2.

    The function automatically finds the nested feature-extraction model and its
    final convolutional layer, so it does not assume that model.layers[0] is the
    MobileNetV2 model. This supports models whose first layer is an InputLayer.
    """
    # Find the nested feature extractor (for example MobileNetV2).
    base_model = next(
        (
            layer
            for layer in model.layers
            if isinstance(layer, tf.keras.Model)
            and any(
                isinstance(inner, (tf.keras.layers.Conv2D, tf.keras.layers.DepthwiseConv2D))
                for inner in layer.layers
            )
        ),
        None,
    )

    if base_model is None:
        raise ValueError("No convolutional feature extractor was found in the disease model.")

    # Find the final spatial convolutional layer inside the feature extractor.
    last_conv = next(
        (
            layer
            for layer in reversed(base_model.layers)
            if isinstance(layer, (tf.keras.layers.Conv2D, tf.keras.layers.DepthwiseConv2D))
        ),
        None,
    )

    if last_conv is None:
        raise ValueError("No convolutional layer was found for the highlighted area.")

    # Extract both the final convolutional features and the base-model output.
    feature_model = tf.keras.Model(
        inputs=base_model.input,
        outputs=[last_conv.output, base_model.output],
        name="gradcam_feature_model",
    )

    # Layers after the nested MobileNetV2 form the classification head.
    base_index = model.layers.index(base_model)
    classifier_layers = model.layers[base_index + 1:]

    with tf.GradientTape() as tape:
        conv_output, x = feature_model(img_array, training=False)
        tape.watch(conv_output)

        for layer in classifier_layers:
            # InputLayer cannot be called and should not appear here, but skip it
            # defensively in case the model structure changes later.
            if isinstance(layer, tf.keras.layers.InputLayer):
                continue
            x = layer(x, training=False)

        predictions = x
        predicted_index = tf.argmax(predictions[0])
        predicted_score = predictions[:, predicted_index]

    gradients = tape.gradient(predicted_score, conv_output)
    if gradients is None:
        raise ValueError("The highlighted area could not be connected to the prediction output.")

    pooled_gradients = tf.reduce_mean(gradients, axis=(0, 1, 2))
    heatmap = tf.reduce_sum(conv_output[0] * pooled_gradients, axis=-1)
    heatmap = tf.maximum(heatmap, 0)

    maximum = tf.reduce_max(heatmap)
    heatmap = tf.where(maximum > 0, heatmap / maximum, heatmap)
    return heatmap.numpy()

def overlay_gradcam(img_array, heatmap):
    h = cv2.resize(heatmap, (224, 224))
    hc = cv2.applyColorMap(np.uint8(255 * h), cv2.COLORMAP_JET)
    hc = cv2.cvtColor(hc, cv2.COLOR_BGR2RGB)
    return np.clip((hc / 255.0 * 0.4) + img_array.astype(np.float32) / 255.0 * 0.6, 0, 1)

# ─────────────────────────────────────────────
# CSS / BACKGROUND
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# MULTI-IMAGE REPORT HELPERS
# ─────────────────────────────────────────────
def build_reports_zip(report_documents):
    """Package individually generated reports into one ZIP without extra dependencies."""
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for file_name, document in report_documents:
            if document:
                archive.writestr(file_name, document)
    return output.getvalue()


def safe_file_stem(filename, fallback="banana_image"):
    stem = Path(filename or fallback).stem
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")
    return cleaned or fallback


@st.cache_resource

def load_imagenet_validator():
    """Load an ImageNet MobileNetV2 gate. This does not retrain either project model."""
    try:
        from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2
        return MobileNetV2(weights="imagenet")
    except Exception:
        return None


def _image_quality_and_colour(image):
    rgb = np.array(image.convert("RGB").resize((224, 224)))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, sat, val = cv2.split(hsv)

    green = ((h >= 28) & (h <= 95) & (sat >= 35) & (val >= 30))
    yellow = ((h >= 15) & (h <= 38) & (sat >= 45) & (val >= 45))
    brown = ((h >= 3) & (h <= 22) & (sat >= 35) & (val >= 20) & (val <= 200))
    organic = green | yellow | brown

    return {
        "brightness": float(val.mean()),
        "contrast": float(gray.std()),
        "saturation": float(sat.mean()),
        "green_ratio": float(green.mean()),
        "yellow_ratio": float(yellow.mean()),
        "brown_ratio": float(brown.mean()),
        "organic_ratio": float(organic.mean()),
    }


def _imagenet_labels(image, top=10):
    model = load_imagenet_validator()
    if model is None:
        return []
    try:
        from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions
        arr = np.array(image.convert("RGB").resize((224, 224)), dtype=np.float32)
        arr = preprocess_input(np.expand_dims(arr, axis=0))
        predictions = model.predict(arr, verbose=0)
        return [(label.lower().replace("_", " "), float(score))
                for _, label, score in decode_predictions(predictions, top=top)[0]]
    except Exception:
        return []


def validate_target_image(image, mode):
    """Basic no-retraining input gate. Returns (accepted, message, details).

    It rejects obvious unsupported inputs. Because no dedicated banana-vs-other
    validator was trained, visually similar plants or yellow objects can still
    occasionally pass; this limitation is shown in the UI wording.
    """
    features = _image_quality_and_colour(image)
    labels = _imagenet_labels(image)
    label_text = " ".join(label for label, _ in labels)

    if features["brightness"] < 22 or features["contrast"] < 8:
        return False, "The image is too dark, blank, or unclear. Please upload a clearer image.", features

    non_target_terms = {
        "person", "face", "dog", "cat", "car", "truck", "bus", "motorcycle",
        "airliner", "screen", "laptop", "keyboard", "book", "building", "room",
        "plate", "bottle", "shoe", "clock", "television", "furniture"
    }
    strong_non_target = any(term in label_text for term in non_target_terms)

    if mode == "disease":
        plant_terms = {
            "leaf", "plant", "banana", "tree", "vegetable", "cabbage", "corn",
            "maize", "grass", "flower", "herb", "palm", "fern", "rapeseed"
        }
        semantic_plant = any(term in label_text for term in plant_terms)
        visual_leaf = (
            features["green_ratio"] >= 0.10
            or features["organic_ratio"] >= 0.24
            or (features["saturation"] >= 45 and features["contrast"] >= 24)
        )
        accepted = visual_leaf and (semantic_plant or not strong_non_target)
        message = (
            "This mode only accepts a banana leaf image, including a full leaf or a close-up of leaf symptoms."
        )
    else:
        semantic_banana = "banana" in label_text
        banana_colours = (
            features["yellow_ratio"] >= 0.07
            or features["green_ratio"] >= 0.14
            or (features["yellow_ratio"] + features["brown_ratio"] >= 0.12)
        )
        accepted = banana_colours and (semantic_banana or not strong_non_target)
        # For fruit mode, semantic confirmation is preferred. A stronger colour
        # threshold keeps green/unripe bananas usable when ImageNet is uncertain.
        if labels and not semantic_banana and features["organic_ratio"] < 0.32:
            accepted = False
        message = "This mode only accepts a clear image of banana fruit, either a single banana or a banana bunch."

    return bool(accepted), message, {**features, "labels": labels}


def build_disease_display_data(pred_class):
    legacy = DISEASE_INFO.get(pred_class, DISEASE_INFO['healthy'])
    evidence = EVIDENCE_DISEASE_INFO.get(
        pred_class.replace('_', ' ').lower().strip(),
        EVIDENCE_DISEASE_INFO['healthy'],
    )
    disease = dict(legacy)
    disease['severity'] = evidence['severity']
    disease['what_is_it'] = evidence['what_is_it']
    disease['immediate_actions'] = {
        code: [item['text'] for item in get_evidence_items(pred_class, 'immediate_actions', code)]
        for code in ('EN', 'BM', 'ZH')
    }
    disease['prevention_tips'] = {
        code: [item['text'] for item in get_evidence_items(pred_class, 'prevention_tips', code)]
        for code in ('EN', 'BM', 'ZH')
    }
    disease['monitoring_schedule'] = {
        code: ' '.join(item['text'] for item in get_evidence_items(pred_class, 'monitoring', code))
        for code in ('EN', 'BM', 'ZH')
    }
    disease['estimated_loss'] = None
    return disease


def evidence_reference_list_for_disease(pred_class, lang):
    references = []
    seen = set()
    for section in ('immediate_actions', 'prevention_tips', 'monitoring'):
        for entry in get_evidence_items(pred_class, section, lang):
            for source in entry['sources']:
                if source['url'] not in seen:
                    seen.add(source['url'])
                    references.append({
                        'short': f"{source['organisation']} — {source['title']}",
                        'url': source['url'],
                    })
    return references


# ─────────────────────────────────────────────
# CSS / BACKGROUND
# ─────────────────────────────────────────────
apply_theme(CSS_PATH, BACKGROUND_PATH)

# Compact styling for batch result cards and the single sidebar disclaimer.
st.markdown("""
<style>
.batch-summary {font-size:0.88rem;color:#6b7280;margin:-0.2rem 0 0.7rem 0;}
.sidebar-disclaimer {font-size:0.68rem;line-height:1.42;color:#8a8f98;padding-top:0.25rem;}
[data-testid="stFileUploader"] small {font-size:0.78rem;}
/* Professional blue primary actions */
button[kind="primary"] {
    background:#1976D2 !important;
    border-color:#1976D2 !important;
    color:#ffffff !important;
    border-radius:10px !important;
    font-weight:600 !important;
    box-shadow:0 4px 12px rgba(25, 118, 210, 0.20) !important;
    transition:background-color 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease !important;
}
button[kind="primary"]:hover {
    background:#1565C0 !important;
    border-color:#1565C0 !important;
    box-shadow:0 6px 16px rgba(21, 101, 192, 0.28) !important;
    transform:translateY(-1px);
}
button[kind="primary"]:active {
    transform:translateY(0);
    box-shadow:0 2px 8px rgba(21, 101, 192, 0.22) !important;
}
.analysis-loader {
    display:flex;
    align-items:center;
    gap:0.55rem;
    padding:0.45rem 0.1rem;
    font-weight:600;
    color:#243447;
}
.analysis-loader .rolling-banana {
    display:inline-block;
    font-size:1.35rem;
    transform-origin:center;
    animation:banana-roll 1.15s linear infinite;
}
@keyframes banana-roll {
    0%   {transform:translateX(0) rotate(0deg);}
    50%  {transform:translateX(34px) rotate(180deg);}
    100% {transform:translateX(0) rotate(360deg);}
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LANGUAGE SELECTOR
# ─────────────────────────────────────────────
lang_col1, lang_col2, lang_col3 = st.columns([3, 1, 1])
with lang_col3:
    lang = st.selectbox("Language", ['EN', 'BM', 'ZH'], label_visibility='collapsed')
T = LANG_CONTENT[lang]

batch_text = {
    'EN': {
        'selected': 'images selected', 'analyse_all': 'Analyse all images', 'start_analysis': 'Start Analysis', 'images_label': 'Images', 'analysing': 'Analysing...',
        'combined': 'Download all reports (.zip)', 'individual': 'Individual reports',
        'result': 'Result', 'image': 'Image', 'batch_done': 'Batch analysis completed.',
        'disclaimer_title': 'Disclaimer',
        'disclaimer': 'BananaChain AI provides image-based decision support only. Results are not a confirmed diagnosis, grading certificate, or guaranteed market price. Follow registered product labels and local Department of Agriculture guidance.',
    },
    'BM': {
        'selected': 'imej dipilih', 'analyse_all': 'Analisis semua imej', 'start_analysis': 'Mula Analisis', 'images_label': 'Imej', 'analysing': 'Menganalisis...',
        'combined': 'Muat turun semua laporan (.zip)', 'individual': 'Laporan individu',
        'result': 'Keputusan', 'image': 'Imej', 'batch_done': 'Analisis kelompok selesai.',
        'disclaimer_title': 'Penafian',
        'disclaimer': 'BananaChain AI hanya menyediakan sokongan keputusan berasaskan imej. Hasil bukan diagnosis disahkan, sijil penggredan atau harga pasaran terjamin. Ikuti label produk berdaftar dan panduan Jabatan Pertanian tempatan.',
    },
    'ZH': {
        'selected': '张图片已选择', 'analyse_all': '分析全部图片', 'start_analysis': '开始分析', 'images_label': '张图片', 'analysing': '分析中...',
        'combined': '下载全部报告（ZIP）', 'individual': '单独报告',
        'result': '诊断结果', 'image': '图片', 'batch_done': '批量分析完成。',
        'disclaimer_title': '免责声明',
        'disclaimer': 'BananaChain AI 仅提供基于图片的决策支持。结果不代表正式确诊、品质认证或保证的市场价格。农药使用及农业措施请遵循已登记产品标签与当地农业部门指导。',
    },
}[lang]

# ─────────────────────────────────────────────
# SIDEBAR & HEADER
# ─────────────────────────────────────────────
with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_container_width=True)
    else:
        st.warning("Logo file not found: assets/logo.png")

    st.markdown("## BananaChain")
    st.caption("Chain the Future.")
    st.divider()

    reference_labels = {
        "EN": "References",
        "BM": "Rujukan",
        "ZH": "参考文献",
    }
    with st.expander(reference_labels[lang], expanded=False):
        for ref_index, source in enumerate(ALL_REFERENCE_SOURCES, start=1):
            st.markdown(f"**[{ref_index}]** {_apa_reference(source)}")

    st.divider()
    st.markdown(f"<div class='sidebar-disclaimer'>{batch_text['disclaimer']}</div>", unsafe_allow_html=True)

if TITLE_PATH.exists():
    st.image(str(TITLE_PATH), width=650)
else:
    st.markdown(f'<div class="main-title">{T["app_title"]}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-title">{T["app_sub"]}</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs([T['mode1_tab'], T['mode2_tab']])

# ══════════════════════════════════════════════
# MODE 1 — MULTI-IMAGE DISEASE DETECTION
# ══════════════════════════════════════════════
with tab1:
    st.subheader(T['mode1_title'])
    st.write(T['mode1_desc'])
    st.caption("Accepted input: a full banana leaf or a close-up of banana leaf symptoms. Other images are rejected before diagnosis.")

    left_col, right_col = st.columns([1, 1.6], gap="large")

    with left_col:
        uploaded_files = st.file_uploader(
            T['upload_leaf'], type=["jpg", "jpeg", "png"],
            accept_multiple_files=True, key="disease_upload_batch",
        )

        if uploaded_files:
            st.caption(f"{len(uploaded_files)} {batch_text['selected']}")
            preview_cols = st.columns(2)
            for index, file in enumerate(uploaded_files[:4]):
                with preview_cols[index % 2]:
                    st.image(Image.open(file).convert('RGB'), width=155)
                    st.caption(file.name)
            if len(uploaded_files) > 4:
                st.caption(f"+{len(uploaded_files) - 4} more")

        show_gradcam = st.checkbox(T['show_gradcam'], value=True, key="disease_batch_gradcam")

        # Original weather layout: directly visible in the left control column.
        st.markdown(f"**{T['weather_title']}**")
        city = st.text_input(T['weather_city'], value="Kuala Lumpur", key="weather_city_batch")
        if st.button(T['get_weather_btn'], key="weather_btn_batch"):
            with st.spinner("Fetching weather..."):
                st.session_state['weather'] = get_weather(city)

        if st.session_state.get('weather'):
            w = st.session_state['weather']
            st.markdown(f"""<div class="weather-box">
            🌍 <b>{w['city']}</b><br>
            🌡️ {w['temp']}°C &nbsp;|&nbsp; 💧 {w['humidity']}% humidity<br>
            ☁️ {w['description'].title()}
            </div>""", unsafe_allow_html=True)

        disease_count = len(uploaded_files) if uploaded_files else 0
        disease_button_label = batch_text['start_analysis']
        if disease_count > 1:
            disease_button_label = f"{batch_text['start_analysis']} ({disease_count} {batch_text['images_label']})"
        analyse_disease_batch = st.button(
            disease_button_label, use_container_width=True, type="primary",
            disabled=not uploaded_files, key="analyse_disease_batch",
        )

        if analyse_disease_batch:
            results = []
            loading_box = st.empty()
            loading_box.markdown(
                f"<div class='analysis-loader'><span>{batch_text['analysing']}</span><span class='rolling-banana'>🍌</span></div>",
                unsafe_allow_html=True,
            )
            try:
                model, info = load_disease_model()
                classes = info['classes']
                for index, uploaded in enumerate(uploaded_files):
                    image = Image.open(uploaded).convert('RGB')
                    is_valid, validation_message, validation_details = validate_target_image(image, "disease")
                    if not is_valid:
                        results.append({
                            'file_name': uploaded.name, 'unsupported': True,
                            'validation_message': validation_message,
                            'img_raw': np.array(image.resize((224, 224))),
                        })
                        continue
                    img_input, img_raw = preprocess_image(image)
                    preds = model.predict(img_input, verbose=0)[0]
                    pred_idx = int(np.argmax(preds))
                    pred_class = classes[pred_idx]
                    overlay = None
                    if show_gradcam:
                        try:
                            overlay = overlay_gradcam(img_raw, get_gradcam(model, img_input))
                        except Exception:
                            overlay = None
                    results.append({
                        'file_name': uploaded.name, 'pred_class': pred_class,
                        'confidence': float(preds[pred_idx]), 'preds': preds,
                        'classes': classes, 'img_raw': img_raw, 'overlay': overlay,
                    })
                st.session_state['disease_results'] = results
                loading_box.empty()
            except Exception as exc:
                loading_box.empty()
                st.error(f"Error: {exc}")

    with right_col:
        disease_results = st.session_state.get('disease_results', [])
        if disease_results:
            st.markdown(f"### {batch_text['result']} ({len(disease_results)})")
            disease_zip_reports = []
            generated_disease_reports = []

            for index, result in enumerate(disease_results):
                if result.get('unsupported'):
                    with st.expander(f"{index + 1}. {result['file_name']} — Unsupported image", expanded=(index == 0)):
                        c1, c2 = st.columns([1, 1.5])
                        c1.image(result['img_raw'], caption=result['file_name'], use_container_width=True)
                        c2.error(result['validation_message'])
                        c2.caption("This image was not sent to the disease model, and no diagnostic PDF was generated.")
                    continue
                pred_class = result['pred_class']
                disease = build_disease_display_data(pred_class)
                weather = st.session_state.get('weather')
                weather_entries = get_evidence_weather_advice(weather, pred_class, lang) if weather else []
                weather_entries = weather_entries or []
                treatment_entries = get_evidence_items(pred_class, 'immediate_actions', lang)
                prevention_entries = get_evidence_items(pred_class, 'prevention_tips', lang)
                monitoring_entries = get_evidence_items(pred_class, 'monitoring', lang)
                refs = evidence_reference_list_for_disease(pred_class, lang)
                report_weather_advice = [entry['text'] for entry in weather_entries]

                try:
                    diagnostic_pdf = build_disease_report(
                        report_scope="diagnostic", language=lang, result=result, disease=disease,
                        weather=weather, weather_advice=report_weather_advice, references=refs,
                        disclaimer=DISCLAIMER['disease'][lang], confidence_note=CONFIDENCE_NOTE[lang],
                        logo_path=LOGO_PATH,
                    )
                    full_pdf = build_disease_report(
                        report_scope="full", language=lang, result=result, disease=disease,
                        weather=weather, weather_advice=report_weather_advice, references=refs,
                        disclaimer=DISCLAIMER['disease'][lang], confidence_note=CONFIDENCE_NOTE[lang],
                        logo_path=LOGO_PATH,
                    )
                    disease_zip_reports.append((f"BananaChain_{safe_file_stem(result['file_name'])}_disease_report.pdf", full_pdf))
                    generated_disease_reports.append((diagnostic_pdf, full_pdf))
                except Exception as exc:
                    generated_disease_reports.append((None, None))

                title = f"{index + 1}. {result['file_name']} — {pred_class.title()} ({result['confidence'] * 100:.1f}%)"
                with st.expander(title, expanded=False):
                    st.markdown(f"""<div class="result-box {disease['box_class']}">
                    <h3>{pred_class.title()}</h3>
                    <b>{T['confidence']}:</b> {result['confidence']*100:.1f}% &nbsp;|&nbsp;
                    <b>{T['severity']}:</b> {disease['severity'][lang]}
                    </div>""", unsafe_allow_html=True)
                    st.caption(CONFIDENCE_NOTE[lang])

                    visual_count = 2 if result.get('overlay') is not None else 1
                    visual_cols = st.columns(visual_count)
                    visual_cols[0].image(result['img_raw'], caption=result['file_name'], use_container_width=True)
                    if result.get('overlay') is not None:
                        visual_cols[1].image(result['overlay'], caption="Highlighted suspected area", use_container_width=True, clamp=True)

                    with st.expander(T['what_is_it'], expanded=False):
                        st.info(disease['what_is_it'][lang])

                    with st.expander(T['ref_images'], expanded=False):
                        st.caption(T['ref_images_desc'])
                        ref_path = DISEASE_REF_IMAGES.get(pred_class.lower())
                        if ref_path and ref_path.exists():
                            ref_col1, ref_col2 = st.columns(2)
                            ref_col1.image(result['img_raw'], caption=T['your_image'], use_container_width=True)
                            ref_col2.image(str(ref_path), caption=f"{pred_class.title()} reference", use_container_width=True)
                        else:
                            st.info(DISEASE_REF_DESC.get(pred_class.lower(), "Reference image is unavailable for this class."))

                    if weather_entries:
                        with st.expander(T['spraying_advice'], expanded=False):
                            for entry in weather_entries:
                                st.markdown(f"- {clean_display_text(entry['text'])} {_citation_badges(entry['sources'], GLOBAL_REFERENCE_NUMBERS)}", unsafe_allow_html=True)

                    with st.expander(T['treatment'], expanded=False):
                        for entry in treatment_entries:
                            st.markdown(f"<div class='step-box'>{clean_display_text(entry['text'])} {_citation_badges(entry['sources'], GLOBAL_REFERENCE_NUMBERS)}</div>", unsafe_allow_html=True)

                    with st.expander(T['prevention'], expanded=False):
                        for entry in prevention_entries:
                            st.markdown(f"- {clean_display_text(entry['text'])} {_citation_badges(entry['sources'], GLOBAL_REFERENCE_NUMBERS)}", unsafe_allow_html=True)

                    with st.expander(T['monitoring'], expanded=False):
                        for entry in monitoring_entries:
                            st.markdown(f"- {clean_display_text(entry['text'])} {_citation_badges(entry['sources'], GLOBAL_REFERENCE_NUMBERS)}", unsafe_allow_html=True)

                    if disease.get('contact'):
                        with st.expander(T['get_help'], expanded=False):
                            st.write(clean_display_text(disease['contact']))

                    with st.expander(batch_text['individual'], expanded=False):
                        diagnostic_pdf, full_pdf = generated_disease_reports[index]
                        if diagnostic_pdf and full_pdf:
                            file_stem = safe_file_stem(result['file_name'])
                            d1, d2 = st.columns(2)
                            d1.download_button("Diagnostic PDF", diagnostic_pdf,
                                file_name=f"BananaChain_{file_stem}_diagnostic.pdf", mime="application/pdf",
                                use_container_width=True, key=f"disease_diag_{index}")
                            d2.download_button("Full Management PDF", full_pdf,
                                file_name=f"BananaChain_{file_stem}_full_report.pdf", mime="application/pdf",
                                use_container_width=True, key=f"disease_full_{index}")

                    with st.expander(T['probabilities'], expanded=False):
                        for cls, probability in zip(result['classes'], result['preds']):
                            st.progress(float(probability), text=f"{cls.title()}: {probability*100:.1f}%")

            if disease_zip_reports:
                reports_zip = build_reports_zip(disease_zip_reports)
                st.download_button(batch_text['combined'], reports_zip,
                    file_name="BananaChain_all_disease_reports.zip", mime="application/zip",
                    use_container_width=True, type="primary", key="combined_disease_zip")
        elif not uploaded_files:
            st.info(T['upload_prompt'])

    # ══════════════════════════════════════════════
# MODE 2 — MULTI-IMAGE RIPENESS & SUPPLY CHAIN
# ══════════════════════════════════════════════
with tab2:
    st.subheader(T['mode2_title'])
    st.write(T['mode2_desc'])
    st.caption("Accepted input: banana fruit only, including a single banana or a banana bunch. Other images are rejected before assessment.")

    left_col2, right_col2 = st.columns([1, 1.6], gap="large")

    with left_col2:
        uploaded_files2 = st.file_uploader(
            T['upload_banana'], type=["jpg", "jpeg", "png"],
            accept_multiple_files=True, key="ripeness_upload_batch",
        )
        if uploaded_files2:
            st.caption(f"{len(uploaded_files2)} {batch_text['selected']}")
            preview_cols2 = st.columns(2)
            for index, file in enumerate(uploaded_files2[:4]):
                with preview_cols2[index % 2]:
                    st.image(Image.open(file).convert('RGB'), width=155)
                    st.caption(file.name)
            if len(uploaded_files2) > 4:
                st.caption(f"+{len(uploaded_files2) - 4} more")

        user_type_options = USER_TYPES[lang]
        user_type = st.selectbox(T['user_type'], user_type_options, key="batch_user_type")
        user_type_idx = user_type_options.index(user_type)
        quantity = st.number_input(T['quantity'], min_value=1, max_value=500, value=10, step=1, key="batch_quantity")
        variety = st.selectbox(T['variety'], list(FAMA_PRICE.keys()), key="batch_variety")

        with st.expander("Observed Reference Price", expanded=False):
            with st.spinner("Fetching live price..."):
                live_price, price_date, price_range = fetch_banana_price(variety)
            st.write(f"{variety}: RM {live_price:.2f}/kg · {price_date or 'N/A'} · {price_range or 'N/A'}")
            st.caption("Reference data only; actual farm-gate, wholesale and retail prices may differ. Source: manamurah.com")

        ripeness_count = len(uploaded_files2) if uploaded_files2 else 0
        ripeness_button_label = batch_text['start_analysis']
        if ripeness_count > 1:
            ripeness_button_label = f"{batch_text['start_analysis']} ({ripeness_count} {batch_text['images_label']})"
        analyse_ripeness_batch = st.button(
            ripeness_button_label, use_container_width=True, type="primary",
            disabled=not uploaded_files2, key="analyse_ripeness_batch",
        )

        if analyse_ripeness_batch:
            results = []
            loading_box2 = st.empty()
            loading_box2.markdown(
                f"<div class='analysis-loader'><span>{batch_text['analysing']}</span><span class='rolling-banana'>🍌</span></div>",
                unsafe_allow_html=True,
            )
            try:
                model2, info2 = load_ripeness_model()
                classes2 = info2['classes']
                for index, uploaded in enumerate(uploaded_files2):
                    image2 = Image.open(uploaded).convert('RGB')
                    is_valid, validation_message, validation_details = validate_target_image(image2, "ripeness")
                    if not is_valid:
                        results.append({
                            'file_name': uploaded.name, 'unsupported': True,
                            'validation_message': validation_message,
                            'img_raw': np.array(image2.resize((224, 224))),
                        })
                        continue
                    img_input2, img_raw2 = preprocess_image(image2)
                    preds2 = model2.predict(img_input2, verbose=0)[0]
                    pred_idx2 = int(np.argmax(preds2))
                    pred_class2 = classes2[pred_idx2]
                    confidence2 = float(preds2[pred_idx2])
                    decision = get_supply_chain_decision(pred_class2, quantity, variety, user_type_idx, lang)
                    results.append({
                        'file_name': uploaded.name, 'pred_class': pred_class2,
                        'confidence': confidence2, 'preds': preds2, 'classes': classes2,
                        'decision': decision, 'quantity': quantity, 'variety': variety,
                        'user_type_idx': user_type_idx, 'img_raw': img_raw2,
                        'price_date': price_date, 'price_range': price_range,
                    })
                st.session_state['ripeness_results'] = results
                loading_box2.empty()
            except Exception as exc:
                loading_box2.empty()
                st.error(f"Error: {exc}")

    with right_col2:
        ripeness_results = st.session_state.get('ripeness_results', [])
        if ripeness_results:
            st.markdown(f"### {batch_text['result']} ({len(ripeness_results)})")
            ripeness_zip_reports = []
            report_refs = REFERENCES.get('ripeness_storage', []) + REFERENCES.get('market_price', [])
            storage_badges = _citation_badges(REFERENCES.get('ripeness_storage', []), GLOBAL_REFERENCE_NUMBERS)
            market_badges = _citation_badges(REFERENCES.get('market_price', []), GLOBAL_REFERENCE_NUMBERS)

            for index, result in enumerate(ripeness_results):
                if result.get('unsupported'):
                    with st.expander(f"{index + 1}. {result['file_name']} — Unsupported image", expanded=(index == 0)):
                        c1, c2 = st.columns([1, 1.5])
                        c1.image(result['img_raw'], caption=result['file_name'], use_container_width=True)
                        c2.error(result['validation_message'])
                        c2.caption("This image was not sent to the ripeness model, and no report was generated.")
                    continue
                decision = result['decision']
                pred_class = result['pred_class']
                base_price = get_fama_price(result['variety'])
                full_value = round(result['quantity'] * base_price, 2)
                salvage = decision['salvage_value']
                loss = round(full_value - salvage, 2) if full_value > salvage else 0
                price_info = {
                    'observed_price': base_price, 'date': result.get('price_date'),
                    'range': result.get('price_range'), 'full_value': full_value,
                    'recoverable_value': salvage, 'potential_loss': loss,
                }
                selected_user_type = user_type_options[result['user_type_idx']]
                pdfs = {}
                try:
                    for scope, name in [('assessment', 'quality'), ('recommendations', 'recommendations'), ('price', 'price'), ('full', 'full')]:
                        pdfs[name] = build_ripeness_report(
                            report_scope=scope, language=lang, result=result, decision=decision,
                            user_type=selected_user_type, price_info=price_info, references=report_refs,
                            disclaimer=DISCLAIMER['ripeness'][lang], confidence_note=CONFIDENCE_NOTE[lang],
                            logo_path=LOGO_PATH,
                        )
                    ripeness_zip_reports.append((f"BananaChain_{safe_file_stem(result['file_name'])}_complete.pdf", pdfs['full']))
                except Exception:
                    pdfs = {}

                title = f"{index + 1}. {result['file_name']} — {decision['status'][lang]} ({result['confidence'] * 100:.1f}%)"
                with st.expander(title, expanded=False):
                    st.markdown(f"""<div class="result-box {decision['box_class']}">
                    <h3>{decision['status'][lang]}</h3>
                    <b>{T['confidence']}:</b> {result['confidence']*100:.1f}% &nbsp;|&nbsp;
                    <b>{T['shelf_life']}:</b> {decision['shelf_life']} &nbsp;|&nbsp;
                    <b>{T['urgency']}:</b> {decision['urgency'][lang]}
                    </div>""", unsafe_allow_html=True)
                    st.caption(CONFIDENCE_NOTE[lang])

                    image_col, metric_col = st.columns([1, 1.3])
                    image_col.image(result['img_raw'], caption=result['file_name'], use_container_width=True)
                    with metric_col:
                        m1, m2 = st.columns(2)
                        m1.metric(T['ripeness'], pred_class.title())
                        m2.metric(T['est_value'], f"RM {decision['estimated_value']}")
                    with st.expander(T['what_it_means'], expanded=False):
                        st.info(decision['what_it_means'][lang])

                    with st.expander(f"{T['actions']} ({selected_user_type})", expanded=False):
                        for action in decision['actions_for_user'][lang]:
                            lower_action = action.lower()
                            uses_market = any(term in lower_action for term in ['rm ', 'price', 'harga', '售价', '定价', 'discount', '折扣', 'diskaun', 'value', 'nilai'])
                            badges = market_badges if uses_market else storage_badges
                            st.markdown(f"<div class='step-box'>{clean_display_text(action)} {badges}</div>", unsafe_allow_html=True)

                    with st.expander(T['storage'], expanded=False):
                        for tip in decision['storage'][lang]:
                            st.markdown(f"- {clean_display_text(tip)} {storage_badges}", unsafe_allow_html=True)

                    with st.expander(T['financial'], expanded=False):
                        f1, f2, f3 = st.columns(3)
                        f1.metric(T['full_value'], f"RM {full_value}")
                        f2.metric(T['recoverable'], f"RM {salvage}")
                        f3.metric(T['potential_loss'], f"RM {loss}")

                    if pdfs:
                        with st.expander(batch_text['individual'], expanded=False):
                            file_stem = safe_file_stem(result['file_name'])
                            p1, p2 = st.columns(2)
                            p1.download_button("Quality Assessment PDF", pdfs['quality'],
                                file_name=f"BananaChain_{file_stem}_quality.pdf", mime="application/pdf",
                                use_container_width=True, key=f"quality_{index}")
                            p2.download_button("Recommendation PDF", pdfs['recommendations'],
                                file_name=f"BananaChain_{file_stem}_recommendations.pdf", mime="application/pdf",
                                use_container_width=True, key=f"recommend_{index}")
                            p3, p4 = st.columns(2)
                            p3.download_button("Price Reference PDF", pdfs['price'],
                                file_name=f"BananaChain_{file_stem}_price.pdf", mime="application/pdf",
                                use_container_width=True, key=f"price_{index}")
                            p4.download_button("Complete Report PDF", pdfs['full'],
                                file_name=f"BananaChain_{file_stem}_complete.pdf", mime="application/pdf",
                                use_container_width=True, key=f"complete_{index}")

                    with st.expander(T['probabilities'], expanded=False):
                        display_names = {'unripe': 'Unripe', 'freshripe': 'Fresh Ripe', 'rotten': 'Rotten/Overripe'}
                        for cls, probability in zip(result['classes'], result['preds']):
                            st.progress(float(probability), text=f"{display_names.get(cls, cls)}: {probability*100:.1f}%")

            if ripeness_zip_reports:
                reports_zip = build_reports_zip(ripeness_zip_reports)
                st.download_button(batch_text['combined'], reports_zip,
                    file_name="BananaChain_all_ripeness_supply_chain_reports.zip", mime="application/zip",
                    use_container_width=True, type="primary", key="combined_ripeness_zip")
        elif not uploaded_files2:
            st.info(T['upload_prompt2'])
