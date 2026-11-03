"""/flow 업무 공유 공간: 로그인(개인 계정) · 대시보드 · 업무 보드 · 업무 상세 · 캘린더 · 프로젝트 · 사용자 관리 · 사이트 내 알림."""
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, g, jsonify
from models import db, Exhibition, Registration, Inquiry
from flow_models import (FlowUser, Project, Task, FlowEvent, Comment, Activity, Notice,
                         ROLES, STATUS, PRIORITY, EVENT_TEMPLATE)

bp = Blueprint("flow", __name__, url_prefix="/flow")
COLORS = ["#12305A", "#B8935A", "#2F7D6D", "#9B4F6A", "#4C6FB5", "#C2662D"]


# ---------- 인증 ----------
@bp.before_request
def load_user():
    uid = session.get("flow_uid")
    g.fu = db.session.get(FlowUser, uid) if uid else None
    if g.fu and not g.fu.active: session.pop("flow_uid", None); g.fu = None
    if request.endpoint in ("flow.login", "static"): return
    if not g.fu: return redirect(url_for("flow.login", next=request.full_path))
    if g.fu.must_change_pw and request.endpoint not in ("flow.me", "flow.logout"):
        flash("처음 로그인하셨습니다. 비밀번호를 바꿔주세요."); return redirect(url_for("flow.me"))


def admin_only(f):
    @wraps(f)
    def w(*a, **k):
        if not g.fu.is_admin: abort(403)
        return f(*a, **k)
    return w


@bp.context_processor
def ctx():
    unread = Notice.query.filter_by(user_id=g.fu.id, read=False).count() if getattr(g, "fu", None) else 0
    side_projects = lambda: Project.query.filter_by(archived=False).order_by(Project.start).limit(6).all()
    return dict(me=getattr(g, "fu", None), unread=unread, STATUS=STATUS, PRIORITY=PRIORITY, ROLES=ROLES, today=date.today(), side_projects=side_projects)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = FlowUser.query.filter_by(login_id=request.form.get("id", "").strip()).first()
        now = datetime.now()
        if u and u.locked_until and u.locked_until > now:
            flash(f"로그인 시도가 많아 잠겼습니다. {u.locked_until:%H:%M} 이후 다시 시도하세요.")
        elif u and u.active and u.check_pw(request.form.get("pw", "")):
            u.fail_count = 0; u.locked_until = None; u.last_login = now; db.session.commit()
            session.clear(); session["flow_uid"] = u.id; session.permanent = True
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/flow") else url_for("flow.dashboard"))
        else:
            if u:
                u.fail_count = (u.fail_count or 0) + 1
                if u.fail_count >= 5: u.locked_until = now + timedelta(minutes=10); u.fail_count = 0
                db.session.commit()
            flash("아이디 또는 비밀번호가 다릅니다.")
    return render_template("flow/login.html")


@bp.route("/logout")
def logout():
    session.pop("flow_uid", None)
    return redirect(url_for("flow.login"))


@bp.route("/me", methods=["GET", "POST"])
def me():
    if request.method == "POST":
        cur, new, new2 = request.form.get("cur", ""), request.form.get("new", ""), request.form.get("new2", "")
        if not g.fu.check_pw(cur): flash("현재 비밀번호가 다릅니다.")
        elif len(new) < 4: flash("새 비밀번호는 4자 이상으로 해주세요.")
        elif new != new2: flash("새 비밀번호 확인이 일치하지 않습니다.")
        else:
            g.fu.set_pw(new); g.fu.must_change_pw = False
            g.fu.phone = request.form.get("phone") or g.fu.phone
            db.session.commit(); flash("비밀번호를 바꿨습니다."); return redirect(url_for("flow.dashboard"))
    return render_template("flow/me.html")


# ---------- 기록·알림 ----------
def log(text, task=None, notify=()):
    db.session.add(Activity(user_id=g.fu.id if getattr(g, "fu", None) else None, text=text, task_id=task.id if task else None))
    for u in {u for u in notify if u and (not getattr(g, "fu", None) or u.id != g.fu.id)}:
        db.session.add(Notice(user_id=u.id, text=text, task_id=task.id if task else None))


