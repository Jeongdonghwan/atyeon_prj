"""SEO: 페이지별 제목·설명·키워드, 절대 URL, JSON-LD, sitemap.xml, robots.txt, rss.xml.
주업(그림 판매·전시)이 검색에 걸리도록 키워드 축: 그림 판매/구매 · 미술품 · 갤러리 전시 · 종로/인사동/안국 갤러리."""
import os
from datetime import datetime, time
from email.utils import format_datetime
from xml.sax.saxutils import escape
from flask import Blueprint, Response, url_for, request, g
from models import Artist, Artwork, Exhibition, Journal, SiteConfig

SITE_URL = os.getenv("SITE_URL", "http://211.45.175.195:8144").rstrip("/")
BRAND = "아르테연"
BRAND_EN = "ARTEYEON"
BRAND_FULL = f"{BRAND} {BRAND_EN}"
ADDRESS = "서울시 종로구 우정국로 38 B1"
CORE_KW = "아르테연, ARTEYEON, 그림 판매, 그림 구매, 미술품 판매, 미술 작품 구매, 갤러리, 미술 전시, 전시회, 종로 갤러리, 인사동 갤러리, 안국역 갤러리, 일조원갤러리, 현대미술, 서양화, 한국화"

# endpoint → (제목, 설명, 추가 키워드). 상세 페이지는 템플릿 block으로 덮어씀.
PAGES = {
    "home": ("아르테연 ARTEYEON | 그림 판매·미술품 구매·갤러리 전시 — 종로 일조원갤러리",
             "아르테연은 서울 종로(안국·인사동) 일조원갤러리에서 한국 현대미술 작가의 그림 판매와 전시를 진행합니다. 회화·한국화·도자 작품 구매 상담, 기획 전시, 작가와의 대화 프로그램을 만나보세요.",
             "그림 사는 곳, 미술품 구입, 원화 구매, 그림 선물"),
    "artworks": ("그림 판매·작품 아카이브 | 아르테연",
                 "아르테연이 소개하는 회화·한국화·추상·도자 작품 아카이브. 작품명·작가·재료·규격을 확인하고 그림 구매 상담을 신청하세요.",
                 "그림 판매, 원화 판매, 작품 구매, 회화 판매, 추상화, 풍경화, 도자기"),
    "artists": ("참여 작가 | 아르테연 — 한국 현대미술 작가",
                "아르테연과 함께하는 한국 현대미술 작가들. 작가별 대표 작품과 작업 세계, 전시 이력을 소개합니다.",
                "한국 작가, 현대미술 작가, 화가, 신진 작가"),
    "exhibitions": ("전시 일정 | 아르테연 — 종로 일조원갤러리 전시회",
                    "서울 종로 일조원갤러리에서 열리는 아르테연의 현재·예정·지난 전시. 전시 일정과 관람 안내를 확인하세요.",
                    "전시 일정, 서울 전시회, 종로 전시, 인사동 전시, 무료 전시, 12월 전시"),
    "about": ("아르테연 소개 | 그림 판매와 전시를 잇는 아트 플랫폼",
              "아르테연은 작가와 컬렉터, 갤러리와 관객을 연결합니다. 일조원갤러리의 전시·큐레이션 경험으로 작품 판매와 기획 전시를 운영합니다.",
              "아트 플랫폼, 큐레이션, 아트 컨설팅"),
    "contact": ("작품 구매·전시 문의 | 아르테연",
                "그림 구매 상담, 작품 소장 문의, 전시·대관·협업 제안을 남겨주세요. 아르테연 담당자가 연락드립니다.",
                "그림 구매 상담, 작품 구매 문의, 전시 문의, 갤러리 문의"),
    "global_": ("국제 교류 | 아르테연", "해외 갤러리·기관과의 공동 전시, 작가 교류, 콘텐츠 협업을 제안합니다.", "국제 전시, 해외 갤러리 협업"),
    "partnership": ("파트너십 제안 | 아르테연", "갤러리·기관·기업과의 전시 협업과 작품 판매 파트너십 제안을 받습니다.", "전시 협업, 기업 미술품, 아트 파트너십"),
    "journal": ("저널 | 아르테연", "작가 인터뷰, 전시 뒷이야기, 작품 읽기.", "미술 칼럼, 작가 인터뷰"),
    "media": ("미디어 | 아르테연", "작업실과 전시 현장을 기록한 영상.", "미술 영상"),
    "academy": ("아카데미 | 아르테연", "미술을 처음 만나는 사람을 위한 프로그램.", "미술 교육"),
    "mirini": ("미린이 프로젝트 | 아르테연", "미술 입문 프로젝트.", "미술 입문"),
    "apply_check": ("신청 확인 | 아르테연", "행사 신청 내역을 확인합니다.", ""),
}
# 내용이 아직 비었거나 샘플인 페이지 → noindex + 사이트맵 제외 (실콘텐츠 들어오면 여기서 빼기)
NOINDEX = {"journal", "journal_post", "media", "academy", "mirini", "apply_check", "event_apply", "nf"}


