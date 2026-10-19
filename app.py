import os
from datetime import date
from flask import Flask, render_template, redirect, url_for, g, request, abort, flash, Response
from dotenv import load_dotenv
from models import db, Artist, Artwork, Exhibition, Program, Journal, Media, Inquiry, SiteConfig
import admin

load_dotenv()
BASE = os.path.dirname(os.path.abspath(__file__))
LANGS = ("ko", "en")

# 상황 이미지 기본값 (발주처 사진 수급 전 임시 · Wikimedia Commons CC BY / PD). 어드민 사이트 설정에서 URL 교체.
PICS = {
    "gallery": "https://commons.wikimedia.org/wiki/Special:FilePath/" + "Inside_MAAT_Lisbon_%E2%80%93_Photography_Exhibit_in_the_Oval_Gallery_(54702984107).jpg",
    "museum":  "https://commons.wikimedia.org/wiki/Special:FilePath/" + "Corning_Museum_of_Glass_-_20220212_-_08_-_Contemporary_Art_+_Design_gallery.jpg",
    "studio":  "https://commons.wikimedia.org/wiki/Special:FilePath/" + "DFC_5422_An_artist_at_work_in_a_lively_studio_in_Pattaya_surrounded_by_colorful_paintings_as_he_adds_finishing_touches_to_a_vibrant_floral_canvas.jpg",
    "class":   "https://commons.wikimedia.org/wiki/Special:FilePath/" + "USMC-100519-M-9780H-005.jpg",
    "mentor":  "https://commons.wikimedia.org/wiki/Special:FilePath/" + "USMC-100519-M-9780H-017.jpg",
}


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///" + os.path.join(BASE, "gallery.db")),
    ADMIN_ID=os.getenv("ADMIN_ID", "admin"), ADMIN_PW=os.getenv("ADMIN_PW", "1234"),
    UPLOAD_DIR=os.path.join(BASE, "static", "uploads"),
    MAX_CONTENT_LENGTH=20 * 1024 * 1024,
)
os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
db.init_app(app)
app.register_blueprint(admin.bp)


# ---------- 언어 프리픽스 (/ko/..., /en/...) ----------
@app.url_defaults
def add_lang(endpoint, values):
    if "lang" in values or not g.get("lang"): return
    if app.url_map.is_endpoint_expecting(endpoint, "lang"): values["lang"] = g.lang


@app.url_value_preprocessor
def pull_lang(endpoint, values):
    g.lang = (values or {}).pop("lang", None) or "ko"
    if g.lang not in LANGS: abort(404)


@app.context_processor
def ctx():
    def img(v, w=1200):
        if not v: return ""
        if v.startswith("http"):
            return v + ("&" if "?" in v else "?") + f"width={w}" if "wikimedia.org" in v else v
        return url_for("static", filename="uploads/" + v)
    def t(obj, field):  # 언어별 필드: en 없으면 ko 폴백
        return getattr(obj, f"{field}_{g.lang}", None) or getattr(obj, f"{field}_ko", "")
    def pic(key): return SiteConfig.get("img_" + key) or PICS[key]
    return dict(img=img, t=t, pic=pic, cfg=SiteConfig.get, lang=g.get("lang", "ko"), today=date.today())


@app.route("/")
def root(): return redirect("/ko")


# ---------- 공개 페이지 ----------
@app.route("/<lang>")
def home():
    return render_template("home.html",
        featured=Artist.live().filter_by(featured=True).first(),
        artists=Artist.live().filter(Artist.featured.is_(False)).limit(6).all(),
        works=Artwork.live().filter(Artwork.image.isnot(None)).limit(8).all(),
        exhibitions=Exhibition.live().limit(3).all(),
        programs=Program.live().limit(3).all(),
        media=Media.live().filter_by(platform="youtube").limit(3).all(),
        posts=Journal.live().order_by(Journal.date.desc()).limit(3).all())


@app.route("/<lang>/about")
def about(): return render_template("about.html")


@app.route("/<lang>/global")
def global_(): return render_template("global.html")


@app.route("/<lang>/partnership")
def partnership(): return render_template("partnership.html")


@app.route("/<lang>/artists")
def artists():
    q = Artist.live()
    m = request.args.get("medium")
    if m: q = q.filter(Artist.medium.contains(m))
    mediums = sorted({a.medium for a in Artist.live() if a.medium})
    return render_template("artists.html", artists=q.all(), mediums=mediums, medium=m)


