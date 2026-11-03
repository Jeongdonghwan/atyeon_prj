"""/flow 업무 공유: 사용자·프로젝트·업무·일정·댓글·활동·알림. 기존 사이트 테이블은 건드리지 않고 flow_ 접두 테이블만 추가."""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db

ROLES = {"admin": "총관리자", "member": "팀원"}
STATUS = {"todo": "할 일", "doing": "진행 중", "review": "확인 요청", "done": "완료"}
PRIORITY = {"high": "높음", "normal": "보통", "low": "낮음"}

task_assignee = db.Table(
    "flow_task_assignee",
    db.Column("task_id", db.ForeignKey("flow_task.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.ForeignKey("flow_user.id", ondelete="CASCADE"), primary_key=True),
)
event_attendee = db.Table(
    "flow_event_attendee",
    db.Column("event_id", db.ForeignKey("flow_event.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.ForeignKey("flow_user.id", ondelete="CASCADE"), primary_key=True),
)


class FlowUser(db.Model):
    __tablename__ = "flow_user"
    id = db.Column(db.Integer, primary_key=True)
    login_id = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(40), nullable=False)
    phone = db.Column(db.String(30))
    role = db.Column(db.String(10), default="member")
    color = db.Column(db.String(9), default="#12305A")
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)
    must_change_pw = db.Column(db.Boolean, default=True)
    fail_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_pw(self, pw): self.password_hash = generate_password_hash(pw)
    def check_pw(self, pw): return check_password_hash(self.password_hash, pw)
    @property
    def is_admin(self): return self.role == "admin"
    @property
    def role_ko(self): return ROLES.get(self.role, self.role)


class Project(db.Model):
    __tablename__ = "flow_project"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(20), default="event")      # event / exhibition / sales / etc
    start = db.Column(db.Date)
    end = db.Column(db.Date)
    exhibition_id = db.Column(db.ForeignKey("exhibition.id"))
    color = db.Column(db.String(9), default="#B8935A")
    archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    tasks = db.relationship("Task", backref="project", lazy=True)

    @property
    def progress(self):
        ts = self.tasks
        return round(100 * sum(t.status == "done" for t in ts) / len(ts)) if ts else 0


class Task(db.Model):
    __tablename__ = "flow_task"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.ForeignKey("flow_project.id"))
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    status = db.Column(db.String(10), default="todo")
    priority = db.Column(db.String(10), default="normal")
    start = db.Column(db.Date)               # 타임라인 시작일 (없으면 마감일 기준)
    due = db.Column(db.Date)
    requester_id = db.Column(db.ForeignKey("flow_user.id"))
    link_type = db.Column(db.String(20))     # registration / inquiry / exhibition / artwork / artist
    link_id = db.Column(db.Integer)
    checklist = db.Column(db.Text)           # 줄마다 "[x] 내용" / "[ ] 내용"
    sort = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    done_at = db.Column(db.DateTime)
    assignees = db.relationship("FlowUser", secondary=task_assignee, lazy="subquery")
    requester = db.relationship("FlowUser", foreign_keys=[requester_id])
    comments = db.relationship("Comment", backref="task", lazy=True, cascade="all, delete-orphan", order_by="Comment.id")

    @property
    def overdue(self):
        return self.due and self.status != "done" and self.due < datetime.now().date()

    @property
    def span(self):
        """타임라인용 (시작, 끝)"""
        if not self.due and not self.start: return None
        s = self.start or self.due; e = self.due or self.start
        return (min(s, e), max(s, e))

    @property
    def check_pct(self):
        c = self.checks
        return round(100 * sum(d for d, _ in c) / len(c)) if c else None

    @property
    def checks(self):
        out = []
        for line in (self.checklist or "").splitlines():
            line = line.strip()
            if not line: continue
            done = line.startswith("[x]")
            out.append((done, line[3:].strip() if line[:3] in ("[x]", "[ ]") else line))
        return out


class FlowEvent(db.Model):
    __tablename__ = "flow_event"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.ForeignKey("flow_project.id"))
    title = db.Column(db.String(200), nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime)
    all_day = db.Column(db.Boolean, default=False)
    place = db.Column(db.String(200))
    memo = db.Column(db.Text)
    created_by = db.Column(db.ForeignKey("flow_user.id"))
    created_at = db.Column(db.DateTime, default=datetime.now)
    attendees = db.relationship("FlowUser", secondary=event_attendee, lazy="subquery")
    project = db.relationship("Project")


class Comment(db.Model):
    __tablename__ = "flow_comment"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.ForeignKey("flow_task.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.ForeignKey("flow_user.id"))
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship("FlowUser")


class Activity(db.Model):
    __tablename__ = "flow_activity"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("flow_user.id"))
    text = db.Column(db.String(300), nullable=False)
    task_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship("FlowUser")


class Notice(db.Model):
    __tablename__ = "flow_notice"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("flow_user.id"), nullable=False)
    text = db.Column(db.String(300), nullable=False)
    task_id = db.Column(db.Integer)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


# 행사 템플릿: (D-day 기준 일수, 업무명, 우선순위)
EVENT_TEMPLATE = [
    (-30, "참여 작가·출품작 확정", "high"),
    (-28, "작품 정보(작품명·재료·규격·연도) 수집", "normal"),
    (-21, "포스터·홍보 이미지 확정", "high"),
    (-18, "홈페이지 행사 페이지·신청 오픈", "high"),
    (-14, "SNS·문자 홍보 1차", "normal"),
    (-10, "선물·액자·소품 발주", "normal"),
    (-7, "입금 확인 마감·참가 확정 안내", "high"),
    (-5, "SNS·문자 홍보 2차 (리마인드)", "normal"),
    (-3, "작품 설치·현장 동선 점검", "high"),
    (-2, "참가자 명단 출력·체크인 준비", "normal"),
    (0, "현장 운영", "high"),
    (3, "정산·사진 정리·후기 게시", "normal"),
]
