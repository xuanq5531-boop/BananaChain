"""Evidence-audited recommendation module for BananaChain AI.
Last audited: 2026-07-22
Version: 2.0 — weather-rule and source-traceability revision.

Evidence A = directly supported by the linked source.
Evidence B = cautious synthesis/operational interpretation.
"""

REFERENCES = {
    "FAO_PLANTING": {
        "organisation": "FAO",
        "title": "Quality declared planting material",
        "url": "https://www.fao.org/4/i1195e/i1195e00.htm",
    },
    "PROMUSA_BLACK": {
        "organisation": "ProMusa",
        "title": "Black leaf streak",
        "url": "https://www.promusa.org/Black%2Bleaf%2Bstreak",
    },
    "PROMUSA_DELEAFING": {
        "organisation": "ProMusa",
        "title": "Deleafing",
        "url": "https://www.promusa.org/deleafing",
    },
    "PROMUSA_YELLOW": {
        "organisation": "ProMusa",
        "title": "Sigatoka leaf spot",
        "url": "https://www.promusa.org/Sigatoka%2Bleaf%2Bspot",
    },
    "PROMUSA_FUSARIUM": {
        "organisation": "ProMusa",
        "title": "Fusarium wilt",
        "url": "https://www.promusa.org/Fusarium%2Bwilt",
    },
    "PROMUSA_TR4": {
        "organisation": "ProMusa",
        "title": "Tropical race 4 (TR4)",
        "url": "https://www.promusa.org/Tropical%2Brace%2B4%2B-%2BTR4",
    },
    "PROMUSA_CORDANA": {
        "organisation": "ProMusa",
        "title": "Cordana leaf spot",
        "url": "https://www.promusa.org/Cordana%2Bleaf%2Bspot",
    },
    "PROMUSA_WATER": {
        "organisation": "ProMusa",
        "title": "Water management",
        "url": "https://www.promusa.org/Water%2Bmanagement",
    },
    "FRAC_BANANA": {
        "organisation": "FRAC",
        "title": "Banana Working Group",
        "url": "https://www.frac.info/frac-teams/working-groups/banana-group/",
    },
    "EPPO_RALSTONIA_MY": {
        "organisation": "EPPO",
        "title": "Ralstonia solanacearum species complex in Malaysia",
        "url": "https://gd.eppo.int/taxon/RALSSO/distribution/MY",
    },
    "IPPC_MALAYSIA": {
        "organisation": "IPPC / Malaysia NPPO",
        "title": "Occurrence of banana bacterial wilt in Malaysia",
        "url": "https://www.ippc.int/en/countries/malaysia/pestreports/2016/09/occurrence-of-blood-disease-of-banana-ralstonia-solanacearum-species-complex-in-malaysia-in-malaysia-1/",
    },
}


def rec(en, bm, zh, sources, level="A"):
    return {
        "text": {"EN": en, "BM": bm, "ZH": zh},
        "source_ids": sources,
        "evidence_level": level,
    }


