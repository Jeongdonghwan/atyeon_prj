"""일조원갤러리 작품 아카이브(artworks.json + 이미지) → DB 가져오기.

  python import_archive.py                    # data/archive 를 읽어 작가·작품·전시 추가 (status=draft)
  python import_archive.py --replace          # 기존 작가·작품·전시 전부 삭제 후 가져오기 (아카데미·저널·미디어는 유지)
  python import_archive.py <폴더> [--replace]  # 다른 폴더(artworks.json + artwork-XX.webp 또는 assets/)
  --publish                                  # 검수 전 임시 공개(status=published). 운영 공개 전엔 쓰지 말 것

규칙
- 작가 '작가 확인 필요' → artist_id 비움 + review_note. 확인되면 어드민에서 작가 선택만 하면 됨.
- '영원한 토지' 3장(11·12·13) → 작품 1건 + image/image_2/image_3. 별개 작품으로 확인되면 어드민에서 분리.
- details 문자열에서 규격(cm)·재료·연도를 파싱. '확인 필요' 문구는 review_note로 보냄.
- 모든 레코드 status=draft. 어드민에서 검수 후 published 로 바꿔야 사이트에 노출.
"""
import json, os, re, shutil, sys
from datetime import date
from app import app
from models import db, Artist, Artwork, Exhibition, Media, Journal, exhibition_artists

args = [a for a in sys.argv[1:] if not a.startswith("--")]
SRC = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "archive")
REPLACE = "--replace" in sys.argv
PUBLISH = "--publish" in sys.argv          # 검수 전 임시 공개 (임시 서버 확인용)
STATUS = "published" if PUBLISH else "draft"
UP = app.config["UPLOAD_DIR"]

# 카테고리 → 작가 매체 라벨
MEDIUM = {"공예": "도자 · 공예", "추상": "회화 · 추상", "회화": "회화", "자연": "회화 · 풍경", "도시": "회화 · 도시", "인물": "회화 · 인물"}
DUP_GROUPS = [("영원한 토지", [11, 12, 13])]   # 동일 작품 복수 촬영본 (대표 id가 첫 번째)


def slugify(s, fallback):
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return s if re.search(r"[a-z0-9]", s) else fallback


def parse_details(d):
    """'72.5 × 72.5 cm · Oil on canvas' → (dimensions, medium, year, notes)"""
    dims = medium = year = None; notes = []
    for part in [p.strip() for p in re.split(r"[·|]", d or "") if p.strip()]:
        if "확인" in part: notes.append(part); continue
        if part in ("재료", "크기", "규격", "연도"): notes.append(part + " 확인 필요"); continue
        if re.search(r"\d+(\.\d+)?\s*[×xX]\s*\d+", part): dims = re.sub(r"\s*cm$", "", part).replace("x", "×").replace("X", "×"); continue
        if re.fullmatch(r"(19|20)\d{2}", part): year = part; continue
        medium = part
    return dims, medium, year, " / ".join(notes)


def copy_image(rel):
    name = os.path.basename(rel)
    src = os.path.join(SRC, rel) if os.path.exists(os.path.join(SRC, rel)) else os.path.join(SRC, name)
    dst_name = "arch-" + name
    shutil.copyfile(src, os.path.join(UP, dst_name))
    return dst_name


with app.app_context():
    db.create_all()
    rows = json.load(open(os.path.join(SRC, "artworks.json"), encoding="utf-8"))

    if REPLACE:
        for m in Media.query.all(): m.artist_id = m.exhibition_id = None
        for j in Journal.query.all(): j.artist_id = None
        db.session.execute(exhibition_artists.delete())
        Artwork.query.delete(); Exhibition.query.delete(); Artist.query.delete()
        db.session.commit()

    # 1) 작가
    artists = {}
    for r in rows:
        n = r["artist"].strip()
        if "확인" in n or n in artists: continue
        a = Artist.query.filter_by(name_ko=n).first()
        if not a:
            a = Artist(slug=slugify(n, f"artist-{len(artists)+1:02d}"), name_ko=n, medium=MEDIUM.get(r["category"], "회화"),
                       cover=None, status=STATUS, sort=len(artists), featured=(n == "김훈섭"),
                       review_note="작가 소개·영문명·CV·초상 이미지 수급 필요")
            db.session.add(a)
        artists[n] = a
    db.session.flush()

    # 2) 작품 (중복 촬영본 묶기)
    merged = {}
    for title, ids in DUP_GROUPS:
        for i in ids[1:]: merged[i] = ids[0]
    extra = {}
    for r in rows:
        if r["id"] in merged: extra.setdefault(merged[r["id"]], []).append(r); continue
    count = 0
    for r in rows:
        if r["id"] in merged: continue
        dims, medium, year, notes = parse_details(r["details"])
        a = artists.get(r["artist"].strip())
        review = []
        if not a: review.append("작가 확인 필요")
        if notes: review.append(notes)
        if r["id"] in extra: review.append(f"동일 작품 촬영본 {len(extra[r['id']])}장 포함(이미지 2·3) — 별개 작품이면 분리")
        if r.get("year", "").find("확인") >= 0 and not year: review.append("제작연도 확인")
        if r["id"] == 3: review.append("저해상도(485px)·세로 비율 — 고해상 원본 수급 전 비공개")
        w = Artwork(slug=slugify(r["title"], f"work-{r['id']:02d}"), title_ko=r["title"], artist=a, category=r["category"],
                    dimensions=dims, medium_ko=medium, year=year, note_ko=r["description"],
                    image=copy_image(r["image"]), rights="© 작가 · 원본 파일: " + r["original_filename"],
                    featured=(r["id"] in (8, 16, 4, 2)), status=("draft" if r["id"] == 3 else STATUS), sort=r["id"],
                    review_note=" / ".join(review) or None)
        for k, e in zip(("image_2", "image_3"), extra.get(r["id"], [])):
            setattr(w, k, copy_image(e["image"]))
        db.session.add(w); count += 1
        if a and not a.cover: a.cover = w.image
    db.session.flush()

    # 3) 전시 (가제)
    ex = Exhibition.query.filter_by(slug="art-holds-time-2026").first() or Exhibition(slug="art-holds-time-2026")
    ex.title_ko = "예술, 시간을 담다 (가제)"; ex.title_en = "Art Holds Time"
    ex.start_date = date(2026, 12, 1); ex.end_date = date(2026, 12, 31); ex.location = "일조원갤러리"
    ex.cover = Artwork.query.filter_by(sort=8).first().image
    ex.status = STATUS; ex.artists = list(artists.values())
    ex.body_ko = ("초록의 숲과 흐르는 물, 눈 덮인 대지와 산의 능선. 도시의 빛, 인간의 모습, 추상의 언어와 공예의 섬세한 결까지. "
                  "각기 다른 작품들은 저마다의 시간과 이야기를 품고 있습니다.\n\n"
                  "서로 다른 시선이 하나의 전시가 되는 순간. 작품을 천천히 바라보고, 서로 다른 표현이 만들어 내는 울림과 연결을 발견하는 시간이 되기를 바랍니다.\n\n"
                  "[검수 필요: 공식 전시명, 개막·폐막일, 전시장 주소, 관람 시간]")
    db.session.add(ex)
    db.session.commit()
    print(f"imported: artists {len(artists)}, artworks {count} (from {len(rows)} images), exhibition 1 - status=" + STATUS)
