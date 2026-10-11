"""어드민: 세션 로그인 1계정 + 모델별 범용 CRUD + 이미지 업로드(WebP 변환)."""
import os, re, uuid
from datetime import date, datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, abort
from sqlalchemy import inspect, String, Text, Boolean, Integer, Date, Enum
from PIL import Image
from models import db, Artist, Artwork, Exhibition, Program, Journal, Media, Inquiry, SiteConfig

bp = Blueprint("admin", __name__, url_prefix="/admin")

# 어드민에 노출할 모델: name -> (Model, 라벨, 목록 컬럼)
MODELS = {
    "artist":     (Artist,     "작가",     ["name_ko", "medium", "featured", "status"]),
    "artwork":    (Artwork,    "작품",     ["title_ko", "artist_id", "year", "featured", "status"]),
    "exhibition": (Exhibition, "전시",     ["title_ko", "start_date", "end_date", "location", "status"]),
    "program":    (Program,    "아카데미", ["title_ko", "category", "schedule", "status"]),
    "journal":    (Journal,    "저널",     ["title_ko", "category", "date", "status"]),
    "media":      (Media,      "미디어",   ["title_ko", "platform", "series", "date", "status"]),
}
IMAGE_COLS = {"portrait", "cover", "image", "thumb"}
HIDDEN = {"id", "created_at"}
LABELS = {  # 폼 라벨 (없으면 컬럼명)
    "name_ko": "이름(국문)", "name_en": "이름(영문)", "title_ko": "제목(국문)", "title_en": "제목(영문)",
    "tagline_ko": "한 문장 소개", "medium": "매체", "medium_ko": "재료/매체", "bio_ko": "소개(국문)", "bio_en": "소개(영문)",
    "note_ko": "노트", "cv_ko": "CV / 전시 이력 (한 줄에 하나)", "portrait": "초상 이미지", "cover": "커버 이미지",
    "image": "작품 이미지", "thumb": "썸네일", "featured": "메인 추천", "status": "상태", "sort": "정렬(낮을수록 앞)",
    "slug": "URL 슬러그", "artist_id": "작가", "exhibition_id": "전시", "year": "제작연도", "dimensions": "규격(cm)",
    "rights": "저작권/출처", "start_date": "시작일", "end_date": "종료일", "location": "장소", "body_ko": "본문(국문)",
    "body_en": "본문(영문)", "category": "분류", "audience": "대상", "summary_ko": "요약", "schedule": "일정",
    "inquiry_link": "신청 링크", "date": "날짜", "platform": "플랫폼", "series": "시리즈", "url": "원본 URL",
    "video_id": "YouTube 영상 ID",
}


@bp.context_processor
def _side():
    return dict(models=MODELS, unread=Inquiry.query.filter_by(read=False).count() if session.get("admin") else 0)


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("admin"):
            return redirect(url_for("admin.login", next=request.path))
        return f(*a, **k)
    return w


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["id"] == current_app.config["ADMIN_ID"] and request.form["pw"] == current_app.config["ADMIN_PW"]:
            session["admin"] = True
            return redirect(request.args.get("next") or url_for("admin.dashboard"))
        flash("아이디 또는 비밀번호가 다릅니다.")
    return render_template("admin/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@bp.route("/")
@login_required
def dashboard():
    counts = {k: (v[1], v[0].query.count()) for k, v in MODELS.items()}
    inquiries = Inquiry.query.order_by(Inquiry.created_at.desc()).limit(8).all()
    unread = Inquiry.query.filter_by(read=False).count()
    return render_template("admin/dashboard.html", counts=counts, inquiries=inquiries, unread=unread)


# ---------- 범용 CRUD ----------
def _model(name):
    if name not in MODELS: abort(404)
    return MODELS[name]


def _fields(Model):
    """폼에 그릴 컬럼 메타: (name, kind, choices)"""
    out = []
    for c in inspect(Model).columns:
        if c.name in HIDDEN: continue
        t = c.type
        if c.name in IMAGE_COLS: kind, choices = "image", None
        elif c.name.endswith("_id"):
            rel = Artist if c.name == "artist_id" else Exhibition
            kind, choices = "select", [("", "—")] + [(str(r.id), str(r)) for r in rel.query.order_by(rel.id).all()]
        elif isinstance(t, Enum): kind, choices = "select", [(e, e) for e in t.enums]
        elif isinstance(t, Boolean): kind, choices = "bool", None
        elif isinstance(t, Date): kind, choices = "date", None
        elif isinstance(t, Text): kind, choices = "text", None
        elif isinstance(t, Integer): kind, choices = "number", None
        else: kind, choices = "string", None
        out.append((c.name, kind, choices, LABELS.get(c.name, c.name)))
    return out


def _save_image(file):
    """업로드 → static/uploads/<uuid>.webp (최대 2000px)"""
    im = Image.open(file.stream).convert("RGB")
    im.thumbnail((2000, 2000))
    name = f"{uuid.uuid4().hex}.webp"
    im.save(os.path.join(current_app.config["UPLOAD_DIR"], name), "WEBP", quality=85)
    return name


def _slugify(s):
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"[\s_-]+", "-", s) or uuid.uuid4().hex[:8]