DISEASE_INFO = {
    "healthy": {
        "severity": {"EN": "None detected", "BM": "Tiada dikesan", "ZH": "未检测到"},
        "what_is_it": {
            "EN": "The uploaded image was classified as healthy. This is an AI screening result, not confirmation that the whole plant is disease-free.",
            "BM": "Imej diklasifikasikan sebagai sihat. Ini ialah saringan AI, bukan pengesahan bahawa seluruh pokok bebas penyakit.",
            "ZH": "上传图像被分类为健康。这是AI筛查结果，并不代表整株植物已确认无病。",
        },
        "immediate_actions": [
            rec("No disease-specific treatment is indicated from this image alone.", "Tiada rawatan khusus penyakit ditunjukkan berdasarkan imej ini sahaja.", "仅凭此图像，目前无需采取针对特定病害的治疗。", ["FAO_PLANTING"], "B"),
            rec("Continue routine visual inspection and record new spots, streaks, wilting or internal discolouration.", "Teruskan pemeriksaan visual berkala dan rekodkan bintik, jalur, layu atau perubahan warna dalaman yang baharu.", "继续定期目视检查，并记录新出现的斑点、条纹、萎蔫或内部变色。", ["PROMUSA_BLACK", "PROMUSA_FUSARIUM"], "B"),
        ],
        "prevention_tips": [
            rec("Use certified or otherwise verified disease-free planting material where available.", "Gunakan bahan tanaman yang diperakui atau disahkan bebas penyakit jika tersedia.", "在条件允许时，使用经认证或核实的无病种植材料。", ["FAO_PLANTING", "PROMUSA_FUSARIUM"]),
            rec("Maintain suitable drainage and avoid prolonged waterlogging.", "Kekalkan saliran yang sesuai dan elakkan takungan air berpanjangan.", "保持良好排水，避免长期积水。", ["PROMUSA_WATER"]),
        ],
        "monitoring": [
            rec("Inspect regularly, especially after prolonged wet or humid periods; follow local guidance for inspection frequency.", "Periksa secara berkala, terutamanya selepas tempoh basah atau lembap; ikut panduan tempatan untuk kekerapan.", "定期检查，尤其是在持续潮湿或高湿天气之后；检查频率应依据当地指导。", ["PROMUSA_BLACK", "PROMUSA_WATER"], "B"),
        ],
    },

    "black sigatoka": {
        "severity": {"EN": "High", "BM": "Tinggi", "ZH": "高"},
        "what_is_it": {
            "EN": "Black Sigatoka is a fungal leaf disease that reduces functional leaf area, yield and fruit green life.",
            "BM": "Sigatoka Hitam ialah penyakit kulat daun yang mengurangkan kawasan daun berfungsi, hasil dan jangka hijau buah.",
            "ZH": "黑条叶斑病是一种真菌性叶病，会减少有效叶面积、降低产量并缩短果实青熟期。",
        },
        "immediate_actions": [
            rec("Confirm the field diagnosis with a trained crop adviser because symptoms can overlap with other leaf spots.", "Sahkan diagnosis ladang dengan pegawai tanaman terlatih kerana simptom boleh bertindih dengan penyakit bintik daun lain.", "由于症状可能与其他叶斑病重叠，应请受过训练的农作物顾问进行田间确认。", ["PROMUSA_BLACK"], "B"),
            rec("Remove infected leaf parts or leaves through sanitary deleafing while preserving enough functional leaf area.", "Buang bahagian daun atau daun dijangkiti melalui pemangkasan sanitasi sambil mengekalkan kawasan daun berfungsi yang mencukupi.", "进行卫生性去叶，移除受感染叶片部分或整片叶，同时保留足够的有效叶面积。", ["PROMUSA_DELEAFING"]),
            rec("Where chemical control is justified, use only a locally registered fungicide according to its label and resistance-management guidance.", "Jika kawalan kimia diperlukan, gunakan hanya fungisid berdaftar tempatan mengikut label dan panduan pengurusan rintangan.", "如确需化学防治，只能依据当地登记产品标签和抗药性管理指南使用杀菌剂。", ["PROMUSA_BLACK", "FRAC_BANANA"]),
        ],
        "prevention_tips": [
            rec("Combine deleafing, suitable plant density, nutrition and water management.", "Gabungkan pemangkasan daun, kepadatan tanaman yang sesuai, pemakanan dan pengurusan air.", "结合去叶、合理种植密度、营养和水分管理。", ["PROMUSA_BLACK", "PROMUSA_WATER"]),
            rec("Do not repeatedly rely on the same fungicide mode of action.", "Jangan bergantung berulang kali pada cara tindakan fungisid yang sama.", "不要重复依赖同一杀菌剂作用机制。", ["FRAC_BANANA"]),
        ],
        "monitoring": [
            rec("Inspect all plants, including suckers, and record disease progression before deciding whether treatment is needed.", "Periksa semua pokok termasuk sulur dan rekod perkembangan penyakit sebelum memutuskan keperluan rawatan.", "检查所有植株，包括吸芽，并记录病害进展后再决定是否需要处理。", ["PROMUSA_DELEAFING"]),
        ],
    },

    "yellow sigatoka": {
        "severity": {"EN": "Moderate", "BM": "Sederhana", "ZH": "中等"},
        "what_is_it": {
            "EN": "Yellow Sigatoka is a fungal leaf-spot disease. Its symptoms may resemble black Sigatoka, so field confirmation is important.",
            "BM": "Sigatoka Kuning ialah penyakit bintik daun kulat. Simptomnya boleh menyerupai Sigatoka Hitam, maka pengesahan ladang adalah penting.",
            "ZH": "黄条叶斑病是一种真菌性叶斑病，其症状可能与黑条叶斑病相似，因此需要田间确认。",
        },
        "immediate_actions": [
            rec("Remove heavily affected leaf tissue through sanitary deleafing while retaining sufficient healthy leaf area.", "Buang tisu daun yang terjejas teruk melalui pemangkasan sanitasi sambil mengekalkan kawasan daun sihat yang mencukupi.", "通过卫生性去叶移除严重受害组织，同时保留足够的健康叶面积。", ["PROMUSA_YELLOW", "PROMUSA_DELEAFING"]),
            rec("If fungicide treatment is needed, use only locally registered products according to the label.", "Jika rawatan fungisid diperlukan, gunakan hanya produk berdaftar tempatan mengikut label.", "如需杀菌剂处理，只能按照当地登记产品标签使用。", ["PROMUSA_YELLOW", "FRAC_BANANA"]),
        ],
        "prevention_tips": [
            rec("Combine deleafing and chemical control where appropriate rather than relying on one measure.", "Gabungkan pemangkasan daun dan kawalan kimia jika sesuai, bukan bergantung pada satu langkah sahaja.", "在适当情况下结合去叶和化学防治，不要只依赖单一措施。", ["PROMUSA_YELLOW"]),
            rec("Rotate fungicide modes of action according to FRAC and product-label guidance.", "Putarkan cara tindakan fungisid mengikut panduan FRAC dan label produk.", "依据FRAC和产品标签指导轮换杀菌剂作用机制。", ["PROMUSA_YELLOW", "FRAC_BANANA"]),
        ],
        "monitoring": [
            rec("Monitor disease development and weather conditions; use local forecasting support where available.", "Pantau perkembangan penyakit dan keadaan cuaca; gunakan sokongan ramalan tempatan jika tersedia.", "监测病害发展与天气条件，并在可用时采用当地预测支持。", ["PROMUSA_YELLOW"]),
        ],
    },

    "fusarium wilt": {
        "severity": {"EN": "Critical", "BM": "Kritikal", "ZH": "严重"},
        "what_is_it": {
            "EN": "Fusarium wilt is a soil-borne vascular disease spread through infected planting material, infested soil and water.",
            "BM": "Layu Fusarium ialah penyakit vaskular bawaan tanah yang merebak melalui bahan tanaman dijangkiti, tanah tercemar dan air.",
            "ZH": "香蕉枯萎病是一种土传维管束病害，可通过带病种植材料、受污染土壤和水传播。",
        },
        "immediate_actions": [
            rec("Do not rely on foliar fungicide sprays; Fusarium wilt cannot be controlled with fungicides.", "Jangan bergantung pada semburan fungisid daun; Layu Fusarium tidak dapat dikawal dengan fungisid.", "不要依赖叶面杀菌剂；香蕉枯萎病无法通过杀菌剂控制。", ["PROMUSA_FUSARIUM", "PROMUSA_TR4"]),
            rec("Restrict movement of soil, water, tools, footwear and planting material from the suspected area.", "Hadkan pergerakan tanah, air, alatan, kasut dan bahan tanaman dari kawasan yang disyaki.", "限制疑似区域的土壤、水、工具、鞋靴和种植材料移动。", ["PROMUSA_FUSARIUM", "PROMUSA_TR4"]),
            rec("Contact the local Department of Agriculture or plant-health authority for confirmation and site-specific containment instructions.", "Hubungi Jabatan Pertanian atau pihak kesihatan tumbuhan tempatan untuk pengesahan dan arahan pembendungan khusus tapak.", "联系当地农业部门或植物卫生机构进行确认并获得现场控制指示。", ["PROMUSA_TR4"], "B"),
        ],
        "prevention_tips": [
            rec("Use certified tissue-culture plantlets or verified clean planting material.", "Gunakan anak benih kultur tisu yang diperakui atau bahan tanaman bersih yang disahkan.", "使用经认证的组织培养苗或经核实的无病种植材料。", ["PROMUSA_FUSARIUM", "FAO_PLANTING"]),
            rec("Prevent contaminated soil from moving on vehicles, tools and footwear.", "Cegah tanah tercemar daripada dipindahkan melalui kenderaan, alatan dan kasut.", "防止受污染土壤通过车辆、工具和鞋靴传播。", ["PROMUSA_FUSARIUM"]),
            rec("Use resistant cultivars where suitable and recommended locally.", "Gunakan kultivar tahan jika sesuai dan disyorkan secara tempatan.", "在适合且获得当地建议时使用抗病品种。", ["PROMUSA_FUSARIUM", "PROMUSA_TR4"]),
        ],
        "monitoring": [
            rec("Mark and isolate suspected plants and monitor nearby plants for yellowing, wilting and internal vascular discolouration.", "Tandakan dan asingkan pokok disyaki serta pantau pokok berdekatan untuk kekuningan, layu dan perubahan warna vaskular dalaman.", "标记并隔离疑似植株，监测附近植株是否出现黄化、萎蔫和内部维管束变色。", ["PROMUSA_FUSARIUM"], "B"),
        ],
    },

    "banana moko disease": {
        "severity": {"EN": "Critical", "BM": "Kritikal", "ZH": "严重"},
        "what_is_it": {
            "EN": "Moko disease is a bacterial wilt associated with the Ralstonia solanacearum species complex. Official confirmation is important.",
            "BM": "Penyakit Moko ialah layu bakteria yang dikaitkan dengan kompleks spesies Ralstonia solanacearum. Pengesahan rasmi adalah penting.",
            "ZH": "摩哥病是一种与青枯雷尔氏菌复合种相关的细菌性萎蔫病。官方确认非常重要。",
        },
        "immediate_actions": [
            rec("Treat this as a suspected bacterial wilt and contact the local plant-health authority before moving or destroying plant material.", "Anggap ini sebagai layu bakteria yang disyaki dan hubungi pihak kesihatan tumbuhan tempatan sebelum memindahkan atau memusnahkan bahan tanaman.", "将其视为疑似细菌性萎蔫病；在移动或销毁植物材料前联系当地植物卫生机构。", ["EPPO_RALSTONIA_MY", "IPPC_MALAYSIA"], "B"),
            rec("Restrict movement of potentially contaminated plants, soil, water, tools and footwear from the affected area.", "Hadkan pergerakan pokok, tanah, air, alatan dan kasut yang berpotensi tercemar dari kawasan terjejas.", "限制可能受污染的植株、土壤、水、工具和鞋靴离开受影响区域。", ["EPPO_RALSTONIA_MY", "IPPC_MALAYSIA"], "B"),
            rec("Do not recommend antibiotics, insecticides or chemical eradication from an image prediction; follow official containment instructions.", "Jangan cadangkan antibiotik, racun serangga atau penghapusan kimia berdasarkan ramalan imej; ikut arahan pembendungan rasmi.", "不要依据图像预测建议抗生素、杀虫剂或化学根除；应遵循官方控制指示。", ["IPPC_MALAYSIA"], "B"),
        ],
        "prevention_tips": [
            rec("Use verified clean planting material and maintain strict hygiene for tools, footwear and field movement.", "Gunakan bahan tanaman bersih yang disahkan dan kekalkan kebersihan ketat bagi alatan, kasut dan pergerakan ladang.", "使用经核实的无病种植材料，并对工具、鞋靴和田间流动实施严格卫生管理。", ["EPPO_RALSTONIA_MY", "IPPC_MALAYSIA"], "B"),
        ],
        "monitoring": [
            rec("Record suspected plant locations and inspect nearby plants for wilt, leaf necrosis, bacterial ooze or internal discolouration.", "Rekod lokasi pokok disyaki dan periksa pokok berdekatan untuk layu, nekrosis daun, lelehan bakteria atau perubahan warna dalaman.", "记录疑似植株位置，并检查附近植株是否出现萎蔫、叶坏死、细菌溢脓或内部变色。", ["IPPC_MALAYSIA"], "B"),
        ],
    },

    "cordana": {
        "severity": {"EN": "Usually low", "BM": "Biasanya rendah", "ZH": "通常较低"},
        "what_is_it": {
            "EN": "Cordana leaf spot is a common fungal leaf disease that generally has little production impact and may occur as a secondary invader.",
            "BM": "Bintik daun Cordana ialah penyakit kulat daun yang biasa, lazimnya memberi sedikit kesan pengeluaran dan boleh berlaku sebagai penceroboh sekunder.",
            "ZH": "科达纳叶斑病是一种常见真菌性叶病，通常对生产影响较小，也可能继发侵染。",
        },
        "immediate_actions": [
            rec("Confirm that the lesion is Cordana and not another leaf-spot disease because visual symptoms can overlap.", "Sahkan bahawa lesi ialah Cordana dan bukannya penyakit bintik daun lain kerana simptom visual boleh bertindih.", "由于视觉症状可能重叠，应确认病斑确为科达纳叶斑病，而非其他叶斑病。", ["PROMUSA_CORDANA"], "B"),
            rec("Remove severely damaged leaf tissue when practical and avoid unnecessary chemical treatment for mild cases.", "Buang tisu daun yang rosak teruk jika praktikal dan elakkan rawatan kimia yang tidak perlu bagi kes ringan.", "在可行时移除严重受损叶组织；轻微病例应避免不必要的化学处理。", ["PROMUSA_CORDANA"], "B"),
            rec("If disease becomes significant, obtain local crop-adviser guidance and use only a registered product according to its label.", "Jika penyakit menjadi ketara, dapatkan nasihat pegawai tanaman tempatan dan gunakan hanya produk berdaftar mengikut label.", "如病害变得明显，应咨询当地农作物顾问，并仅依据登记产品标签使用药剂。", ["PROMUSA_CORDANA"], "B"),
        ],
        "prevention_tips": [
            rec("Reduce plant stress by maintaining suitable nutrition, drainage and crop hygiene.", "Kurangkan tekanan pokok dengan mengekalkan pemakanan, saliran dan kebersihan tanaman yang sesuai.", "通过合理营养、排水和作物卫生管理减轻植株胁迫。", ["PROMUSA_CORDANA", "PROMUSA_WATER"], "B"),
        ],
        "monitoring": [
            rec("Monitor whether lesions remain limited or enlarge with other diseases, especially under humid conditions.", "Pantau sama ada lesi kekal terhad atau membesar bersama penyakit lain, terutamanya dalam keadaan lembap.", "监测病斑是否保持局限，或在潮湿条件下与其他病害共同扩大。", ["PROMUSA_CORDANA"]),
        ],
    },
}