def system_task(title, body, link_type, link_id, due=None, project=None):
    """사이트 이벤트(행사 신청·문의) → 담당자 없는 업무 자동 생성 + 관리자 알림(업무 분담에서 배정). 사이트 쪽 commit 이후 호출."""
    admins = FlowUser.query.filter_by(role="admin", active=True).all()
    if not admins: return
    t = Task(title=title, body=body, link_type=link_type, link_id=link_id, due=due or date.today() + timedelta(days=1),
             priority="high", project=project)
    db.session.add(t); db.session.flush()
    for a in admins:
        db.session.add(Notice(user_id=a.id, text=f"[자동] {title}", task_id=t.id))
    db.session.add(Activity(text=f"[자동] 업무 생성: {title}", task_id=t.id))
    db.session.commit()


def on_registration(r):
    p = Project.query.filter_by(exhibition_id=r.exhibition_id).first()
    system_task(f"입금 확인: {r.name} {r.people}명 ({r.code})",
                f"{r.exhibition.title_ko}\n연락처 {r.phone}\n금액 {r.amount:,}원\n입금 확인 후 사이트 어드민 > 행사 신청에서 '참가 확정'으로 변경",
                "registration", r.id, project=p)


def on_inquiry(q):
    system_task(f"문의 회신: {q.name} ({q.kind})", f"{q.email}\n\n{q.message}", "inquiry", q.id)


# ---------- 대시보드 ----------
@bp.route("/")
def dashboard():
    mine = Task.query.filter(Task.assignees.any(id=g.fu.id), Task.status != "done").order_by(Task.due.is_(None), Task.due).all()
    week = date.today() + timedelta(days=7)
    t0 = datetime.combine(date.today(), datetime.min.time())
    events = FlowEvent.query.filter(db.or_(FlowEvent.start >= t0, FlowEvent.end > t0),
                                    FlowEvent.start < datetime.combine(week, datetime.min.time())).order_by(FlowEvent.start).all()
    overdue = Task.query.filter(Task.status != "done", Task.due < date.today()).order_by(Task.due).all()
    review = Task.query.filter(Task.status == "review", Task.requester_id == g.fu.id).all()
    acts = Activity.query.order_by(Activity.id.desc()).limit(15).all()
    notices = Notice.query.filter_by(user_id=g.fu.id).order_by(Notice.id.desc()).limit(10).all()
    projects = Project.query.filter_by(archived=False).order_by(Project.start).all()
    open_all = Task.query.filter(Task.status != "done").all()
    load = []
    for u in users():
        ts = [t for t in open_all if u in t.assignees]
        load.append((u, {k: sum(t.status == k for t in ts) for k in ("todo", "doing", "review")}, sum(bool(t.overdue) for t in ts), len(ts)))
    mx = max([n for *_, n in load] + [1])
    stats = {"mine": len(mine), "today": sum(t.due == date.today() for t in mine), "overdue": len(overdue), "review": len(review)}
    return render_template("flow/dashboard.html", mine=mine, events=events, overdue=overdue, review=review,
                           acts=acts, notices=notices, projects=projects, load=load, mx=mx, stats=stats,
                           unassigned=sum(not t.assignees for t in open_all))


@bp.post("/notices/read")
def notices_read():
    Notice.query.filter_by(user_id=g.fu.id, read=False).update({"read": True}); db.session.commit()
    return redirect(request.referrer or url_for("flow.dashboard"))


# ---------- 업무 ----------
def users():  # 업무에 쓰는 사람(담당·참석·분담). 관리자 계정은 운영용이라 빠진다
    return FlowUser.query.filter(FlowUser.active.is_(True), FlowUser.role != "admin").order_by(FlowUser.id).all()


