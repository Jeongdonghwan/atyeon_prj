"""초기 데이터: 퍼블릭 도메인 명화로 채운 샘플. 실제 작가·작품은 어드민에서 교체.
실행: python seed.py  (기존 DB 삭제 후 재생성)"""
import os
from datetime import date, timedelta
from app import app, PICS as PIC
from models import db, Artist, Artwork, Exhibition, Program, Journal, Media, SiteConfig

W = "https://commons.wikimedia.org/wiki/Special:FilePath/"
IMG = {
    "wave": W + "Tsunami_by_hokusai_19th_century.jpg",
    "starry": W + "Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
    "almond": W + "Vincent_van_Gogh_-_Almond_blossom_-_Google_Art_Project.jpg",
    "crows": W + "Vincent_van_Gogh_-_Wheatfield_with_crows_-_Google_Art_Project.jpg",
    "kiss": W + "Gustav_Klimt_016.jpg",
    "lilies1": W + "Claude_Monet_-_Water_Lilies_-_1906,_Ryerson.jpg",
    "lilies2": W + "Claude_Monet_-_Water_Lilies_-_Google_Art_Project_(462013).jpg",
    "kandinsky": W + "Vassily_Kandinsky,_1923_-_Composition_8,_huile_sur_toile,_140_cm_x_201_cm,_Mus%C3%A9e_Guggenheim,_New_York.jpg",
    "mondrian": W + "Piet_Mondriaan,_1930_-_Mondrian_Composition_II_in_Red,_Blue,_and_Yellow.jpg",
    "klee": W + "Paul_Klee,_Swiss_-_Fish_Magic_-_Google_Art_Project.jpg",
    "scream": W + "Edvard_Munch,_1893,_The_Scream,_oil,_tempera_and_pastel_on_cardboard,_91_x_73_cm,_National_Gallery_of_Norway.jpg",
    "seurat": W + "Georges_Seurat_-_A_Sunday_on_La_Grande_Jatte_--_1884_-_Google_Art_Project.jpg",
    "cezanne": W + "Paul_C%C3%A9zanne_-_Mont_Sainte-Victoire_-_Google_Art_Project.jpg",
    "gris": W + "Juan_Gris_-_Portrait_of_Pablo_Picasso_-_Google_Art_Project.jpg",
}
PD = "퍼블릭 도메인 (Wikimedia Commons) · 샘플"
T = date.today()

