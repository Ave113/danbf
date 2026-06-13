import logging
import os
import json
import sqlite3
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)
from lunar_python import Solar

TZ_VN = ZoneInfo("Asia/Ho_Chi_Minh")  # UTC+7

def now_vn() -> datetime:
    """Tra ve datetime hien tai theo gio Viet Nam (UTC+7)."""
    return datetime.now(TZ_VN)

def today_vn() -> date:
    """Tra ve ngay hien tai theo gio Viet Nam."""
    return now_vn().date()

# ============================================================
# CONFIG & LOGGING
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
# DB_PATH lay tu bien moi truong de co the tro vao Railway Volume (du lieu ben vung).
# Vi du tren Railway: tao Volume mount tai /data roi dat DB_PATH=/data/daiky.db
DB_PATH = os.environ.get("DB_PATH", "daiky.db")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# HE THONG NGU HANH / AM DUONG (giu nguyen, dung cho tang phan tich)
# ============================================================
THIEN_CAN = ["Giap", "At", "Binh", "Dinh", "Mau", "Ky", "Canh", "Tan", "Nham", "Quy"]
DIA_CHI   = ["Ty", "Suu", "Dan", "Mao", "Thin", "Ty.", "Ngo", "Mui", "Than", "Dau", "Tuat", "Hoi"]

# Bang chuyen tu Can/Chi chu Han (lunar_python) sang ten tieng Viet noi bo.
CAN_HAN_TO_VN = {
    "\u7532": "Giap", "\u4e59": "At", "\u4e19": "Binh", "\u4e01": "Dinh", "\u620a": "Mau",
    "\u5df1": "Ky", "\u5e9a": "Canh", "\u8f9b": "Tan", "\u58ec": "Nham", "\u7678": "Quy",
}
CHI_HAN_TO_VN = {
    "\u5b50": "Ty", "\u4e11": "Suu", "\u5bc5": "Dan", "\u536f": "Mao", "\u8fb0": "Thin",
    "\u5df3": "Ty.", "\u5348": "Ngo", "\u672a": "Mui", "\u7533": "Than", "\u9149": "Dau",
    "\u620c": "Tuat", "\u4ea5": "Hoi",
}

NGU_HANH = {
    "Giap":"Moc","At":"Moc","Binh":"Hoa","Dinh":"Hoa","Mau":"Tho","Ky":"Tho","Canh":"Kim","Tan":"Kim","Nham":"Thuy","Quy":"Thuy",
    "Dan":"Moc","Mao":"Moc","Ty.":"Hoa","Ngo":"Hoa","Than":"Kim","Dau":"Kim","Hoi":"Thuy","Ty":"Thuy","Suu":"Tho","Thin":"Tho","Mui":"Tho","Tuat":"Tho"
}

AM_DUONG_CAN = {"Giap":"Duong","At":"Am","Binh":"Duong","Dinh":"Am","Mau":"Duong","Ky":"Am","Canh":"Duong","Tan":"Am","Nham":"Duong","Quy":"Am"}
TUONG_SINH = {"Moc":"Hoa","Hoa":"Tho","Tho":"Kim","Kim":"Thuy","Thuy":"Moc"}
TUONG_KHAC = {"Moc":"Tho","Tho":"Thuy","Thuy":"Hoa","Hoa":"Kim","Kim":"Moc"}

LUC_HOP = {frozenset({"Ty", "Suu"}), frozenset({"Dan", "Hoi"}), frozenset({"Mao", "Tuat"}), frozenset({"Thin", "Dau"}), frozenset({"Ty.", "Than"}), frozenset({"Ngo", "Mui"})}
LUC_XUNG = {frozenset({"Ty", "Ngo"}), frozenset({"Suu", "Mui"}), frozenset({"Dan", "Than"}), frozenset({"Mao", "Dau"}), frozenset({"Thin", "Tuat"}), frozenset({"Ty.", "Hoi"})}

