"""/flow 초기 세팅 (여러 번 실행해도 안전: 없는 것만 만든다. 기존 사이트 데이터·신청 데이터는 건드리지 않음).
  python flow_init.py
- flow_ 테이블 생성 (기존 테이블은 변경 없음)
- 계정 5개 생성(관리자 + 팀원 4명), 임시 비밀번호 출력 (첫 로그인 때 변경 강제)
- 'Christmas with ARTEYEON 2026' 프로젝트 + 행사 템플릿 업무 12개 + 행사 당일 일정
"""
import secrets
from datetime import date, datetime
from app import app
from models import db, Exhibition
from flow_models import FlowUser, Project, FlowEvent, Activity
import flow

USERS = [  # (아이디, 이름, 역할, 색)
    ("admin", "관리자", "admin", "#0A1630"),  # 운영용. 업무 담당·분담 화면에는 안 나옴
    ("donghwan", "정동환", "member", "#12305A"),
    ("seongja", "강성자", "member", "#B8935A"),
    ("gucheol", "정구철", "member", "#2F7D6D"),
    ("sejun", "김세준", "member", "#9B4F6A"),
]

with app.app_context():
    db.create_all()
    # 예전 세팅(정동환=총관리자) → 정동환은 팀원으로. 관리자 계정은 아래에서 새로 생성
    old = FlowUser.query.filter_by(login_id="donghwan", role="admin").first()
    if old and not FlowUser.query.filter_by(login_id="admin").first():
        old.role = "member"; print("정동환: 총관리자 → 팀원")
    created = []
    for lid, name, role, color in USERS:
        if FlowUser.query.filter_by(login_id=lid).first(): continue
        pw = secrets.token_urlsafe(6)
        u = FlowUser(login_id=lid, name=name, role=role, color=color); u.set_pw(pw)
        db.session.add(u); created.append((name, lid, pw, role))
    db.session.commit()
    owner = FlowUser.query.filter_by(login_id="admin").first()

    ex = Exhibition.query.filter_by(slug="christmas-2026").first()
    if ex and not Project.query.filter_by(exhibition_id=ex.id).first():
        p = Project(name="Christmas with ARTEYEON 2026", kind="event", start=ex.start_date, end=ex.end_date,
                    exhibition_id=ex.id, color="#B8935A")
        db.session.add(p); db.session.flush()
        flow.apply_template(p, owner=owner)
        d = ex.start_date
        ev1 = FlowEvent(project_id=p.id, title="행사 당일 · 전시 자유 관람", start=datetime(d.year, d.month, d.day, 11), end=datetime(d.year, d.month, d.day, 18),
                        place=f"{ex.location} {ex.address or ''}", created_by=owner.id)
        ev2 = FlowEvent(project_id=p.id, title=ex.program_title or "특별 프로그램", start=datetime(d.year, d.month, d.day, 15), end=datetime(d.year, d.month, d.day, 16),
                        place=ex.location, created_by=owner.id)
        ev1.attendees = ev2.attendees = flow.users()
        db.session.add_all([ev1, ev2])
        db.session.add(Activity(user_id=owner.id, text="프로젝트 생성: Christmas with ARTEYEON 2026 (템플릿 업무 12개, 일정 2건)"))
        db.session.commit()
        print("project: Christmas with ARTEYEON 2026 + 12 tasks + 2 events")

    # 시작일 칸이 생기기 전에 만든 프로젝트 업무 → 시작일 채우기(마감 2~4일 전, 타임라인용)
    from datetime import timedelta
    from flow_models import Task
    fill = Task.query.filter(Task.start.is_(None), Task.due.isnot(None), Task.project_id.isnot(None)).all()
    for t in fill: t.start = t.due - timedelta(days=4 if t.priority == "high" else 2)
    if fill: db.session.commit(); print(f"시작일 채움: 업무 {len(fill)}개")

    if created:
        print("\n=== 계정 (임시 비밀번호는 지금 한 번만 표시됩니다) ===")
        for name, lid, pw, role in created:
            print(f"{name:<4} 아이디 {lid:<9} 임시비번 {pw}  ({'총관리자' if role == 'admin' else '팀원'})")
    else:
        print("users already exist")