with app.app_context():
    db.drop_all(); db.create_all()
    P = "published"

    def artist(slug, ko, en, tag, med, img, cover, note, cv, feat=False):
        return Artist(slug=slug, name_ko=ko, name_en=en, tagline_ko=tag, medium=med, portrait=img, cover=cover,
                      bio_ko=f"{ko}은(는) {med}를 중심으로 고유한 시선을 탐구합니다.\n\n[작가 소개 본문 — 활동 이력, 주요 전시, 작업의 태도. 승인 문안으로 교체]",
                      note_ko=note, cv_ko=cv, featured=feat, status=P)

    a1 = artist("hokusai", "가쓰시카 호쿠사이", "Katsushika Hokusai", "파도 하나에 세계를 담다", "목판화", IMG["wave"], IMG["wave"],
                "산을 그리려면 산이 되어야 한다. 파도를 그리려면 파도 속에 있어야 한다.", "1831 후가쿠 36경 연작 발표\n1834 후가쿠 백경 간행\n2026 [전시명] 참여", True)
    a2 = artist("van-gogh", "빈센트 반 고흐", "Vincent van Gogh", "밤하늘을 흐르게 만든 붓질", "회화 · 유채", IMG["starry"], IMG["crows"],
                "나는 별을 보면 언제나 꿈을 꾼다.", "1888 아를 시기\n1889 생레미 시기\n1890 오베르 시기")
    a3 = artist("monet", "클로드 모네", "Claude Monet", "빛이 머무는 순간의 기록", "회화 · 유채", IMG["lilies1"], IMG["lilies2"],
                "나는 단지 보는 것을 그릴 뿐이다.", "1874 제1회 인상주의전\n1899 수련 연작 시작")
    a4 = artist("kandinsky", "바실리 칸딘스키", "Wassily Kandinsky", "소리를 색으로, 색을 형태로", "회화 · 추상", IMG["kandinsky"], IMG["kandinsky"],
                "색은 영혼에 직접 영향을 미치는 힘이다.", "1911 청기사파 결성\n1922 바우하우스 교수")
    a5 = artist("klimt", "구스타프 클림트", "Gustav Klimt", "금빛으로 감싼 인간의 순간", "회화 · 혼합", IMG["kiss"], IMG["kiss"],
                "모든 예술은 에로틱하다.", "1897 빈 분리파 창립\n1908 '키스' 발표")
    a6 = artist("mondrian", "피트 몬드리안", "Piet Mondrian", "수직과 수평이 만드는 균형", "회화 · 추상", IMG["mondrian"], IMG["mondrian"],
                "예술은 자연보다 높다.", "1917 데 스틸 창간")
    db.session.add_all([a1, a2, a3, a4, a5, a6]); db.session.flush()

    works = [
        ("great-wave", "가나가와 해변의 높은 파도", a1, "1831", "다색 목판화", "25.7 × 37.9", IMG["wave"], True),
        ("starry-night", "별이 빛나는 밤", a2, "1889", "캔버스에 유채", "73.7 × 92.1", IMG["starry"], True),
        ("almond-blossom", "꽃 피는 아몬드 나무", a2, "1890", "캔버스에 유채", "73.3 × 92.4", IMG["almond"], True),
        ("wheatfield-crows", "까마귀가 나는 밀밭", a2, "1890", "캔버스에 유채", "50.5 × 103", IMG["crows"], False),
        ("water-lilies-1906", "수련", a3, "1906", "캔버스에 유채", "87.6 × 92.7", IMG["lilies1"], True),
        ("water-lilies-1919", "수련", a3, "1919", "캔버스에 유채", "100 × 200", IMG["lilies2"], False),
        ("composition-8", "구성 VIII", a4, "1923", "캔버스에 유채", "140 × 201", IMG["kandinsky"], True),
        ("the-kiss", "키스", a5, "1908", "캔버스에 유채·금박", "180 × 180", IMG["kiss"], True),
        ("composition-ii", "빨강, 파랑, 노랑의 구성 II", a6, "1930", "캔버스에 유채", "46 × 46", IMG["mondrian"], True),
        ("fish-magic", "물고기 마술", None, "1925", "캔버스에 유채·수채", "77 × 98", IMG["klee"], False),
        ("mont-sainte-victoire", "생트빅투아르 산", None, "1887", "캔버스에 유채", "67 × 92", IMG["cezanne"], False),
        ("the-scream", "절규", None, "1893", "판지에 유채·템페라·파스텔", "91 × 73", IMG["scream"], False),
    ]
    for i, (slug, t, a, y, m, d, img, f) in enumerate(works):
        db.session.add(Artwork(slug=slug, title_ko=t, artist=a, year=y, medium_ko=m, dimensions=d, image=img, featured=f,
                               rights=PD, sort=i, status=P, note_ko="[작가의 의도와 조형적 특성 100~160자 — 승인 문안으로 교체]"))

    db.session.add_all([
        Exhibition(slug="art-beyond-borders-2026", title_ko="Art Beyond Borders", title_en="Art Beyond Borders", start_date=T - timedelta(days=9), end_date=T + timedelta(days=50),
                   location="일조원갤러리", cover=IMG["seurat"], artists=[a1, a2, a3], status=P,
                   body_ko="[전시 서문 — 기획 의도, 참여 작가, 구성. 승인 문안으로 교체]\n\n경계를 넘어 만나는 세 작가의 시선을 한 공간에 모았습니다."),
        Exhibition(slug="color-and-form", title_ko="색과 형태", title_en="Color & Form", start_date=T + timedelta(days=61), end_date=T + timedelta(days=120),
                   location="일조원갤러리", cover=IMG["klee"], artists=[a4, a6], status=P, body_ko="[예정 전시 소개 — 승인 문안으로 교체]"),
        Exhibition(slug="golden-hour", title_ko="골든 아워", title_en="Golden Hour", start_date=T - timedelta(days=144), end_date=T - timedelta(days=46),
                   location="일조원갤러리", cover=IMG["kiss"], artists=[a5], status=P, body_ko="[지난 전시 기록 — 승인 문안으로 교체]"),
    ])
    db.session.add_all([
        Program(slug="mirini-101", title_ko="미린이 101 · 처음 만나는 미술", category="mirini", audience="입문", schedule="격주 토요일 · 4회", cover=PIC["class"], summary_ko="LEARN · MEET · MAKE · SHARE", status=P, sort=0),
        Program(slug="mirini-201", title_ko="미린이 201 · 작품을 읽는 법", category="mirini", audience="입문 수료자", schedule="매월 1회", cover=PIC["museum"], summary_ko="한 작품을 이해하는 세 가지 질문", status=P, sort=1),
        Program(slug="artist-talk", title_ko="작가와의 만남", category="talk", audience="누구나", schedule="전시 기간 중", cover=PIC["studio"], summary_ko="작업실에서 듣는 작품의 시작", status=P, sort=2),
        Program(slug="lecture-series", title_ko="렉처 시리즈 · 국제 미술 현장", category="lecture", audience="누구나", schedule="분기 1회", cover=PIC["gallery"], summary_ko="한국과 세계가 만나는 아트 현장", status=P, sort=3),
    ])
    db.session.add_all([
        Journal(slug="interview-hokusai", title_ko="[인터뷰] 파도 하나에 세계를 담다", category="interview", date=T - timedelta(days=8), cover=IMG["wave"], artist=a1, status=P,
                summary_ko="한 장의 판화가 어떻게 세계의 이미지가 되었는지, 작가의 작업실에서 묻습니다.", body_ko="[인터뷰 본문 — 승인 문안으로 교체]\n\n[문단 2]\n\n[문단 3]"),
        Journal(slug="behind-art-beyond-borders", title_ko="전시 뒷이야기 — Art Beyond Borders가 만들어지기까지", category="behind", date=T - timedelta(days=16), cover=IMG["seurat"], status=P,
                summary_ko="세 작가의 작품이 한 공간에 놓이기까지, 기획과 설치의 기록.", body_ko="[본문 — 승인 문안으로 교체]"),
        Journal(slug="global-first-dialogue", title_ko="해외 갤러리와의 첫 대화, 무엇을 묻고 무엇을 들었나", category="global", date=T - timedelta(days=30), cover=IMG["mondrian"], status=P,
                summary_ko="국제 교류의 첫 단계에서 오간 질문들.", body_ko="[본문 — 승인 문안으로 교체]"),
        Journal(slug="review-lilies", title_ko="빛이 머무는 자리 — 모네의 수련 다시 보기", category="review", date=T - timedelta(days=45), cover=IMG["lilies2"], artist=a3, status=P,
                summary_ko="같은 연못을 수백 번 그린 이유.", body_ko="[본문 — 승인 문안으로 교체]"),
    ])
    # 영상: video_id는 샘플(교체 필요). thumb 없으면 YouTube 썸네일 사용
    db.session.add_all([
        Media(slug="in-the-studio-1", platform="youtube", series="IN THE STUDIO", title_ko="작가의 공간에서 발견하는 작품의 시작", video_id="", url="#", thumb=PIC["studio"], date=T - timedelta(days=5), artist=a2, status=P),
        Media(slug="one-work-1", platform="youtube", series="ONE WORK, ONE STORY", title_ko="한 작품을 이해하는 세 가지 질문", video_id="", url="#", thumb=PIC["museum"], date=T - timedelta(days=12), artist=a1, status=P),
        Media(slug="exhibition-notes-1", platform="youtube", series="EXHIBITION NOTES", title_ko="전시가 만들어지는 순간", video_id="", url="#", thumb=PIC["gallery"], date=T - timedelta(days=20), status=P),
        Media(slug="mirini-class-1", platform="youtube", series="MIRINI CLASS", title_ko="처음 미술을 보는 사람을 위한 5분", video_id="", url="#", thumb=PIC["class"], date=T - timedelta(days=28), status=P),
        Media(slug="reel-1", platform="instagram", series="Reels", title_ko="설치 전경 타임랩스", url="#", thumb=PIC["gallery"], date=T - timedelta(days=3), status=P),
        Media(slug="reel-2", platform="instagram", series="Reels", title_ko="작가 토크 하이라이트", url="#", thumb=PIC["mentor"], date=T - timedelta(days=6), status=P),
        Media(slug="reel-3", platform="instagram", series="Reels", title_ko="미린이 101 현장", url="#", thumb=PIC["class"], date=T - timedelta(days=9), status=P),
        Media(slug="reel-4", platform="instagram", series="Reels", title_ko="오프닝 스케치", url="#", thumb=PIC["studio"], date=T - timedelta(days=14), status=P),
    ])
    for k, v in {"site_name": "CHEONGYEON", "tagline": "한국의 예술적 자산을 세계와 잇고, 세계의 다양한 예술적 시선을 한국에 소개하는 아트·교류·교육 플랫폼.",
                 "email": "", "phone": "", "address": "", "youtube": "", "instagram": ""}.items():
        db.session.add(SiteConfig(key=k, value=v))
    db.session.commit()
    print("seeded:", Artist.query.count(), "artists,", Artwork.query.count(), "artworks,", Exhibition.query.count(), "exhibitions")
