# -*- coding: utf-8 -*-
"""후기 사진 확대 창: 흐린 미리보기 상자가 확대본보다 작게 떴다가 커지며 튀던 결함(2026-09-29) 회귀 잠금.

실측(nuvie_ux_lab/check_lb_box.py, 모바일 390·PC 1440·/a 390): 수정 전 미리보기 299x640 → 확대본 339x726(튐),
수정 후 339x726 → 339x726. map.json 의 원본 w·h 를 확대 img 의 width/height 로 먼저 넣어 상자를 최종 크기로 잡는다.
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
SITEJS = (ROOT / "site.js").read_text(encoding="utf-8")


def test_home_openlb_takes_dims_and_sets_box_before_placeholder():
    m = re.search(r"function openLb\(src,trigger,alt,placeholder,dims\)\{(.*?)var probe=new Image\(\);", INDEX, flags=re.S)
    assert m, "홈 openLb 가 dims(원본 w·h)를 받지 않는다"
    body = m.group(1)
    i_dims = body.find("lbImg.width=dims.w")
    i_ph = body.find("lbImg.src=placeholder")
    assert 0 <= i_dims < i_ph, "미리보기를 띄우기 전에 상자 크기(width/height)를 먼저 잡아야 한다"
    assert "lbImg.removeAttribute('width')" in body, "dims 가 없으면(갤러리 등) 이전 크기를 지워야 한다"


def test_home_review_thumbs_pass_map_entry_as_dims():
    assert INDEX.count("openLb(fullSrc,im,null,ent&&ent.thumb?thumbSrc:null,ent)") == 2, "클릭·키보드 둘 다 ent 를 넘겨야 한다"


def test_home_closelb_clears_box():
    m = re.search(r"function closeLb\(\)\{([^\n]*)", INDEX)
    assert m and "removeAttribute('width')" in m.group(1) and "removeAttribute('height')" in m.group(1)


def test_room_page_review_open_sets_box_and_close_clears_it():
    assert re.search(r"if \(ent\.w && ent\.h\) \{ lbImg\.width = ent\.w; lbImg\.height = ent\.h; \}", SITEJS)
    m = re.search(r"function closeLb\(\)\{([^\n]*)", SITEJS)
    assert m and "removeAttribute('width')" in m.group(1) and "removeAttribute('height')" in m.group(1)