def _apply(obj, Model):
    for name, kind, _, _ in _fields(Model):
        if kind == "image":
            f = request.files.get(name)
            if f and f.filename: setattr(obj, name, _save_image(f))
            elif request.form.get(name + "_url") is not None: setattr(obj, name, request.form.get(name + "_url") or None)
            continue
        v = request.form.get(name)
        if kind == "bool": v = name in request.form
        elif kind == "date": v = date.fromisoformat(v) if v else None
        elif kind == "number": v = int(v) if v else 0
        elif kind == "select" and name.endswith("_id"): v = int(v) if v else None
        elif v == "": v = None
        setattr(obj, name, v)
    if hasattr(obj, "slug") and not obj.slug:
        obj.slug = _slugify(getattr(obj, "name_en", None) or getattr(obj, "title_en", None)
                            or getattr(obj, "name_ko", None) or getattr(obj, "title_ko", ""))
    if Model is Exhibition:
        ids = [int(i) for i in request.form.getlist("artists")]
        obj.artists = Artist.query.filter(Artist.id.in_(ids)).all() if ids else []


@bp.route("/<name>")
@login_required
def list_(name):
    Model, label, cols = _model(name)
    rows = Model.query.order_by(Model.sort, Model.id.desc()).all()
    return render_template("admin/list.html", name=name, label=label, cols=cols, rows=rows, labels=LABELS)


@bp.route("/<name>/new", methods=["GET", "POST"])
@bp.route("/<name>/<int:id>", methods=["GET", "POST"])
@login_required
def edit(name, id=None):
    Model, label, _ = _model(name)
    obj = db.session.get(Model, id) if id else Model()
    if id and not obj: abort(404)
    if request.method == "POST":
        _apply(obj, Model)
        db.session.add(obj)
        db.session.commit()
        flash("저장했습니다.")
        return redirect(url_for("admin.list_", name=name))
    extra = {"artists": Artist.query.order_by(Artist.name_ko).all()} if Model is Exhibition else {}
    return render_template("admin/form.html", name=name, label=label, obj=obj, fields=_fields(Model), **extra)


@bp.post("/<name>/<int:id>/delete")
@login_required
def delete(name, id):
    Model, _, _ = _model(name)
    obj = db.session.get(Model, id) or abort(404)
    db.session.delete(obj); db.session.commit()
    flash("삭제했습니다.")
    return redirect(url_for("admin.list_", name=name))


# ---------- 문의 / 설정 ----------
@bp.route("/inquiry")
@login_required
def inquiries():
    rows = Inquiry.query.order_by(Inquiry.created_at.desc()).all()
    return render_template("admin/inquiry.html", rows=rows)


@bp.post("/inquiry/<int:id>/read")
@login_required
def inquiry_read(id):
    q = db.session.get(Inquiry, id) or abort(404)
    q.read = True; db.session.commit()
    return redirect(url_for("admin.inquiries"))


CONFIG_KEYS = [("site_name", "사이트명"), ("tagline", "슬로건"), ("email", "대표 이메일"), ("phone", "전화"),
               ("address", "주소"), ("youtube", "YouTube URL"), ("instagram", "Instagram URL"),
               ("og_image", "기본 OG 이미지 URL")]


@bp.route("/config", methods=["GET", "POST"])
@login_required
def config():
    if request.method == "POST":
        for k, _ in CONFIG_KEYS:
            row = db.session.get(SiteConfig, k) or SiteConfig(key=k)
            row.value = request.form.get(k, "")
            db.session.add(row)
        db.session.commit(); flash("저장했습니다.")
        return redirect(url_for("admin.config"))
    vals = {k: SiteConfig.get(k) for k, _ in CONFIG_KEYS}
    return render_template("admin/config.html", keys=CONFIG_KEYS, vals=vals)