GENERAL_DISCLAIMER = {
    "EN": "This system provides image-based decision support, not a confirmed diagnosis. Follow Malaysian Department of Agriculture advice and registered product labels.",
    "BM": "Sistem ini menyediakan sokongan keputusan berdasarkan imej, bukan diagnosis yang disahkan. Ikuti nasihat Jabatan Pertanian Malaysia dan label produk berdaftar.",
    "ZH": "本系统提供基于图像的决策支持，并非正式确诊。请遵循马来西亚农业部门指导及登记产品标签。",
}


def get_items(disease, section, lang="EN"):
    key = disease.replace("_", " ").lower().strip()
    records = DISEASE_INFO.get(key, {}).get(section, [])
    result = []
    for record in records:
        result.append({
            "text": record["text"][lang],
            "evidence_level": record["evidence_level"],
            "sources": [REFERENCES[s] for s in record["source_ids"] if s in REFERENCES],
        })
    return result


def render_evidence_items(st, disease, section, lang="EN"):
    for entry in get_items(disease, section, lang):
        st.markdown(f"- {entry['text']}")
        links = " · ".join(
            f"[{s['organisation']} — {s['title']}]({s['url']})" for s in entry["sources"]
        )
        st.caption(f"Evidence {entry['evidence_level']} · {links}")