def abs_url(path): return SITE_URL + path


def canonical():
    if not request.endpoint or request.endpoint == "nf": return ""
    args = dict(request.view_args or {}); args["lang"] = "ko"
    return abs_url(url_for(request.endpoint, **args))


def abs_img(v, img):
    u = img(v, 1200) if v else ""
    return u if u.startswith("http") else (abs_url(u) if u else "")


def page_meta(endpoint):
    t, d, k = PAGES.get(endpoint, (BRAND_FULL, PAGES["home"][1], ""))
    return {"title": t, "desc": d, "keywords": ", ".join(x for x in (k, CORE_KW) if x),
            "noindex": not endpoint or endpoint in NOINDEX or getattr(g, "lang", "ko") != "ko"}


# ---------- JSON-LD ----------
def org_ld():
    return {"@context": "https://schema.org", "@type": "ArtGallery", "name": BRAND_FULL, "alternateName": [BRAND, BRAND_EN, "일조원갤러리"],
            "url": SITE_URL + "/ko", "telephone": "02-725-3588",
            "address": {"@type": "PostalAddress", "streetAddress": "우정국로 38 B1", "addressLocality": "종로구", "addressRegion": "서울특별시", "addressCountry": "KR"},
            "openingHours": "Sa 11:00-18:00",
            "sameAs": [u for u in (SiteConfig.get("youtube"), SiteConfig.get("instagram")) if u]}


def website_ld():
    return {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND_FULL, "url": SITE_URL + "/ko", "inLanguage": "ko-KR"}


def crumb_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": abs_url(u)} for i, (n, u) in enumerate(items)]}


def itemlist_ld(rows, ep, img):
    return {"@context": "https://schema.org", "@type": "ItemList",
            "itemListElement": [dict({"@type": "ListItem", "position": i + 1, "url": abs_url(url_for(ep, lang="ko", slug=r.slug)),
                                      "name": getattr(r, "title_ko", None) or r.name_ko},
                                     **({"image": abs_img(getattr(r, "image", None) or getattr(r, "cover", None), img)} if (getattr(r, "image", None) or getattr(r, "cover", None)) else {}))
                                for i, r in enumerate(rows)]}


def artwork_ld(w, img):
    d = {"@context": "https://schema.org", "@type": "VisualArtwork", "name": w.title_ko, "url": abs_url(url_for("artwork", lang="ko", slug=w.slug))}
    if w.image: d["image"] = abs_img(w.image, img)
    if w.artist: d["creator"] = {"@type": "Person", "name": w.artist.name_ko}
    if w.medium_ko: d["artMedium"] = w.medium_ko
    if w.year: d["dateCreated"] = w.year
    if w.category: d["genre"] = w.category
    if w.note_ko: d["description"] = w.note_ko
    if w.dimensions and "×" in w.dimensions:
        h, wd = [x.strip() for x in w.dimensions.split("×")[:2]]
        d["height"] = {"@type": "Distance", "name": f"{h} cm"}; d["width"] = {"@type": "Distance", "name": f"{wd} cm"}
    return d


def person_ld(a, img):
    d = {"@context": "https://schema.org", "@type": "Person", "name": a.name_ko, "jobTitle": "미술 작가", "url": abs_url(url_for("artist", lang="ko", slug=a.slug))}
    if a.name_en: d["alternateName"] = a.name_en
    if a.portrait or a.cover: d["image"] = abs_img(a.portrait or a.cover, img)
    return d


def event_ld(e, img):
    def dt(tstr):
        h, m = (tstr or "11:00").split(":")[:2]
        return datetime.combine(e.start_date, time(int(h), int(m))).isoformat() + "+09:00"
    t0, t1 = (e.hours or "11:00~18:00").replace(" ", "").split("~")[:2]
    url = abs_url(url_for("exhibition", lang="ko", slug=e.slug))
    d = {"@context": "https://schema.org", "@type": "ExhibitionEvent", "name": e.title_ko, "description": (e.body_ko or "").split("\n")[0],
         "startDate": dt(t0), "endDate": dt(t1), "eventStatus": "https://schema.org/EventScheduled",
         "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "url": url,
         "location": {"@type": "Place", "name": e.location, "address": {"@type": "PostalAddress", "streetAddress": e.address or ADDRESS, "addressCountry": "KR"}},
         "organizer": {"@type": "Organization", "name": BRAND_FULL, "url": SITE_URL + "/ko"},
         "isAccessibleForFree": True}
    if e.poster or e.cover: d["image"] = [abs_img(e.poster or e.cover, img)]
    if e.names: d["performer"] = [{"@type": "Person", "name": n} for n in e.names]
    if e.fee:
        d["offers"] = {"@type": "Offer", "name": e.program_title, "price": e.fee, "priceCurrency": "KRW",
                       "availability": "https://schema.org/InStock" if e.can_apply else "https://schema.org/SoldOut",
                       "url": abs_url(url_for("event_apply", lang="ko", slug=e.slug))}
    return d