@bp.route("/tasks")
def tasks():
    q = Task.query
    pid, uid = request.args.get("p", type=int), request.args.get("u", type=int)
    if pid: q = q.filter_by(project_id=pid)
    if uid: q = q.filter(Task.assignees.any(id=uid))
    rows = q.order_by(Task.sort, Task.due.is_(None), Task.due, Task.id).all()
    cols = {k: [t for t in rows if t.status == k] for k in STATUS}
    return render_template("flow/board.html", cols=cols, projects=Project.query.filter_by(archived=False).all(),
                           users=users(), pid=pid, uid=uid)


def _apply_task(t):
    f = request.form
    t.title = f.get("title", "").strip() or t.title
    t.body = f.get("body") or None
    t.project_id = f.get("project_id", type=int) or None
    t.priority = f.get("priority") if f.get("priority") in PRIORITY else "normal"
    t.due = date.fromisoformat(f["due"]) if f.get("due") else None
    t.start = date.fromisoformat(f["start"]) if f.get("start") else None
    if f.get("status") in STATUS: t.status = f["status"]
    t.checklist = f.get("checklist") or None
    ids = [int(x) for x in f.getlist("assignees") if x.isdigit()]
    before = {u.id for u in t.assignees}
    t.assignees = FlowUser.query.filter(FlowUser.id.in_(ids)).all() if ids else []
    return [u for u in t.assignees if u.id not in before]


@bp.route("/tasks/new", methods=["GET", "POST"])
def task_new():
    if request.method == "POST":
        t = Task(requester_id=g.fu.id, title="(제목 없음)")
        added = _apply_task(t)
        db.session.add(t); db.session.flush()
        log(f"{g.fu.name}님이 업무를 만들었습니다: {t.title}" + (f" → 담당 {', '.join(u.name for u in t.assignees)}" if t.assignees else ""), t, notify=added)
        db.session.commit(); flash("업무를 만들었습니다.")
        return redirect(url_for("flow.task", id=t.id))
    t = Task(project_id=request.args.get("p", type=int), status=request.args.get("s", "todo"),
             due=date.fromisoformat(request.args["due"]) if request.args.get("due") else None)
    return render_template("flow/task_form.html", t=t, users=users(), projects=Project.query.filter_by(archived=False).all())


@bp.route("/tasks/<int:id>", methods=["GET", "POST"])
def task(id):
    t = db.session.get(Task, id) or abort(404)
    if request.method == "POST":
        old = t.status
        added = _apply_task(t)
        msg = f"{g.fu.name}님이 업무를 수정했습니다: {t.title}"
        if old != t.status: msg = f"{g.fu.name}님이 '{t.title}' 상태를 {STATUS[old]} → {STATUS[t.status]}(으)로 바꿨습니다"
        if t.status == "done" and old != "done": t.done_at = datetime.now()
        log(msg, t, notify=list(t.assignees) + [t.requester])
        if added: log(f"{g.fu.name}님이 '{t.title}' 담당으로 {', '.join(u.name for u in added)}님을 지정했습니다", t, notify=added)
        db.session.commit(); flash("저장했습니다.")
        return redirect(url_for("flow.task", id=t.id))
    acts = Activity.query.filter_by(task_id=t.id).order_by(Activity.id.desc()).limit(30).all()
    link = None
    if t.link_type == "registration": link = db.session.get(Registration, t.link_id)
    elif t.link_type == "inquiry": link = db.session.get(Inquiry, t.link_id)
    Notice.query.filter_by(user_id=g.fu.id, task_id=t.id, read=False).update({"read": True}); db.session.commit()
    return render_template("flow/task.html", t=t, acts=acts, link=link, users=users(), projects=Project.query.all())


@bp.post("/tasks/<int:id>/status")
def task_status(id):
    t = db.session.get(Task, id) or abort(404)
    s = request.form.get("status") or (request.json or {}).get("status")
    if s not in STATUS: abort(400)
    if s != t.status:
        old = t.status; t.status = s
        t.done_at = datetime.now() if s == "done" else None
        notify = [t.requester] if s == "review" else list(t.assignees) + [t.requester]
        log(f"{g.fu.name}님이 '{t.title}' 상태를 {STATUS[old]} → {STATUS[s]}(으)로 바꿨습니다", t, notify=notify)
        db.session.commit()
    if request.is_json: return jsonify(ok=True)
    return redirect(request.referrer or url_for("flow.tasks"))