# ============================================================
# TANG CAN CHUAN (ban day du, ti le nang luong nguyet lenh xap xi)
# ============================================================
TANG_CAN = {
    "Ty":   {"Quy": 1.0},
    "Suu":  {"Ky": 0.6, "Quy": 0.3, "Tan": 0.1},
    "Dan":  {"Giap": 0.6, "Binh": 0.3, "Mau": 0.1},
    "Mao":  {"At": 1.0},
    "Thin": {"Mau": 0.6, "At": 0.3, "Quy": 0.1},
    "Ty.":  {"Binh": 0.6, "Canh": 0.3, "Mau": 0.1},
    "Ngo":  {"Dinh": 0.7, "Ky": 0.3},
    "Mui":  {"Ky": 0.6, "Dinh": 0.3, "At": 0.1},
    "Than": {"Canh": 0.6, "Nham": 0.3, "Mau": 0.1},
    "Dau":  {"Tan": 1.0},
    "Tuat": {"Mau": 0.6, "Tan": 0.3, "Dinh": 0.1},
    "Hoi":  {"Nham": 0.7, "Giap": 0.3}
}

# ------------------------------------------------------------
# VONG TRUONG SINH (giu nguyen)
# ------------------------------------------------------------
TRUONG_SINH_SEQ = ["Truong Sinh", "Moc Duc", "Quan Doi", "Lam Quan", "De Vuong", "Suy", "Benh", "Tu", "Mo", "Tuyet", "Thai", "Duong"]
CAN_TS_START = {
    "Giap":("Hoi", 1), "At":("Ngo", -1), "Binh":("Dan", 1), "Dinh":("Dau", -1), "Mau":("Dan", 1),
    "Ky":("Dau", -1), "Canh":("Ty.", 1), "Tan":("Ty", -1), "Nham":("Than", 1), "Quy":("Mao", -1)
}
TS_HE_SO = {
    "De Vuong": 1.4, "Lam Quan": 1.3, "Truong Sinh": 1.2, "Quan Doi": 1.1, "Moc Duc": 1.0,
    "Duong": 1.0, "Thai": 0.9, "Suy": 0.9, "Mo": 0.8, "Benh": 0.7, "Tu": 0.5, "Tuyet": 0.4
}

def get_truong_sinh(can, chi):
    if can not in CAN_TS_START or chi not in DIA_CHI: return "N/A"
    start_chi, step = CAN_TS_START[can]
    idx_start = DIA_CHI.index(start_chi)
    idx_target = DIA_CHI.index(chi)
    dist = (idx_target - idx_start) * step
    return TRUONG_SINH_SEQ[dist % 12]

def tinh_thap_than(nhat_chu, can_check):
    if nhat_chu not in NGU_HANH or can_check not in NGU_HANH: return "N/A"
    nh_chu, nh_check = NGU_HANH[nhat_chu], NGU_HANH[can_check]
    cung_ad = (AM_DUONG_CAN[nhat_chu] == AM_DUONG_CAN[can_check])
    if nh_check == nh_chu: return "Ty Kien" if cung_ad else "Kiep Tai"
    if TUONG_SINH.get(nh_check) == nh_chu: return "Thien An" if cung_ad else "Chinh An"
    if TUONG_SINH.get(nh_chu) == nh_check: return "Thuc Than" if cung_ad else "Thuong Quan"
    if TUONG_KHAC.get(nh_chu) == nh_check: return "Thien Tai" if cung_ad else "Chinh Tai"
    if TUONG_KHAC.get(nh_check) == nh_chu: return "That Sat" if cung_ad else "Chinh Quan"
    return "N/A"

# ============================================================
# LA SO TU TRU DUNG lunar_python (6tail) - CHUAN JDN + TIET KHI
# ============================================================
def _ganzhi_to_vn(gz):
    """Chuyen chuoi Can-Chi chu Han sang (can_vn, chi_vn). Quet tung ky tu de
    bo qua khoang trang/ky tu thua. Raise ValueError neu thieu Can hoac Chi."""
    if not gz:
        raise ValueError("Chuoi Can-Chi rong tu lunar_python")
    can = chi = None
    for ch in str(gz):
        if can is None and ch in CAN_HAN_TO_VN:
            can = CAN_HAN_TO_VN[ch]
        elif chi is None and ch in CHI_HAN_TO_VN:
            chi = CHI_HAN_TO_VN[ch]
    if can is None or chi is None:
        raise ValueError("Khong doc duoc Can-Chi tu '%s'" % gz)
    return can, chi