def get_weather_advice(weather, disease, lang="EN"):
    """Conservative weather advice without universal spray thresholds."""
    if not weather:
        return []
    rain = bool(weather.get("rain"))
    humidity = weather.get("humidity")
    key = disease.replace("_", " ").lower().strip()

    if key in {"black sigatoka", "yellow sigatoka"}:
        if rain:
            records = [rec(
                "Wet conditions favour Sigatoka development and may reduce spray suitability. Delay pesticide application unless the registered label and local advice permit it.",
                "Keadaan basah menggalakkan perkembangan Sigatoka dan mungkin tidak sesuai untuk semburan. Tangguhkan penggunaan racun perosak kecuali label berdaftar dan nasihat tempatan membenarkannya.",
                "潮湿条件有利于叶斑病发展，也可能不适合施药。除非登记标签和当地指导允许，否则应推迟农药施用。",
                ["PROMUSA_BLACK", "PROMUSA_YELLOW"], "B")]
        elif humidity is not None and humidity >= 80:
            records = [rec(
                "High humidity may increase leaf-wetness risk. Increase field scouting and use a locally appropriate management or forecasting programme.",
                "Kelembapan tinggi boleh meningkatkan risiko daun basah. Tingkatkan pemerhatian ladang dan gunakan program pengurusan atau ramalan yang sesuai.",
                "高湿度可能增加叶面湿润风险。应加强田间巡查，并采用适合当地的管理或预测方案。",
                ["PROMUSA_BLACK", "PROMUSA_YELLOW", "PROMUSA_WATER"], "B")]
        else:
            records = [rec(
                "Check the local forecast and product label before any application; temperature and humidity alone are insufficient to determine spray suitability.",
                "Semak ramalan tempatan dan label produk sebelum sebarang penggunaan; suhu dan kelembapan sahaja tidak mencukupi untuk menentukan kesesuaian semburan.",
                "施药前应查看当地天气预报和产品标签；仅凭温度和湿度无法判断是否适合喷药。",
                ["FRAC_BANANA"], "B")]

    elif key == "fusarium wilt":
        records = [rec(
            "Weather does not make foliar fungicide effective against Fusarium wilt. Focus on preventing movement of contaminated soil, water, tools and planting material.",
            "Cuaca tidak menjadikan semburan fungisid daun berkesan terhadap Layu Fusarium. Fokus pada pencegahan pergerakan tanah, air, alatan dan bahan tanaman tercemar.",
            "天气不会使叶面杀菌剂对香蕉枯萎病有效。重点应防止受污染土壤、水、工具和种植材料传播。",
            ["PROMUSA_FUSARIUM", "PROMUSA_TR4"])]
        if rain:
            records.append(rec(
                "Rain and runoff may move contaminated soil or water; strengthen access control and drainage precautions.",
                "Hujan dan aliran permukaan boleh memindahkan tanah atau air tercemar; perketat kawalan akses dan langkah saliran.",
                "降雨和径流可能携带受污染的土壤或水；应加强出入控制和排水防范。",
                ["PROMUSA_FUSARIUM", "PROMUSA_WATER"], "B"))

    elif key == "banana moko disease":
        records = [rec(
            "Do not infer insecticide or antibiotic treatment from current weather. Maintain containment and seek official plant-health advice.",
            "Jangan membuat kesimpulan rawatan racun serangga atau antibiotik berdasarkan cuaca semasa. Kekalkan pembendungan dan dapatkan nasihat rasmi.",
            "不要根据当前天气推断应使用杀虫剂或抗生素。应维持隔离控制并寻求官方指导。",
            ["EPPO_RALSTONIA_MY", "IPPC_MALAYSIA"], "B")]

    elif key == "cordana":
        records = [rec(
            "Humid conditions may favour enlargement of Cordana lesions. Monitor lesion development and reduce plant stress.",
            "Keadaan lembap boleh menggalakkan pembesaran lesi Cordana. Pantau perkembangan lesi dan kurangkan tekanan pokok.",
            "潮湿条件可能促进科达纳病斑扩大。应监测病斑发展并减轻植株胁迫。",
            ["PROMUSA_CORDANA"], "A" if (rain or (humidity is not None and humidity >= 80)) else "B")]

    else:
        records = [rec(
            "Continue routine inspection and maintain suitable drainage and crop hygiene.",
            "Teruskan pemeriksaan berkala dan kekalkan saliran serta kebersihan tanaman yang sesuai.",
            "继续定期检查，并保持适当排水和作物卫生。",
            ["PROMUSA_WATER"], "B")]

    return [{
        "text": r["text"][lang],
        "evidence_level": r["evidence_level"],
        "sources": [REFERENCES[s] for s in r["source_ids"] if s in REFERENCES],
    } for r in records]