@bp.post("/tasks/<int:id>/check/<int:i>")
def task_check(id, i):
    t = db.session.get(Task, id) or abort(404)
    lines = [l for l in (t.checklist or "").splitlines() if l.strip()]
    if 0 <= i < len(lines):
        l = lines[i].strip()
        lines[i] = ("[ ] " + l[3:].strip()) if l.startswith("[x]") else ("[x] " + (l[3:].strip() if l.startswith("[ ]") else l))
        t.checklist = "\n".join(lines); db.session.commit()
    return redirect(url_for("flow.task", id=id))


@bp.post("/tasks/<int:id>/comment")
def task_comment(id):
    t = db.session.get(Task, id) or abort(404)
    body = request.form.get("body", "").strip()
    if body:
        db.session.add(Comment(task_id=t.id, user_id=g.fu.id, body=body))
        log(f"{g.fu.name}님이 '{t.title}'에 댓글: {body[:60]}", t, notify=list(t.assignees) + [t.requester])
        db.session.commit()
    return redirect(url_for("flow.task", id=id) + "#comments")


@bp.post("/tasks/<int:id>/delete")
def task_delete(id):
    t = db.session.get(Task, id) or abort(404)
    if not (g.fu.is_admin or t.requester_id == g.fu.id): abort(403)
    log(f"{g.fu.name}님이 업무를 삭제했습니다: {t.title}")
    db.session.delete(t); db.session.commit(); flash("삭제했습니다.")
    return redirect(url_for("flow.tasks"))


# ---------- 팀 업무 분담 ----------
@bp.route("/team")
def team():
    us = users()
    open_ = Task.query.filter(Task.status != "done").order_by(Task.due.is_(None), Task.due).all()
    pid = request.args.get("p", type=int)
    if pid: open_ = [t for t in open_ if t.project_id == pid]
    cols = [(u, [t for t in open_ if u in t.assignees]) for u in us]
    none = [t for t in open_ if not t.assignees]
    return render_template("flow/team.html", cols=cols, unassigned=none, projects=Project.query.filter_by(archived=False).all(), pid=pid)


@bp.post("/team/move")
def team_move():
    d = request.get_json(force=True)
    t = db.session.get(Task, int(d["task"])) or abort(404)
    to = db.session.get(FlowUser, int(d["to"])) if d.get("to") else None
    frm = int(d["from"]) if d.get("from") else None
    names = [u for u in t.assignees if u.id != frm]
    if to and to not in names: names.append(to)
    t.assignees = names
    log(f"{g.fu.name}님이 '{t.title}' 담당을 {(to.name if to else '미지정')}(으)로 옮겼습니다", t, notify=[to] if to else [])
    db.session.commit()
    return jsonify(ok=True)


# ---------- 캘린더 ----------
@bp.route("/calendar")
def calendar():
    return render_template("flow/calendar.html", users=users(), projects=Project.query.filter_by(archived=False).all())


@bp.route("/calendar/feed")
def calendar_feed():
    uid = request.args.get("u", type=int)
    out = []
    for e in FlowEvent.query.all():
        if uid and uid not in [a.id for a in e.attendees] and e.created_by != uid: continue
        c = e.project.color if e.project else "#12305A"
        out.append({"id": f"e{e.id}", "title": e.title, "start": e.start.isoformat(), "end": e.end.isoformat() if e.end else None,
                    "allDay": e.all_day, "color": c, "url": url_for("flow.event", id=e.id)})
    q = Task.query.filter(Task.due.isnot(None))
    if uid: q = q.filter(Task.assignees.any(id=uid))
    for t in q:
        c = t.assignees[0].color if t.assignees else "#888"
        out.append({"id": f"t{t.id}", "title": ("✓ " if t.status == "done" else "마감 · ") + t.title, "start": t.due.isoformat(),
                    "allDay": True, "color": "#bbb" if t.status == "done" else c, "url": url_for("flow.task", id=t.id),
                    "classNames": ["is-task"] + (["is-done"] if t.status == "done" else [])})
    for p in Project.query.filter(Project.start.isnot(None)):
        out.append({"id": f"p{p.id}", "title": "★ " + p.name, "start": p.start.isoformat(),
                    "end": ((p.end or p.start) + timedelta(days=1)).isoformat(), "allDay": True, "color": p.color,
                    "url": url_for("flow.project", id=p.id), "display": "block"})
    return jsonify(out)