def get_tiet_khi(ngay: date):
    """
    Tra ve (ten_tiet_khi_xap_xi, dia_chi_thang) cho `ngay`, dung tiet khi chuan
    cua lunar_python (tinh theo vi tri thien van that). Dia chi thang lay tu
    tru thang trong EightChar nen luon dung ranh gioi tiet (khong phai khi).
    """
    solar = Solar.fromYmd(ngay.year, ngay.month, ngay.day)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()
    _, chi_thang = _ganzhi_to_vn(ec.getMonth())
    ten_tiet = ""
    try:
        jq = lunar.getPrevJieQi(True)
        if jq is not None:
            ten_tiet = jq.getName() or ""
    except Exception:
        ten_tiet = lunar.getJieQi() or ""
    return ten_tiet, chi_thang

def build_tu_tru(nam, tc, ngay, gio):
    """
    Dung lunar_python de sinh Tu Tru chuan.
    Tham so `tc` (chi thang) giu lai cho tuong thich chu ky goi cu, khong dung
    nua vi tru thang duoc lay truc tiep tu thu vien.
    `ngay` la datetime.date, `gio` la gio (0-23).
    Thu vien tu xu ly gio Ty som/muon (23h -> ngay moi) chuan xac.
    """
    solar = Solar.fromYmdHms(ngay.year, ngay.month, ngay.day, gio, 0, 0)
    ec = solar.getLunar().getEightChar()

    cn, chin   = _ganzhi_to_vn(ec.getYear())
    cthang, ct = _ganzhi_to_vn(ec.getMonth())
    cng, ching = _ganzhi_to_vn(ec.getDay())
    cg, chig   = _ganzhi_to_vn(ec.getTime())

    if cng not in NGU_HANH:
        raise ValueError("Nhat Chu khong hop le sau khi dung Tu Tru")

    return {
        "nam": {"can": cn, "chi": chin},
        "thang": {"can": cthang, "chi": ct},
        "ngay": {"can": cng, "chi": ching},
        "gio": {"can": cg, "chi": chig},
        "nhat_chu": cng
    }

# ------------------------------------------------------------
# THUAT TOAN DINH LUONG NANG LUONG
# ------------------------------------------------------------
TRONG_SO_NL = {
    "can_nam": 1.0, "chi_nam": 1.5,
    "can_thang": 1.0, "chi_thang": 3.5,
    "can_ngay": 0.0, "chi_ngay": 1.5,
    "can_gio": 1.0, "chi_gio": 1.5
}

def dinh_luong_nang_luong(ls):
    nc_hanh = NGU_HANH[ls["nhat_chu"]]
    hanh_sinh_nc = next((k for k, v in TUONG_SINH.items() if v == nc_hanh), None)

    diem_tuong_tro = 0.0
    diem_that_tho = 0.0
    chi_tiet_hanh = {"Moc": 0.0, "Hoa": 0.0, "Tho": 0.0, "Kim": 0.0, "Thuy": 0.0}

    cac_can = {
        "can_nam": ls["nam"]["can"],
        "can_thang": ls["thang"]["can"],
        "can_ngay": ls["ngay"]["can"],
        "can_gio": ls["gio"]["can"]
    }
    for vitri, can in cac_can.items():
        if vitri in TRONG_SO_NL and TRONG_SO_NL[vitri] > 0:
            hanh = NGU_HANH.get(can)
            if hanh:
                chi_tiet_hanh[hanh] += TRONG_SO_NL[vitri]

    cac_chi = {
        "chi_nam": ls["nam"]["chi"],
        "chi_thang": ls["thang"]["chi"],
        "chi_ngay": ls["ngay"]["chi"],
        "chi_gio": ls["gio"]["chi"]
    }
    for vitri, chi in cac_chi.items():
        if vitri in TRONG_SO_NL and TRONG_SO_NL[vitri] > 0:
            tong_diem_chi = TRONG_SO_NL[vitri]
            tang_can_dict = TANG_CAN.get(chi, {})
            for can_an, ti_le in tang_can_dict.items():
                hanh_an = NGU_HANH.get(can_an)
                if hanh_an:
                    chi_tiet_hanh[hanh_an] += tong_diem_chi * ti_le

    for hanh, diem in chi_tiet_hanh.items():
        if hanh == nc_hanh or hanh == hanh_sinh_nc:
            diem_tuong_tro += diem
        else:
            diem_that_tho += diem

    return round(diem_tuong_tro, 2), round(diem_that_tho, 2), {k: round(v, 2) for k, v in chi_tiet_hanh.items()}