# ---------- sitemap / robots / rss ----------
bp = Blueprint("seo", __name__)


def _lastmod(*objs):
    ts = [o.created_at for o in objs if o is not None and getattr(o, "created_at", None)]
    return max(ts).strftime("%Y-%m-%d") if ts else None


@bp.route("/sitemap.xml")
def sitemap():
    works, artists, exhibitions = Artwork.live().all(), Artist.live().all(), Exhibition.live().all()
    allm = _lastmod(*(works + artists + exhibitions))
    rows = [(url_for("home", lang="ko"), allm, "1.0", None),
            (url_for("artworks", lang="ko"), _lastmod(*works), "0.9", None),
            (url_for("exhibitions", lang="ko"), _lastmod(*exhibitions), "0.9", None),
            (url_for("artists", lang="ko"), _lastmod(*artists), "0.8", None),
            (url_for("about", lang="ko"), None, "0.6", None),
            (url_for("contact", lang="ko"), None, "0.6", None),
            (url_for("global_", lang="ko"), None, "0.4", None),
            (url_for("partnership", lang="ko"), None, "0.4", None)]
    rows += [(url_for("exhibition", lang="ko", slug=e.slug), _lastmod(e), "0.9" if e.is_event else "0.7", e.poster or e.cover) for e in exhibitions]
    rows += [(url_for("artwork", lang="ko", slug=w.slug), _lastmod(w), "0.7", w.image) for w in works]
    rows += [(url_for("artist", lang="ko", slug=a.slug), _lastmod(a), "0.6", a.portrait or a.cover) for a in artists]
    from app import app
    img = app.jinja_env.globals.get("_img")
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for path, lm, pr, im in rows:
        out.append("<url><loc>" + escape(abs_url(path)) + "</loc>" + (f"<lastmod>{lm}</lastmod>" if lm else "") + f"<priority>{pr}</priority>"
                   + (f"<image:image><image:loc>{escape(abs_img(im, img))}</image:loc></image:image>" if im else "") + "</url>")
    out.append("</urlset>")
    return Response("\n".join(out), mimetype="application/xml")


@bp.route("/robots.txt")
def robots():
    return Response("User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /en\nDisallow: /ko/apply/\nDisallow: /*/apply$\n"
                    f"\nSitemap: {SITE_URL}/sitemap.xml\n", mimetype="text/plain")


@bp.route("/rss.xml")
@bp.route("/rss")
def rss():
    """네이버용 RSS: 행사·전시 + 작품(최신 50). 본문 전체 포함."""
    from app import app
    img = app.jinja_env.globals.get("_img")
    items = []
    for e in Exhibition.live().all():
        when = f"{e.start_date:%Y.%m.%d} {e.hours or ''} · {e.location or ''} {e.address or ''}"
        body = f"{when}<br>{(e.body_ko or '').replace(chr(10), '<br>')}"
        if e.program_title: body += f"<br>{e.program_title} {e.program_time} · 참가비 {e.fee:,}원 · 사전 신청 {e.capacity}명"
        items.append((e.created_at, e.title_ko, url_for("exhibition", lang="ko", slug=e.slug), body, e.poster or e.cover))
    for w in Artwork.live().all():
        who = w.artist.name_ko if w.artist else ""
        spec = " · ".join(x for x in (who, w.year, w.medium_ko, (w.dimensions + " cm") if w.dimensions else "") if x)
        items.append((w.created_at, f"{w.title_ko}{' — ' + who if who else ''} | 그림 판매·작품 아카이브", url_for("artwork", lang="ko", slug=w.slug),
                      f"{spec}<br>{w.note_ko or ''}<br>작품 구매 상담: 아르테연 02-725-3588", w.image))
    items.sort(key=lambda x: x[0] or datetime.min, reverse=True)
    xs = []
    for dt_, title, path, body, im in items[:50]:
        u = abs_url(path); iu = abs_img(im, img) if im else ""
        desc = (f'<img src="{iu}" alt="{escape(title)}"><br>' if iu else "") + body
        xs.append(f"<item><title>{escape(title)}</title><link>{escape(u)}</link><guid isPermaLink=\"true\">{escape(u)}</guid>"
                  f"<pubDate>{format_datetime((dt_ or datetime.now()).astimezone())}</pubDate>"
                  f"<description><![CDATA[{desc}]]></description></item>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
           f"<title>{BRAND_FULL} — 그림 판매·갤러리 전시</title><link>{SITE_URL}/ko</link>"
           f"<description>{escape(PAGES['home'][1])}</description><language>ko</language>"
           f'<atom:link href="{SITE_URL}/rss.xml" rel="self" type="application/rss+xml"/>' + "".join(xs) + "</channel></rss>")
    return Response(xml, mimetype="application/rss+xml")