def _when(e, f):
    """f: 폼 또는 쿼리. date~date2 기간, 종일이면 end=마지막날+1(캘린더 규칙)."""
    e.all_day = bool(f.get("all_day"))
    d = date.fromisoformat(f.get("date") or date.today().isoformat())
    d2 = max(d, date.fromisoformat(f.get("date2"))) if f.get("date2") else d
    if e.all_day:
        e.start = datetime.combine(d, datetime.min.time()); e.end = datetime.combine(d2 + timedelta(days=1), datetime.min.time())
    else:
        e.start = datetime.fromisoformat(f"{d}T{f.get('t0') or '10:00'}")
        e.end = max(e.start, datetime.fromisoformat(f"{d2}T{f.get('t1') or f.get('t0') or '11:00'}"))


def _apply_event(e):
    f = request.form
    e.title = f.get("title", "").strip() or "(일정)"
    _when(e, f)
    e.place = f.get("place") or None; e.memo = f.get("memo") or None
    e.project_id = f.get("project_id", type=int) or None
    ids = [int(x) for x in f.getlist("attendees") if x.isdigit()]
    before = {u.id for u in e.attendees}
    e.attendees = FlowUser.query.filter(FlowUser.id.in_(ids)).all() if ids else []
    return [u for u in e.attendees if u.id not in before]


@bp.route("/events/new", methods=["GET", "POST"])
@bp.route("/events/<int:id>", methods=["GET", "POST"])
def event(id=None):
    e = db.session.get(FlowEvent, id) if id else FlowEvent(created_by=g.fu.id)
    if id and not e: abort(404)
    if request.method == "POST":
        if request.form.get("delete") and e.id:
            log(f"{g.fu.name}님이 일정을 삭제했습니다: {e.title}"); db.session.delete(e); db.session.commit()
            return redirect(url_for("flow.calendar"))
        added = _apply_event(e); db.session.add(e); db.session.flush()
        log(f"{g.fu.name}님이 일정을 {'수정' if id else '등록'}했습니다: {e.start:%m/%d}{e.last_day != e.start.date() and f'~{e.last_day:%m/%d}' or ''} {e.title}", notify=added)
        db.session.commit(); flash("저장했습니다.")
        return redirect(url_for("flow.calendar"))
    if not id and request.args.get("date"):
        _when(e, request.args)
    return render_template("flow/event.html", e=e, users=users(), projects=Project.query.filter_by(archived=False).all())


# ---------- 프로젝트 ----------
@bp.route("/projects", methods=["GET", "POST"])
def projects():
    if request.method == "POST":
        f = request.form
        p = Project(name=f["name"].strip(), kind=f.get("kind", "event"),
                    start=date.fromisoformat(f["start"]) if f.get("start") else None,
                    end=date.fromisoformat(f["end"]) if f.get("end") else None,
                    exhibition_id=f.get("exhibition_id", type=int) or None,
                    color=f.get("color") or "#B8935A")
        db.session.add(p); db.session.flush()
        n = apply_template(p, owner=g.fu) if f.get("template") and p.start else 0
        log(f"{g.fu.name}님이 프로젝트를 만들었습니다: {p.name}" + (f" (템플릿 업무 {n}개)" if n else ""))
        db.session.commit(); flash("프로젝트를 만들었습니다.")
        return redirect(url_for("flow.project", id=p.id))
    rows = Project.query.order_by(Project.archived, Project.start.desc()).all()
    return render_template("flow/projects.html", rows=rows, exhibitions=Exhibition.query.order_by(Exhibition.start_date.desc()).all())


