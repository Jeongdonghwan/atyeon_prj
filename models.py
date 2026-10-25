from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
STATUS = ("draft", "published")


class Base(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    status = db.Column(db.Enum(*STATUS), default="draft", nullable=False)
    sort = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def live(cls):
        return cls.query.filter_by(status="published").order_by(cls.sort, cls.id.desc())


exhibition_artists = db.Table(
    "exhibition_artists",
    db.Column("exhibition_id", db.ForeignKey("exhibition.id"), primary_key=True),
    db.Column("artist_id", db.ForeignKey("artist.id"), primary_key=True),
)


class Artist(Base):
    name_ko = db.Column(db.String(80), nullable=False)
    name_en = db.Column(db.String(80))
    tagline_ko = db.Column(db.String(160))      # 작업을 설명하는 한 문장
    medium = db.Column(db.String(80))           # 회화 · 설치
    bio_ko = db.Column(db.Text)
    bio_en = db.Column(db.Text)
    note_ko = db.Column(db.Text)                # 작가 노트
    cv_ko = db.Column(db.Text)                  # 줄바꿈 구분
    portrait = db.Column(db.String(400))
    cover = db.Column(db.String(400))
    featured = db.Column(db.Boolean, default=False)
    review_note = db.Column(db.Text)             # 검수 메모 (어드민 전용)
    artworks = db.relationship("Artwork", backref="artist", lazy=True)
    media = db.relationship("Media", backref="artist", lazy=True)

    def __str__(self): return self.name_ko


class Artwork(Base):
    title_ko = db.Column(db.String(160), nullable=False)
    title_en = db.Column(db.String(160))
    artist_id = db.Column(db.ForeignKey("artist.id"))
    year = db.Column(db.String(10))
    medium_ko = db.Column(db.String(120))
    dimensions = db.Column(db.String(80))
    category = db.Column(db.String(40))         # 자연 · 추상 · 회화 · 도시 · 인물 · 공예
    image = db.Column(db.String(400))
    image_2 = db.Column(db.String(400))         # 디테일 · 설치 모습 (최대 3종)
    image_3 = db.Column(db.String(400))
    note_ko = db.Column(db.Text)
    rights = db.Column(db.String(160))
    featured = db.Column(db.Boolean, default=False)
    review_note = db.Column(db.Text)             # 검수 메모 (어드민 전용)

    @property
    def images(self): return [i for i in (self.image, self.image_2, self.image_3) if i]

    def __str__(self): return self.title_ko


class Exhibition(Base):
    title_ko = db.Column(db.String(160), nullable=False)
    title_en = db.Column(db.String(160))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    location = db.Column(db.String(120))
    cover = db.Column(db.String(400))
    body_ko = db.Column(db.Text)
    body_en = db.Column(db.Text)
    # --- 행사(신청 받는 전시) 필드: capacity > 0 이면 행사 페이지·신청이 열림 ---
    subtitle = db.Column(db.String(200))
    hours = db.Column(db.String(80))             # 11:00~18:00
    address = db.Column(db.String(200))
    phone = db.Column(db.String(120))
    subway = db.Column(db.String(300))           # 줄바꿈 구분
    artist_names = db.Column(db.Text)            # 참여 작가 전체 명단(쉼표). 미등록 작가 포함
    program_title = db.Column(db.String(160))
    program_time = db.Column(db.String(80))
    capacity = db.Column(db.Integer, default=0)  # 사전 신청 정원(명)
    fee = db.Column(db.Integer, default=0)       # 1인 참가비(원)
    pay_info = db.Column(db.String(300))         # 입금 계좌 안내
    apply_open = db.Column(db.Boolean, default=False)
    poster = db.Column(db.String(400))
    poster_2 = db.Column(db.String(400))
    artists = db.relationship("Artist", secondary=exhibition_artists, backref="exhibitions")
    media = db.relationship("Media", backref="exhibition", lazy=True)
    registrations = db.relationship("Registration", backref="exhibition", lazy=True)

    @property
    def is_event(self): return (self.capacity or 0) > 0

    @property
    def booked(self):
        return sum(r.people for r in self.registrations if r.status != "cancelled")

    @property
    def remaining(self): return max(0, (self.capacity or 0) - self.booked)

    @property
    def can_apply(self):
        return self.apply_open and self.remaining > 0 and (not self.start_date or self.start_date >= date.today())

    @property
    def names(self): return [n.strip() for n in (self.artist_names or "").split(",") if n.strip()]

    @property
    def phase(self):
        t = date.today()
        if self.end_date and self.end_date < t: return "past"
        if self.start_date and self.start_date > t: return "upcoming"
        return "current"

    def __str__(self): return self.title_ko


class Program(Base):
    title_ko = db.Column(db.String(160), nullable=False)
    title_en = db.Column(db.String(160))
    category = db.Column(db.Enum("mirini", "talk", "lecture", "course"), default="course")
    audience = db.Column(db.String(120))
    summary_ko = db.Column(db.Text)
    schedule = db.Column(db.String(160))
    cover = db.Column(db.String(400))
    inquiry_link = db.Column(db.String(400))

    def __str__(self): return self.title_ko


class Journal(Base):
    title_ko = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200))
    category = db.Column(db.Enum("interview", "behind", "global", "review", "news"), default="news")
    date = db.Column(db.Date, default=date.today)
    cover = db.Column(db.String(400))
    summary_ko = db.Column(db.Text)
    body_ko = db.Column(db.Text)
    artist_id = db.Column(db.ForeignKey("artist.id"))
    artist = db.relationship("Artist")

    def __str__(self): return self.title_ko


class Media(Base):
    platform = db.Column(db.Enum("youtube", "instagram"), default="youtube")
    series = db.Column(db.String(80))           # IN THE STUDIO 등
    title_ko = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(400))
    video_id = db.Column(db.String(40))         # youtube id
    thumb = db.Column(db.String(400))
    date = db.Column(db.Date, default=date.today)
    artist_id = db.Column(db.ForeignKey("artist.id"))
    exhibition_id = db.Column(db.ForeignKey("exhibition.id"))

    def __str__(self): return self.title_ko


class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.Enum("global", "artist", "academy", "general"), default="general")
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    organization = db.Column(db.String(160))
    country = db.Column(db.String(80))
    message = db.Column(db.Text, nullable=False)
    consent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    def __str__(self): return f"{self.name} ({self.kind})"


class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exhibition_id = db.Column(db.ForeignKey("exhibition.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(160))
    people = db.Column(db.Integer, default=1)
    message = db.Column(db.String(300))          # 미리 남기는 감상 한 문장
    consent = db.Column(db.Boolean, default=False)
    status = db.Column(db.Enum("received", "confirmed", "cancelled"), default="received")  # 입금대기/확정/취소
    memo = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.now)  # 서버 현지시각(KST)

    STATUS_KO = {"received": "입금 대기", "confirmed": "참가 확정", "cancelled": "취소"}

    @property
    def code(self): return f"AY{self.created_at:%y}-{self.id:04d}"

    @property
    def status_ko(self): return self.STATUS_KO[self.status]

    @property
    def amount(self): return (self.exhibition.fee or 0) * self.people


class SiteConfig(db.Model):
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.String(400))

    @staticmethod
    def get(key, default=""):
        row = db.session.get(SiteConfig, key)
        return row.value if row and row.value else default
