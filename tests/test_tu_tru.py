"""
Bo test doi chieu logic Tu Tru / Bat Tu.

MUC TIEU: xac nhan build_tu_tru (dung lunar_python) tra dung Can-Chi 4 tru,
vong Truong Sinh, Thap Than va Luc Xung dung ly thuyet Tu Binh.

LUU Y QUAN TRONG:
- Cac gia tri ky vong Can-Chi duoi day dua tren ly thuyet/doi chieu lich van
  nien. Khi chay lan dau, neu lunar_python tra ket qua khac, PHAI kiem tra lai
  bang nguon chuan (vd lichvannien.net) truoc khi sua gia tri ky vong.
- KHONG sua gia tri ky vong chi de cho test pass. Neu code sai thi sua code.
"""
import datetime

import pytest


# ------------------------------------------------------------------
# 1. DOI CHIEU LA SO 4 TRU
# ------------------------------------------------------------------
# Moi case: (nam, thang, ngay, gio, ky_vong_dict)
# ky_vong_dict: {"nam": (can, chi), "thang": (can, chi), "ngay": (can, chi), "gio": (can, chi)}
# Cac gia tri nay can duoc xac nhan bang lich van nien khi chay lan dau.
_CASES = [
    # Ca thuong: 1990-05-15 10:00 (gio Ty.)
    (
        1990, 5, 15, 10,
        {
            "nam":   ("Canh", "Ngo"),
            "thang": ("Tan", "Ty."),
            "ngay":  ("Quy", "Mui"),
            "gio":   ("Dinh", "Ty."),
        },
    ),
    # Ca thuong: 2000-01-01 00:00 (gio Ty chinh)
    (
        2000, 1, 1, 0,
        {
            "nam":   ("Ky", "Mao"),
            "thang": ("Binh", "Ty"),
            "ngay":  ("Mau", "Ngo"),
            "gio":   ("Nham", "Ty"),
        },
    ),
]


@pytest.mark.parametrize("nam,thang,ngay,gio,kv", _CASES)
def test_build_tu_tru_doi_chieu(bot, nam, thang, ngay, gio, kv):
    ls = bot.build_tu_tru(nam, None, datetime.date(nam, thang, ngay), gio)
    for tru, (can_kv, chi_kv) in kv.items():
        assert ls[tru]["can"] == can_kv, (
            f"{nam}-{thang}-{ngay} {gio}h: tru {tru} can = {ls[tru]['can']}, ky vong {can_kv}"
        )
        assert ls[tru]["chi"] == chi_kv, (
            f"{nam}-{thang}-{ngay} {gio}h: tru {tru} chi = {ls[tru]['chi']}, ky vong {chi_kv}"
        )
    assert ls["nhat_chu"] == ls["ngay"]["can"]


# ------------------------------------------------------------------
# 2. GIO TY SOM (23h -> tru ngay sang ngay hom sau)
# ------------------------------------------------------------------
def test_gio_ty_som_doi_ngay(bot):
    """
    23h cua ngay D phai cho tru ngay = tru ngay cua (D+1) theo quy uoc Tu Binh
    (gio Ty som thuoc ve ngay moi). Chi gio phai la 'Ty'.
    """
    d = datetime.date(2000, 1, 1)
    ls_23h = bot.build_tu_tru(2000, None, d, 23)
    ls_next_00h = bot.build_tu_tru(2000, None, d + datetime.timedelta(days=1), 0)

    assert ls_23h["gio"]["chi"] == "Ty"
    # Tru ngay luc 23h phai trung tru ngay 00h hom sau
    assert ls_23h["ngay"]["can"] == ls_next_00h["ngay"]["can"]
    assert ls_23h["ngay"]["chi"] == ls_next_00h["ngay"]["chi"]


# ------------------------------------------------------------------
# 3. RANH GIOI TIET KHI (chi thang doi tai dau tiet)
# ------------------------------------------------------------------
def test_ranh_gioi_tiet_khi_lap_xuan(bot):
    """
    Quanh Lap Xuan (dau thang Dan). Truoc Lap Xuan chi thang van la Suu,
    tu Lap Xuan tro di la Dan. Kiem tra chi thang thay doi dung quanh ranh gioi,
    khong assert ngay cu the (tiet khi xe dich theo nam) ma kiem tra tinh nhat quan:
    chi thang dau thang 1 (truoc Lap Xuan) khac chi thang giua thang 2.
    """
    _, chi_dau_t1 = bot.get_tiet_khi(datetime.date(2024, 1, 10))   # truoc Tieu Han? -> Ty/Suu
    _, chi_giua_t2 = bot.get_tiet_khi(datetime.date(2024, 2, 20))  # sau Lap Xuan -> Dan
    assert chi_giua_t2 == "Dan"
    # Dau thang 1 duong lich chua qua Lap Xuan nen khong the la Dan
    assert chi_dau_t1 != "Dan"


# ------------------------------------------------------------------
# 4. VONG TRUONG SINH
# ------------------------------------------------------------------
@pytest.mark.parametrize("can,chi,ky_vong", [
    ("Giap", "Hoi", "Truong Sinh"),   # Giap truong sinh tai Hoi
    ("Giap", "Ty", "Moc Duc"),        # ke tiep theo chieu thuan
    ("Giap", "Ngo", "Tu"),            # Giap tu tai Ngo
    ("Binh", "Dan", "Truong Sinh"),   # Binh/Mau truong sinh tai Dan
    ("Nham", "Than", "Truong Sinh"),  # Nham truong sinh tai Than
])
def test_truong_sinh(bot, can, chi, ky_vong):
    assert bot.get_truong_sinh(can, chi) == ky_vong


# ------------------------------------------------------------------
# 5. THAP THAN
# ------------------------------------------------------------------
@pytest.mark.parametrize("nhat_chu,can_check,ky_vong", [
    ("Giap", "Giap", "Ty Kien"),     # cung Moc, cung Duong
    ("Giap", "At", "Kiep Tai"),      # cung Moc, khac am duong
    ("Giap", "Binh", "Thuc Than"),   # Moc sinh Hoa, cung Duong
    ("Giap", "Dinh", "Thuong Quan"), # Moc sinh Hoa, khac am duong
    ("Giap", "Canh", "That Sat"),    # Kim khac Moc, cung Duong
    ("Giap", "Tan", "Chinh Quan"),   # Kim khac Moc, khac am duong
])
def test_thap_than(bot, nhat_chu, can_check, ky_vong):
    assert bot.tinh_thap_than(nhat_chu, can_check) == ky_vong


# ------------------------------------------------------------------
# 6. LUC XUNG / LUC HOP (kiem tra bang du lieu nhat quan)
# ------------------------------------------------------------------
def test_luc_xung_hop_day_du(bot):
    assert len(bot.LUC_XUNG) == 6
    assert len(bot.LUC_HOP) == 6
    assert frozenset({"Ty", "Ngo"}) in bot.LUC_XUNG
    assert frozenset({"Ty", "Suu"}) in bot.LUC_HOP


# ------------------------------------------------------------------
# 7. _ganzhi_to_vn raise loi khi format la
# ------------------------------------------------------------------
def test_ganzhi_to_vn_raise_khi_rong(bot):
    with pytest.raises(ValueError):
        bot._ganzhi_to_vn("")
    with pytest.raises(ValueError):
        bot._ganzhi_to_vn("xyz")