def apply_template(p, owner=None):
    d0 = p.end or p.start
    for off, title, pr in EVENT_TEMPLATE:
        due = d0 + timedelta(days=off)
        t = Task(project=p, title=title, priority=pr, due=due, start=due - timedelta(days=0 if off >= 0 else (4 if pr == "high" else 2)), requester=owner)
        if owner and not owner.is_admin: t.assignees = [owner]
        db.session.add(t)
    return len(EVENT_TEMPLATE)


@bp.route("/projects/<int:id>", methods=["GET", "POST"])
def project(id):
    p = db.session.get(Project, id) or abort(404)
    if request.method == "POST":
        if request.form.get("archive"): p.archived = not p.archived
        db.session.commit(); return redirect(url_for("flow.project", id=id))
    ex = db.session.get(Exhibition, p.exhibition_id) if p.exhibition_id else None
    cols = {k: [t for t in sorted(p.tasks, key=lambda t: (t.due or date.max, t.id)) if t.status == k] for k in STATUS}
    evs = FlowEvent.query.filter_by(project_id=p.id).order_by(FlowEvent.start).all()
    view = request.args.get("view", "timeline")
    gantt = None
    spans = [t.span for t in p.tasks if t.span]
    if spans:
        g0 = min(s for s, _ in spans + ([(p.start, p.start)] if p.start else [])) - timedelta(days=2)
        g1 = max(e for _, e in spans + ([(p.end or p.start, p.end or p.start)] if p.start else [])) + timedelta(days=2)
        days = [g0 + timedelta(days=i) for i in range((g1 - g0).days + 1)]
        rows = sorted([t for t in p.tasks if t.span], key=lambda t: (t.span[0], t.span[1], t.id))
        gantt = {"days": days, "rows": rows, "g0": g0}
    return render_template("flow/project.html", p=p, ex=ex, cols=cols, evs=evs, view=view, gantt=gantt)


# ---------- 사용자 관리 (총관리자) ----------
@bp.route("/users", methods=["GET", "POST"])
@admin_only
def users_admin():
    import secrets
    temp = None
    if request.method == "POST":
        f = request.form
        if f.get("action") == "add":
            if FlowUser.query.filter_by(login_id=f["login_id"].strip()).first():
                flash("이미 있는 아이디입니다.")
            else:
                temp = f.get("pw", "").strip() or secrets.token_urlsafe(6)
                if len(temp) < 4 and f.get("pw"): flash("비밀번호는 4자 이상으로 해주세요."); return redirect(url_for("flow.users_admin"))
                u = FlowUser(login_id=f["login_id"].strip(), name=f["name"].strip(), phone=f.get("phone"),
                             role=f.get("role") if f.get("role") in ROLES else "member",
                             color=COLORS[FlowUser.query.count() % len(COLORS)])
                u.set_pw(temp); db.session.add(u)
                log(f"{g.fu.name}님이 사용자를 추가했습니다: {u.name}")
                db.session.commit(); flash(f"{u.name}님 계정을 만들었습니다. 아이디 {u.login_id} · 비밀번호: {temp}")
        else:
            u = db.session.get(FlowUser, f.get("uid", type=int)) or abort(404)
            if f.get("action") == "reset":
                temp = secrets.token_urlsafe(6); u.set_pw(temp); u.must_change_pw = True; u.locked_until = None
                flash(f"{u.name}님 임시 비밀번호: {temp}")
            elif f.get("action") == "toggle" and u.id != g.fu.id:
                u.active = not u.active; flash(f"{u.name}님을 {'활성' if u.active else '비활성'}화했습니다.")
            elif f.get("action") == "role" and u.id != g.fu.id and f.get("role") in ROLES:
                u.role = f["role"]; flash(f"{u.name}님 역할: {ROLES[u.role]}")
            elif f.get("action") == "color":
                u.color = f.get("color") or u.color
            db.session.commit()
        return redirect(url_for("flow.users_admin"))
    return render_template("flow/users.html", rows=FlowUser.query.order_by(FlowUser.id).all())