def xac_dinh_dung_than(ls):
    nc_hanh = NGU_HANH[ls["nhat_chu"]]
    hanh_sinh_nc = next((k for k, v in TUONG_SINH.items() if v == nc_hanh), None)
    hanh_nc_sinh = TUONG_SINH.get(nc_hanh)
    hanh_khac_nc = next((k for k, v in TUONG_KHAC.items() if v == nc_hanh), None)
    hanh_nc_khac = TUONG_KHAC.get(nc_hanh)
    diem_tuong_tro, diem_that_tho, chi_tiet_hanh = dinh_luong_nang_luong(ls)

    if diem_tuong_tro <= 2.0:
        hanh_manh_nhat = max(chi_tiet_hanh, key=chi_tiet_hanh.get)
        hanh_sinh_manh = TUONG_SINH.get(hanh_manh_nhat)
        return [h for h in [hanh_manh_nhat, hanh_sinh_manh] if h is not None], "Tong Nhuoc (Dac Biet)"
    if diem_that_tho <= 2.0:
        return [hanh_nc_sinh, nc_hanh], "Tong Cuong (Dac Biet)"
    if diem_tuong_tro >= 5.5:
        dung_than = [h for h in [hanh_nc_khac, hanh_nc_sinh, hanh_khac_nc] if h is not None]
        return dung_than, "Vuong"
    else:
        dung_than = [h for h in [hanh_sinh_nc, nc_hanh] if h is not None]
        return dung_than, "Nhuoc"

# ------------------------------------------------------------
# LOGIC BINH GIAI
# ------------------------------------------------------------
def get_season_multiplier(month_chi, day_chi):
    day_nh = NGU_HANH.get(day_chi)
    seasons = {"Moc":["Dan","Mao","Thin"],"Hoa":["Ty.","Ngo","Mui"],"Kim":["Than","Dau","Tuat"],"Thuy":["Hoi","Ty","Suu"]}
    vuong_element = next((k for k, v in seasons.items() if month_chi in v), None)
    return 1.3 if day_nh == vuong_element else 1.0

def tinh_suc_manh_nhat_chu(ls):
    nh_chu = NGU_HANH[ls["nhat_chu"]]
    chi_thang = ls["thang"]["chi"]
    mua_vuong = {"Moc":["Dan","Mao","Hoi"],"Hoa":["Ty.","Ngo","Dan"],"Tho":["Suu","Thin","Mui","Tuat"],"Kim":["Than","Dau","Suu"],"Thuy":["Ty","Hoi","Dau"]}
    return 1.2 if chi_thang in mua_vuong.get(nh_chu, []) else 0.8

def get_dich_ma(chi):
    ma_map = {"Than":"Dan","Ty":"Dan","Thin":"Dan","Ty.":"Hoi","Dau":"Hoi","Suu":"Hoi","Dan":"Than","Ngo":"Than","Tuat":"Than","Hoi":"Ty.","Mao":"Ty.","Mui":"Ty."}
    return ma_map.get(chi)