@app.route("/<lang>/artists/<slug>")
def artist(slug):
    a = Artist.query.filter_by(slug=slug, status="published").first_or_404()
    return render_template("artist.html", a=a,
        works=[w for w in a.artworks if w.status == "published"][:8],
        exhibitions=[e for e in a.exhibitions if e.status == "published"],
        videos=[m for m in a.media if m.status == "published"])


@app.route("/<lang>/artworks")
def artworks():
    q = Artwork.live()
    aid, c = request.args.get("artist", type=int), request.args.get("category")
    if aid: q = q.filter_by(artist_id=aid)
    if c: q = q.filter_by(category=c)
    categories = sorted({w.category for w in Artwork.live() if w.category})
    return render_template("artworks.html", works=q.all(), artists=Artist.live().all(), categories=categories, aid=aid, category=c)


@app.route("/<lang>/artworks/<slug>")
def artwork(slug):
    w = Artwork.query.filter_by(slug=slug, status="published").first_or_404()
    rel = Artwork.live().filter(Artwork.id != w.id)
    rel = rel.filter(Artwork.artist_id == w.artist_id) if w.artist_id else rel.filter(Artwork.category == w.category)
    related = rel.limit(4).all()
    return render_template("artwork.html", w=w, related=related)


@app.route("/<lang>/exhibitions")
def exhibitions():
    rows = Exhibition.live().all()
    groups = {k: [e for e in rows if e.phase == k] for k in ("current", "upcoming", "past")}
    return render_template("exhibitions.html", groups=groups)


@app.route("/<lang>/exhibitions/<slug>")
def exhibition(slug):
    e = Exhibition.query.filter_by(slug=slug, status="published").first_or_404()
    return render_template("exhibition.html", e=e, videos=[m for m in e.media if m.status == "published"])


@app.route("/<lang>/academy")
def academy():
    rows = Program.live().all()
    return render_template("academy.html", programs=rows, mirini=[p for p in rows if p.category == "mirini"])


@app.route("/<lang>/academy/mirini")
def mirini(): return render_template("mirini.html", programs=Program.live().filter_by(category="mirini").all())


@app.route("/<lang>/journal")
def journal():
    q = Journal.live().order_by(Journal.date.desc())
    c = request.args.get("category")
    if c: q = q.filter_by(category=c)
    rows = q.all()
    return render_template("journal.html", posts=rows, lead=rows[0] if rows and not c else None, category=c)


@app.route("/<lang>/journal/<slug>")
def journal_post(slug):
    p = Journal.query.filter_by(slug=slug, status="published").first_or_404()
    more = Journal.live().filter(Journal.id != p.id).order_by(Journal.date.desc()).limit(3).all()
    return render_template("journal_post.html", p=p, more=more)


@app.route("/<lang>/media")
def media():
    rows = Media.live().order_by(Media.date.desc()).all()
    return render_template("media.html",
        yt=[m for m in rows if m.platform == "youtube"], ig=[m for m in rows if m.platform == "instagram"],
        posts=Journal.live().order_by(Journal.date.desc()).limit(3).all())


@app.route("/<lang>/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        f = request.form
        if f.get("website"):  # honeypot
            return redirect(url_for("contact", sent=1))
        if not (f.get("name") and f.get("email") and f.get("message") and f.get("consent")):
            flash("필수 항목을 확인해 주세요.")
        else:
            db.session.add(Inquiry(kind=f.get("kind", "general"), name=f["name"], email=f["email"],
                                   organization=f.get("organization"), country=f.get("country"),
                                   message=f["message"], consent=True))
            db.session.commit()
            return redirect(url_for("contact", sent=1))
    return render_template("contact.html", kind=request.args.get("kind", "general"), sent=request.args.get("sent"))


# ---------- SEO ----------
@app.route("/sitemap.xml")
def sitemap():
    urls = [url_for(e, lang="ko", _external=True) for e in
            ("home", "about", "global_", "partnership", "artists", "artworks", "exhibitions", "academy", "mirini", "journal", "media", "contact")]
    for M, ep in ((Artist, "artist"), (Artwork, "artwork"), (Exhibition, "exhibition"), (Journal, "journal_post")):
        urls += [url_for(ep, lang="ko", slug=r.slug, _external=True) for r in M.live()]
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + \
          "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>"
    return Response(xml, mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    return Response(f"User-agent: *\nDisallow: /admin\nSitemap: {url_for('sitemap', _external=True)}\n", mimetype="text/plain")


@app.errorhandler(404)
def nf(e):
    g.lang = g.get("lang") or "ko"
    return render_template("404.html"), 404


if __name__ == "__main__":
    with app.app_context(): db.create_all()
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 8088)), debug=True)