@bp.route("/users/<int:id>", methods=["GET", "POST"])
@admin_only
def user_edit(id):
    """총관리자: 계정 정보 수정 · 비밀번호 직접 지정 · 삭제"""
    u = db.session.get(FlowUser, id) or abort(404)
    if request.method == "POST":
        f = request.form
        act = f.get("action")
        if act == "save":
            lid = f.get("login_id", "").strip()
            if not lid or not lid.replace("_", "").replace(".", "").replace("-", "").isalnum():
                flash("아이디는 영문·숫자로 입력하세요.")
            elif FlowUser.query.filter(FlowUser.login_id == lid, FlowUser.id != u.id).first():
                flash("이미 있는 아이디입니다.")
            else:
                u.login_id = lid; u.name = f.get("name", "").strip() or u.name
                u.phone = f.get("phone") or None; u.color = f.get("color") or u.color
                if u.id != g.fu.id and f.get("role") in ROLES: u.role = f["role"]
                if u.id != g.fu.id: u.active = "active" in f
                log(f"{g.fu.name}님이 {u.name}님 계정 정보를 수정했습니다")
                db.session.commit(); flash("저장했습니다.")
        elif act == "password":
            pw = f.get("pw", "")
            if len(pw) < 4: flash("비밀번호는 4자 이상으로 해주세요.")
            else:
                u.set_pw(pw); u.must_change_pw = "force_change" in f; u.fail_count = 0; u.locked_until = None
                log(f"{g.fu.name}님이 {u.name}님 비밀번호를 지정했습니다")
                db.session.commit(); flash(f"{u.name}님 비밀번호를 바꿨습니다." + (" 첫 로그인 때 본인이 다시 바꾸게 됩니다." if u.must_change_pw else ""))
        elif act == "unlock":
            u.fail_count = 0; u.locked_until = None; db.session.commit(); flash("잠금을 풀었습니다.")
        elif act == "delete":
            if u.id == g.fu.id: flash("본인 계정은 삭제할 수 없습니다.")
            elif u.is_admin and FlowUser.query.filter_by(role="admin", active=True).count() <= 1: flash("마지막 총관리자는 삭제할 수 없습니다.")
            else:
                name = u.name
                # 기록은 남기고 연결만 끊는다: 담당 해제, 요청자·작성자 비움, 알림 삭제
                for t in Task.query.filter(Task.assignees.any(id=u.id)).all(): t.assignees = [x for x in t.assignees if x.id != u.id]
                for e in FlowEvent.query.filter(FlowEvent.attendees.any(id=u.id)).all(): e.attendees = [x for x in e.attendees if x.id != u.id]
                Task.query.filter_by(requester_id=u.id).update({"requester_id": None})
                FlowEvent.query.filter_by(created_by=u.id).update({"created_by": None})
                Comment.query.filter_by(user_id=u.id).update({"user_id": None})
                Activity.query.filter_by(user_id=u.id).update({"user_id": None})
                Notice.query.filter_by(user_id=u.id).delete()
                db.session.delete(u)
                log(f"{g.fu.name}님이 {name}님 계정을 삭제했습니다")
                db.session.commit(); flash(f"{name}님 계정을 삭제했습니다. 맡았던 업무는 담당자 없음으로 남습니다.")
                return redirect(url_for("flow.users_admin"))
        return redirect(url_for("flow.user_edit", id=u.id))
    open_tasks = Task.query.filter(Task.assignees.any(id=u.id), Task.status != "done").count()
    return render_template("flow/user_edit.html", u=u, open_tasks=open_tasks, locked=bool(u.locked_until and u.locked_until > datetime.now()))


@bp.route("/log")
def activity_log():
    return render_template("flow/log.html", acts=Activity.query.order_by(Activity.id.desc()).limit(300).all())