def phan_tich_chuyen_gia_3_mon(ngay_check: date, ls: dict):
    tt_now = build_tu_tru(ngay_check.year, None, ngay_check, 12)
    month_chi = tt_now["thang"]["chi"]
    thap_than = tinh_thap_than(ls["nhat_chu"], tt_now["ngay"]["can"])
    suc_manh = tinh_suc_manh_nhat_chu(ls)
    chi_ngay = tt_now["ngay"]["chi"]
    ngay_hanh = NGU_HANH.get(chi_ngay)

    dung_than, _ = xac_dinh_dung_than(ls)
    ts_state = get_truong_sinh(ls["nhat_chu"], chi_ngay)
    he_so_ts = TS_HE_SO.get(ts_state, 1.0)

    s_trade = 5.0 + (3.5 * suc_manh if thap_than in ["Thien Tai", "Chinh Tai"] else -3.0 if thap_than == "Kiep Tai" else 0)
    if frozenset({chi_ngay, ls["ngay"]["chi"]}) in LUC_XUNG: s_trade -= 2.5
    s_study = 5.0 + (3.0 if thap_than in ["Chinh An", "Thien An"] else 0) + (1.0 if NGU_HANH[chi_ngay] in ["Thuy", "Moc"] else 0)
    s_move = 5.0 + (4.5 if chi_ngay in [get_dich_ma(ls["nam"]["chi"]), get_dich_ma(ls["ngay"]["chi"])] else 0)
    if frozenset({chi_ngay, ls["ngay"]["chi"]}) in LUC_XUNG: s_move -= 4.0

    s_health = 5.0
    if ts_state in ["De Vuong", "Lam Quan", "Truong Sinh"]: s_health += 3.0
    elif ts_state in ["Tuyet", "Tu", "Benh"]: s_health -= 3.0
    elif ts_state in ["Suy", "Mo"]: s_health -= 1.5
    if NGU_HANH[chi_ngay] in ["Thuy", "Moc"]: s_health += 1.0
    if frozenset({chi_ngay, ls["ngay"]["chi"]}) in LUC_XUNG: s_health -= 2.5

    s_work = 5.0
    if thap_than in ["Chinh Quan"]: s_work += 3.0
    elif thap_than in ["That Sat"]: s_work += 1.5
    elif thap_than in ["Thuc Than"]: s_work += 2.5
    elif thap_than in ["Thuong Quan"]: s_work += 1.0
    elif thap_than in ["Kiep Tai"]: s_work -= 2.0
    if frozenset({chi_ngay, ls["thang"]["chi"]}) in LUC_XUNG: s_work -= 3.0

    if ngay_hanh in dung_than:
        s_trade += 2.0; s_study += 2.0; s_move += 2.0
        s_health += 1.5; s_work += 2.0
    else:
        s_trade -= 1.5; s_study -= 1.0; s_move -= 1.5
        s_health -= 1.0; s_work -= 1.5

    s_trade *= he_so_ts; s_study *= he_so_ts; s_move *= he_so_ts
    s_work *= he_so_ts
    return {k: round(max(0, min(10, v)), 1) for k, v in {
        "trading": s_trade, "study": s_study, "move": s_move,
        "health": s_health, "work": s_work
    }.items()}

def phan_tich_ngay_sau(ngay_check: date, gio: int, sinh_info: dict):
    ls = sinh_info["la_so"]
    nhat_chu_can = ls["nhat_chu"]
    tt_now = build_tu_tru(ngay_check.year, None, ngay_check, gio)
    month_chi = tt_now["thang"]["chi"]

    diem_hung = 0.0; chi_tiet = []
    check_list = [("Ngay", tt_now["ngay"]["chi"], 1.5), ("Nam", tt_now["nam"]["chi"], 1.2)]
    targets = [("Nhat Chu", ls["ngay"]["chi"], 8), ("Tru Nam", ls["nam"]["chi"], 5)]

    dung_than, _ = xac_dinh_dung_than(ls)
    ngay_hanh = NGU_HANH.get(tt_now["ngay"]["chi"])
    ts_state = get_truong_sinh(nhat_chu_can, tt_now["ngay"]["chi"])

    if ngay_hanh in dung_than:
        chi_tiet.append(f"\u2728 Hanh {ngay_hanh} la DUNG THAN (Do duoc hung hiem)")
        diem_hung -= 3.0
    else:
        chi_tiet.append(f"\u26a0\ufe0f Hanh {ngay_hanh} la KY THAN (Can than rui ro)")
        diem_hung += 2.0

    chi_tiet.append(f"\U0001f50b Nang luong: {ts_state}")
    if ts_state in ["Tuyet", "Tu", "Benh"]:
        diem_hung += 3.0
        chi_tiet.append(f"\U0001f4c9 Menh roi vao cung {ts_state}, khi luc suy kiet.")
    elif ts_state in ["De Vuong", "Lam Quan", "Truong Sinh"]:
        diem_hung -= 2.0

    all_la_so_chi = {ls["nam"]["chi"], ls["thang"]["chi"], ls["ngay"]["chi"], ls["gio"]["chi"]}
    for n_now, c_now, p_coeff in check_list:
        for n_tar, c_tar, weight in targets:
            if frozenset({c_now, c_tar}) in LUC_XUNG:
                current_score = weight * p_coeff * get_season_multiplier(month_chi, c_now)
                is_saved = any(frozenset({c_now, chi_gs}) in LUC_HOP for chi_gs in all_la_so_chi)
                if is_saved: chi_tiet.append(f"\U0001f6e1\ufe0f {n_now} Xung {n_tar} nhung co Hop giai tu la so goc")
                else:
                    diem_hung += current_score
                    chi_tiet.append(f"\U0001f525 {n_now} Xung {n_tar} ({c_now}-{c_tar})")

    if tinh_thap_than(nhat_chu_can, tt_now["ngay"]["can"]) == "That Sat":
        diem_hung += 5; chi_tiet.append(f"\u2694\ufe0f Thien Can pham That Sat")

    if diem_hung >= 12: muc = "\U0001f534 CUC NANG"
    elif diem_hung >= 7: muc = "\U0001f7e0 RAT NANG"
    elif diem_hung >= 3: muc = "\U0001f7e1 TRUNG BINH"
    else: muc = "\u2705 BINH THUONG"
    return {"diem": round(diem_hung, 1), "muc": muc, "detail": chi_tiet, "is_dangerous": diem_hung >= 7}

