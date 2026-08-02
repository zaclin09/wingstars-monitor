"""Wing Stars 26 位成員 + 台鋼 4 球團官方 Threads 帳號清單。

資料來源：
- cpblgirls.tw 官方名單
- PTT CheerGirlsTW 2025/03 年鑑
- 補查玖玖 (bubu_520)、Mingo (_min_go)、圈圈 (alien_circle_00)
- 球團官方 (2026/04 補):
    雄鷹 @tsg_hawks  獵鷹 @tainan_tsg_ghosthawks
    天鷹 @tsg_skyhawks  Wing Stars @wing_stars_official
"""

# 球團官方帳號 (group = "球團官方")
TEAM_ACCOUNTS: list[dict] = [
    {"id": "TM-HAWK", "name": "台鋼雄鷹（棒球）",  "username": "tsg_hawks"},
    {"id": "TM-GHST", "name": "台鋼獵鷹（籃球）",  "username": "tainan_tsg_ghosthawks"},
    {"id": "TM-SKY",  "name": "台鋼天鷹（排球）",  "username": "tsg_skyhawks"},
    {"id": "TM-WS",   "name": "Wing Stars 官方",   "username": "wing_stars_official"},
]


WINGSTARS_ACCOUNTS: list[dict] = [
    {"id": "WS-02", "jersey": "2",  "name": "安芝儇 Jihyun",   "username": "wlgus2qh"},
    {"id": "WS-03", "jersey": "3",  "name": "米妮 Minnie",     "username": "nacccni"},
    {"id": "WS-05", "jersey": "5",  "name": "恬魚 Tianyu",     "username": "_940905_"},
    {"id": "WS-06", "jersey": "6",  "name": "尼莫 Nemo",       "username": "vanessa_ooi_99"},
    {"id": "WS-07", "jersey": "7",  "name": "昆昆",            "username": "yu_jun.hu"},
    {"id": "WS-08", "jersey": "8",  "name": "米亞 Mia",        "username": "mia___1117"},
    {"id": "WS-10", "jersey": "10", "name": "李樂 Luna",       "username": "lunelile"},
    {"id": "WS-15", "jersey": "15", "name": "千千 Chien",      "username": "iamchien_chien"},
    {"id": "WS-16", "jersey": "16", "name": "JC",              "username": "jiayin_ching"},
    {"id": "WS-17", "jersey": "17", "name": "ET",              "username": "etetet"},
    {"id": "WS-18", "jersey": "18", "name": "黃澄澄",          "username": "2005_2_11"},
    {"id": "WS-19", "jersey": "19", "name": "妡0",             "username": "for_you_1105"},
    {"id": "WS-20", "jersey": "20", "name": "艾琳 Irene",      "username": "xnirene_"},
    {"id": "WS-22", "jersey": "22", "name": "一粒 Ili",        "username": "ilixoxov"},
    {"id": "WS-23", "jersey": "23", "name": "瑈瑈 Rou",        "username": "y.rouu_"},
    {"id": "WS-33", "jersey": "33", "name": "林浠",            "username": "llyincc__"},
    {"id": "WS-39", "jersey": "39", "name": "毛毛 Momo",       "username": "_momo_.39"},
    {"id": "WS-52", "jersey": "52", "name": "筱雯 Melody",     "username": "cx_moon_"},
    {"id": "WS-57", "jersey": "57", "name": "芃芃 Peng",       "username": "_peng.7_"},
    {"id": "WS-62", "jersey": "62", "name": "螢螢 Joanna",     "username": "yinnng_0522"},
    {"id": "WS-66", "jersey": "66", "name": "會晴 Bella",      "username": "chiiingnapa"},
    {"id": "WS-75", "jersey": "75", "name": "芋頭 Taro",       "username": "tarotaro__9"},
    {"id": "WS-84", "jersey": "84", "name": "Nina",            "username": "nina_84_na"},
    {"id": "WS-90", "jersey": "90", "name": "朴旻曙 Mingo",    "username": "_min_go"},
    {"id": "WS-99", "jersey": "99", "name": "玖玖 Bubu",       "username": "bubu_520"},
    {"id": "WS-00", "jersey": "00", "name": "圈圈 Eileen",     "username": "alien_circle_00"},
]


def load_wingstars_accounts() -> list[dict]:
    """26 位 Wing Stars 啦啦隊員 + 4 個球團官方帳號。"""
    members = [
        {
            "id": a["id"],
            "name": a["name"],
            "username": a["username"],
            "display_name": a["name"],
            "group": "Wing Stars",
            "jersey": a["jersey"],
        }
        for a in WINGSTARS_ACCOUNTS
    ]
    teams = [
        {
            "id": t["id"],
            "name": t["name"],
            "username": t["username"],
            "display_name": t["name"],
            "group": "球團官方",
            "jersey": "",
        }
        for t in TEAM_ACCOUNTS
    ]
    return members + teams


if __name__ == "__main__":
    accts = load_wingstars_accounts()
    print(f"Loaded {len(accts)} accounts total:")
    for a in accts:
        tag = f"#{a['jersey']:>2}" if a['jersey'] else "    "
        print(f"  [{a['group']:<10}] {tag}  {a['name']:<22}  @{a['username']}")
