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
    artists = db.relationship("Artist", secondary=exhibition_artists, backref="exhibitions")
    media = db.relationship("Media", backref="exhibition", lazy=True)

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


class SiteConfig(db.Model):
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.String(400))

    @staticmethod
    def get(key, default=""):
        row = db.session.get(SiteConfig, key)
        return row.value if row and row.value else default