# ============================================================
# DB & BOT HANDLERS
# ============================================================
def init_db():
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH); conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT)"); conn.commit(); conn.close()
def get_data(uid):
    conn = sqlite3.connect(DB_PATH); r = conn.execute("SELECT data FROM users WHERE user_id=?", (str(uid),)).fetchone(); conn.close()
    if not r:
        return None
    info = json.loads(r[0])
    ls = info.get("la_so") or {}
    if ls.get("nhat_chu") not in NGU_HANH:
        logger.warning("La so hong cho user %s, bo qua", uid)
        return None
    return info

NHAP_N, NHAP_T, NHAP_D, NHAP_G = range(4)

async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    txt = "\U0001f31f *BOT DAI KY - MA TRAN TU TRU*\n\n\U0001f4dc *MENU LENH:*\n\u2022 /nhapngaysinh - Thiet lap la so\n\u2022 /ngaydaiky - Danh sach ngay xau thang nay\n\u2022 /canhbao - Quet chi tiet 30 ngay toi\n\u2022 /homnay - Khi van gio hien tai"
    await u.message.reply_text(txt, parse_mode="Markdown")

async def nhap_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Nhap NAM SINH (vd: 1990):"); return NHAP_N

async def nhap_n(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        c.user_data["n"] = int(u.message.text); await u.message.reply_text("Nhap THANG SINH (1-12):"); return NHAP_T
    except ValueError: await u.message.reply_text("Nhap so ho tao cai! Nhap lai NAM:"); return NHAP_N

async def nhap_t(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        val = int(u.message.text)
        if 1 <= val <= 12: c.user_data["t"] = val; await u.message.reply_text("Nhap NGAY SINH (1-31):"); return NHAP_D
        await u.message.reply_text("Thang gi la vay? Nhap lai tu 1 den 12:"); return NHAP_T
    except ValueError: await u.message.reply_text("Dung go chu! Hay nhap THANG bang so (1-12):"); return NHAP_T

async def nhap_d(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        val = int(u.message.text)
        if 1 <= val <= 31: c.user_data["d"] = val; await u.message.reply_text("Nhap GIO SINH (0-23):"); return NHAP_G
        await u.message.reply_text("Ngay khong hop le! Nhap lai tu 1 den 31:"); return NHAP_D
    except ValueError: await u.message.reply_text("Dung go chu! Hay nhap NGAY bang so (1-31):"); return NHAP_D

async def nhap_g(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        g = int(u.message.text)
        if not (0 <= g <= 23): await u.message.reply_text("Gio sinh phai tu 0 den 23. Nhap lai:"); return NHAP_G
        n, t, d = c.user_data["n"], c.user_data["t"], c.user_data["d"]
        try:
            ngay_sinh = date(n, t, d)
        except ValueError:
            await u.message.reply_text(f"\u274c Loi: Ngay {d}/{t}/{n} khong ton tai. Go /nhapngaysinh lai!"); return ConversationHandler.END
        try:
            ls = build_tu_tru(n, None, ngay_sinh, g)
        except Exception as e:
            logger.exception("Loi dung Tu Tru: %s", e)
            await u.message.reply_text("\u274c Khong tinh duoc la so cho ngay nay. Go /nhapngaysinh thu lai!"); return ConversationHandler.END
        conn = sqlite3.connect(DB_PATH); conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (str(u.effective_user.id), json.dumps({"n":n,"t":t,"d":d,"g":g,"la_so":ls}))); conn.commit(); conn.close()
        await u.message.reply_text("\u2705 Xong! Cau hinh thanh cong. Go /canhbao & /ngaydaiky & /homnay de xem han nhe."); return ConversationHandler.END
    except ValueError: await u.message.reply_text("Lai go chu a? Hay nhap GIO bang so (0-23):"); return NHAP_G

async def cmd_canh_bao(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("May chua nhap thong tin! Go /nhapngaysinh di da."); return
    today = today_vn(); warns = []
    for i in range(1, 31):
        d = today + timedelta(days=i); res = phan_tich_ngay_sau(d, 12, info)
        if res["is_dangerous"]: warns.append(f"\U0001f4c5 *{d.strftime('%d/%m')}* ({res['diem']}d): {res['muc']}\n   \u21b3 {', '.join(res['detail'])}")
    await u.message.reply_text("\u26a0\ufe0f *QUET 30 NGAY TOI*\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n" + ("\n\n".join(warns) if warns else "\u2705 Moi su binh an."), parse_mode="Markdown")

async def cmd_ngay_dai_ky(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("May chua nhap thong tin! Go /nhapngaysinh di da."); return
    m = int(c.args[0]) if c.args and c.args[0].isdigit() else today_vn().month
    y = today_vn().year; msg = [f"\U0001f4c5 *NGAY XUNG THANG {m}/{y}*\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"]; curr = date(y, m, 1); found = False
    while curr.month == m:
        res = phan_tich_ngay_sau(curr, 12, info)
        if res["is_dangerous"]: msg.append(f"\u2022 *{curr.strftime('%d/%m')}*: {res['muc']} ({res['diem']}d)"); found = True
        curr += timedelta(days=1)
    if not found: msg.append("\u2705 Khong co ngay xung nang.")
    await u.message.reply_text("\n".join(msg), parse_mode="Markdown")

async def cmd_hom_nay(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("May chua nhap thong tin! Go /nhapngaysinh di da."); return
    res = phan_tich_ngay_sau(today_vn(), now_vn().hour, info); exp = phan_tich_chuyen_gia_3_mon(today_vn(), info["la_so"])
    dung_than, than_loai = xac_dinh_dung_than(info["la_so"])
    def bar(s): return "\U0001f7e2" * int(s/2) + "\u26aa" * (5 - int(s/2))
    txt = f"\u2600\ufe0f *KHI VAN HIEN TAI :*\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n" \
          f"\U0001f464 Than {than_loai} - Dung Than: {', '.join(dung_than)}\n\n" \
          f"\U0001f4ca *Chi so (Thang 10):*\n" \
          f"\U0001f4b0 Trading: {exp['trading']} {bar(exp['trading'])}\n" \
          f"\U0001f4da Hoc tap: {exp['study']} {bar(exp['study'])}\n" \
          f"\U0001f697 Di chuyen: {exp['move']} {bar(exp['move'])}\n" \
          f"\u2764\ufe0f Suc khoe: {exp['health']} {bar(exp['health'])}\n" \
          f"\U0001f4bc Cong viec: {exp['work']} {bar(exp['work'])}\n\n" \
          f"*Ket qua:* {res['muc']} ({res['diem']}d)\n" + "\n".join(res['detail'])
    await u.message.reply_text(txt, parse_mode="Markdown")

def main():
    if not BOT_TOKEN: return
    init_db(); app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(entry_points=[CommandHandler("nhapngaysinh", nhap_start)], states={NHAP_N:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_n)], NHAP_T:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_t)], NHAP_D:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_d)], NHAP_G:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_g)]}, fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)])
    app.add_handler(conv); app.add_handler(CommandHandler("start", cmd_start)); app.add_handler(CommandHandler("canhbao", cmd_canh_bao)); app.add_handler(CommandHandler("ngaydaiky", cmd_ngay_dai_ky)); app.add_handler(CommandHandler("homnay", cmd_hom_nay)); app.run_polling()

if __name__ == "__main__": main()
