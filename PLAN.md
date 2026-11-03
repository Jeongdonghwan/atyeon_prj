# 갤러리 홈페이지 개발 기획안

## 0. 실행 (현재 상태: W1 완료 — Flask 앱 + 어드민 + 샘플 데이터)

```bash
pip install -r requirements.txt
python seed.py        # DB 초기화 + 퍼블릭 도메인 샘플 데이터 (기존 데이터 삭제됨)
python app.py         # http://127.0.0.1:8088  /  어드민 http://127.0.0.1:8088/admin  (admin / 1234)
```

- 공개 페이지 15종: `/ko`, `/ko/about`, `/ko/global`, `/ko/partnership`, `/ko/artists[/slug]`, `/ko/artworks[/slug]`, `/ko/exhibitions[/slug]`, `/ko/academy`, `/ko/academy/mirini`, `/ko/journal[/slug]`, `/ko/media`, `/ko/contact`
- 어드민: 작가·작품·전시·아카데미·저널·미디어 CRUD, 이미지 업로드(WebP 자동 변환) 또는 URL, 문의함, 사이트 설정(상호·연락처·SNS)
- 브랜드 컬러는 `static/site.css` 맨 위 `--p / --p2 / --gold` 세 변수로 교체
- `mockup/`은 초기 정적 시안·레퍼런스 캡처 보관용


기반: `홈페이지화면시안콘텐츠.pdf` (CHEONGYEON Developer Handoff KR v2.0)
상태: 상호·디자인 가이드 미확정 → 아래는 치환 전제로 작성. 문서 내 `{{BRAND}}` 는 상호 확정 후 일괄 치환.

---

## 1. 핵심 결정

| 항목 | 결정 | 이유 |
|---|---|---|
| 스택 | Flask + Jinja2 + SQLAlchemy + MariaDB, gunicorn, nginx | 기존 카페24 서버·deploy 스킬과 동일. 빌드 도구 없음 |
| 프론트 | 순수 HTML/CSS + 최소 JS (햄버거, 폼 검증) | PDF 디자인 방향이 "최소한의 움직임". 프레임워크 불필요 |
| 언어 | `/ko/...` 라우트로 시작, 모든 텍스트 컬럼 `_ko/_en` 쌍 | EN 확장을 1주차에 DB 스키마로만 선반영. EN 템플릿·번역은 2차 |
| 어드민 | Flask 세션 로그인 1계정 + 콘텐츠별 CRUD 폼 | 관리자 1~2명. 권한 체계 불필요 |
| 영상/SNS | YouTube ID 수동 등록 → `youtube-nocookie.com` 임베드. Instagram은 썸네일 + 외부 링크만 | PDF 08 운영 원칙. API 연동은 운영 후 검토 |
| 이미지 | 업로드 시 Pillow로 WebP 변환 + 2종 srcset (800/1600) | 성능 체크리스트 충족, 별도 CDN 없음 |
| 문의 | DB 저장 + 관리자 이메일 알림 (SMTP), honeypot 봇 방어 | 외부 폼 서비스 의존 없음 |
| 검색/필터 | 쿼리스트링 + SQL WHERE | 데이터 100건 이하. 검색엔진 불필요 |

---

## 2. 사이트맵 / 라우트 (14 화면)

```
/ko                        HOME
/ko/about                  ABOUT (브랜드 + 운영주체 2곳 관계 설명)
/ko/global                 GLOBAL (국제 교류)
/ko/partnership            PARTNERSHIP (B2B 제안 + 폼)
/ko/artists                ARTISTS 목록 (?medium=)
/ko/artists/<slug>         ARTIST DETAIL
/ko/artworks               ARTWORKS 목록 (?artist=&medium=)
/ko/artworks/<slug>        ARTWORK DETAIL
/ko/exhibitions            EXHIBITIONS (현재/예정/지난 탭)
/ko/exhibitions/<slug>     EXHIBITION DETAIL
/ko/academy                ACADEMY
/ko/academy/mirini         MIRINI
/ko/journal                JOURNAL 목록 (?category=)
/ko/journal/<slug>         JOURNAL DETAIL
/ko/media                  MEDIA 허브
/ko/contact                CONTACT (목적 분기 폼)
/admin/...                 관리자
/sitemap.xml /robots.txt
```

`/` → `/ko` 리다이렉트. 상단 메뉴: ABOUT · GLOBAL · ARTISTS · EXHIBITIONS · ACADEMY · JOURNAL · CONTACT (PDF 목업 기준 7개. ARTWORKS·MEDIA는 하위 진입).

---

## 3. 데이터 모델

PDF 10절 그대로. 공통 컬럼: `id, slug, status(draft/review/published), published_at, sort, created_at, updated_at`.

| 테이블 | 고유 필드 | 관계 |
|---|---|---|
| artist | name_ko/en, bio_ko/en, portrait, cover | 1:N artwork, N:M exhibition, N:M media |
| artwork | title_ko/en, artist_id, year, medium_ko/en, dimensions, image, alt_ko/en, rights | N:1 artist, N:M exhibition |
| exhibition | title_ko/en, start_date, end_date, location, cover, body_ko/en | N:M artist, N:M artwork, N:M media |
| academy | title_ko/en, audience, summary_ko/en, schedule, inquiry_link | N:M media |
| journal | title_ko/en, category, date, body_ko/en, cover, seo_title, seo_desc | N:1 artist?, N:1 exhibition? |
| media | platform(youtube/instagram), url, video_id, title_ko/en, thumb, description, date | N:M artist/exhibition/academy |
| inquiry | kind(global/artist/academy/general), name, email, organization, country, message, consent, created_at | — (비공개) |
| site_config | key, value | SNS URL, 대표 이메일, OG 기본, 푸터 텍스트 |

N:M은 연결 테이블 3개 (`artist_exhibition`, `artwork_exhibition`, `media_link(media_id, target_type, target_id)`).
`media_link` 하나로 artist/exhibition/academy 연결을 모두 처리 — 테이블 3개 대신 1개.

---

## 4. 페이지별 구성 (PDF 04·05절 요약)

| 화면 | 섹션 순서 | 필요 데이터 |
|---|---|---|
| HOME | 히어로 → 글로벌 선언 → 3 Pillars → 추천 작가·작품 → Academy → 영상·SNS → 문의 CTA | artist(featured 3), artwork(featured 4), media(featured 1+2) |
| ABOUT | 핵심 소개 → 운영 주체 → 갤러리 → WON ART → 비전 → 문의 | 정적 |
| GLOBAL | 대형 선언 → 교류 모델 4종 → 협업 대상 → 제안 절차 → 문의 | 정적 (파트너 로고 없음, PDF 06절 준수) |
| PARTNERSHIP | 제안 → 모델 → 필요 자료 → 폼 → 회신 안내 | inquiry(kind=global) |
| ARTISTS | 인트로 → 추천 → 필터 → 카드 그리드 | artist |
| ARTIST DETAIL | 커버 → 프로필 → 노트 → 작품 4~8 → CV/전시 → 영상 → 문의 | artist + artwork + exhibition + media |
| ARTWORKS | 대표 비주얼 → 그리드 → 필터 | artwork |
| ARTWORK DETAIL | 이미지 → 정보 → 노트 → 관련 작가/전시 → 문의 | artwork |
| EXHIBITIONS | 현재 → 예정 → 지난 (날짜로 자동 분류) | exhibition |
| ACADEMY | 철학 → 과정 카드 → 강연 → 미린이 → 문의 | academy |
| MIRINI | 정의 → LEARN/MEET/MAKE/SHARE → 과정 → FAQ → 문의 | academy(mirini) |
| JOURNAL | 추천 → 카테고리 → 목록 → 관련 링크 | journal |
| MEDIA | 대표 영상 → 유튜브 시리즈 → 릴스 → 저널 → 구독 | media |
| CONTACT | 목적 선택 → 필수 입력 → 동의 → 완료 | inquiry |

카피는 PDF 04·05절 원고를 그대로 템플릿에 하드코딩 (상호 치환 후). 정적 페이지 카피를 DB화하지 않음 — 수정 빈도 낮음.

---

## 5. 디자인 토큰 (잠정, 디자인 가이드 오면 교체)

```css
--bg: #F6F5F0;      /* 아이보리 */
--green: #113E35;   /* 딥 그린 */
--gold: #AF9070;    /* 샌드 골드 */
--text: #172520;
```

브레이크포인트 390 / 768 / 1440. 버튼 최소 높이 44px. 여백 55%+. 폰트 2종 이내.

---

## 6. 단계

| 단계 | 산출물 | 완료 조건 |
|---|---|---|
| W1 | Flask 뼈대, DB 스키마, 어드민 로그인+CRUD, 14개 라우트에 PDF 카피 입힌 흰 템플릿 | 모든 URL 이동, 어드민에서 작가 1명 등록→상세 노출 |
| W2 | 디자인 가이드 반영 (CSS), 반응형, 이미지 업로드/WebP | 390/1440 검수 통과 |
| W3 | 문의 폼+메일, YouTube 임베드, sitemap/robots/OG/hreflang, 실데이터 입력 | 문의 접수 알림 수신, Lighthouse 성능 90+ |
| W4 | 카페24 배포, 도메인 연결, 운영 인수 | HTTPS 접속, 관리자 교육 |

EN 콘텐츠·번역: 별도 단계. 템플릿은 `lang` 변수만 받으면 되도록 W1에서 설계.

---

## 7. 발주처 확인 필요 (임의 제작 금지, PDF 15절)

- [ ] 상호 / 영문 표기 (→ 사용자 별도 제공 예정)
- [ ] 디자인 가이드 (→ 사용자 별도 제공 예정)
- [ ] 실제 작가·작품 명단 + 이미지 이용 허락
- [ ] 일조원갤러리 · WON ART 공식 표기·연혁 (ABOUT 본문)
- [ ] YouTube / Instagram 채널 URL ("명연" 표기 확인)
- [ ] 도메인 (후보: cheongyeonart.com, cheongyeon.art 등 5종 — 등록 가능 여부 미확인)
- [ ] 문의 수신 이메일, 개인정보 처리 담당
- [ ] 글로벌 협업 파트너 표기 — 서면 승인 전 로고·이름 게시 금지

---

## 8. 의도적으로 뺀 것

- YouTube/Instagram API 자동 수집 → 수동 등록 6~12건으로 시작, 운영 후 검토
- 전문 검색, 태그 시스템 → 필터는 쿼리스트링
- 다중 관리자·권한 → 1계정
- CMS 프레임워크(Wagtail 등) → 직접 CRUD가 더 짧음
- 쇼핑/결제 → PDF 명시: "판매가 아닌 비주얼 아카이브"
- 패럴랙스·애니메이션 → PDF 명시 배제

---

## 9. 작가·작품 아카이브 반영 (2026-10-19 추가)

자료: `작가작품아카이브.pdf`(20p 미리보기 북) + `작가 작품 아카이브/`(index.html, artworks.json, artworks.csv, assets 32장). 세 파일 모두 같은 16장 레코드. 레포의 `data/archive/`에 json + 원본 16장(4.9MB) 보관.

### 자료 상태

| 항목 | 내용 |
|---|---|
| 이미지 | 16장 (485×640 ~ 1850px, WebP). 썸네일 16장은 우리 쪽에서 불필요 |
| 작가 확인됨 | 9명: 권대하, 김나라, 김정희, 김준영, 김훈섭, 김진현(도자), 이정박, 정해광, 차영규 |
| 작가 미확인 | 7장: 꽃들 사이에서, 세계의 궤도, The World Is Broad, 모악산 가는 길, 영원한 토지 ×3 |
| 중복 가능 | 영원한 토지 11·12·13 → 동일 작품 촬영본으로 보고 **작품 1건 + 이미지 3장**으로 묶음 |
| 완전한 메타 | 차영규 〈꿈꾸는 산〉 1건만 (100×80, 한지 위에 오브제 및 채색, 2025) |
| 전시 | 가제 "예술, 시간을 담다", 2026-12, 일조원갤러리. 일정·주소·관람시간 미정 |
| 카테고리 | 자연 7 · 추상 3 · 회화 2 · 도시 1 · 인물 1 · 공예 1 (아카이브 필터 기준) |

### 모델 변경 (반영 완료)

- `Artwork.category` (자연·추상·회화·도시·인물·공예) → 작품 목록 필터 칩. 작가 매체 필터와 별개.
- `Artwork.image_2 / image_3` → PDF 스펙 IMG-05 "정면·디테일·설치 최대 3종". 상세 페이지 썸네일 전환.
- `Artwork.review_note`, `Artist.review_note` → 어드민 전용 검수 메모. 사이트 비노출. 목록에 노란 배지.
- 작가 미확인 작품은 `artist_id` 비움. 목록에 "작가 미표기", 어드민에 "미확인" 배지. 관련 작품은 같은 분류로 대체.

### 가져오기 (`import_archive.py`)

```bash
python import_archive.py --replace            # 작가·작품·전시 교체, status=draft (검수 후 어드민에서 공개)
python import_archive.py --replace --publish  # 임시 서버 확인용: 바로 공개
```

- details 문자열 파싱: "72.5 × 72.5 cm · Oil on canvas" → 규격/재료/연도. "확인 필요" 문구는 review_note로.
- 원본 이미지는 `static/uploads/arch-artwork-XX.webp`로 복사. 어드민에서 교체 가능.
- 작가 cover = 그 작가의 첫 작품. 초상(portrait)은 비어 있음 → 수급 필요.
- 전시 cover = 〈숲의 생명, 참 아름다워라〉(PDF 표지와 동일).

### 사이트에서 보이는 위치

| 위치 | 데이터 |
|---|---|
| 홈 히어로 슬라이드 3장 | featured 작품 (세계의 궤도, 푸른 도시의 밤, 숲의 생명, 꿈꾸는 산 중) |
| 홈 Selected Works 띠 | 작품 8점 |
| 홈 추천 작가 | featured 작가 (현재 없음 → 어드민에서 지정) |
| /ko/artists | 9명, 매체 필터 |
| /ko/artists/[slug] | 대표작 · 전시 · CV(비어 있음) |
| /ko/artworks | 14점, 카테고리 + 작가 칩 |
| /ko/artworks/[slug] | 복수 이미지 · 분류 · 규격 · 노트 · 관련 작품 |
| /ko/exhibitions | "예술, 시간을 담다" Upcoming |
| /ko/exhibitions/art-holds-time-2026 | 서문 · 참여 작가 9 · 출품작 |

### 검수 → 공개 절차 (어드민)

1. 작품 14건: 검수 메모 보고 작가 선택 / 재료·규격·연도 입력 / 영원한 토지 분리 여부 결정.
2. 작가 9명: 영문명, 한 문장 소개, 소개문, CV, 초상 이미지. 메인 추천 1~2명 체크.
3. 전시: 공식 전시명, 개막·폐막일, 주소, 관람 시간. 서문 끝 [검수 필요] 문구 삭제.
4. 각 레코드 status → published. 검수 메모 비우기.
5. 작가 저작권 표기 확인 (rights 필드).

### 남은 작업

- 이미지 srcset/리사이즈 (현재 원본 ≤840KB 그대로 서빙. 20장 이하라 당장은 무방)
- 작가 미확인 7장의 작가 확인 → 발주처
- 전시 상세에 설치 전경 사진 슬롯 (image_2/3 활용 또는 Exhibition에 갤러리 추가)

---

## 10. 12월 행사 페이지 기획 — Christmas with ARTEYEON 2026 (2026-10-25)

근거: 행사 포스터 이미지 1장. 아래 "포스터에서 읽은 값"은 확정 전 임시값.

### 포스터에서 읽은 값

| 항목 | 값 |
|---|---|
| 행사명 | Christmas with ARTEYEON 2026 · 참여 작가 & 작품 소개 |
| 부제 | ART CONSTELLATION · 예술과 함께하는 크리스마스의 순간 |
| 주최 | CHEONGYEON × ILJOWON GALLERY |
| 일시 | 2026-12-19(토) 11:00–18:00 (하루 행사) |
| 장소 | 일조원갤러리 · 서울시 종로구 우정국로 38 B1 |
| 문의 | 02-725-3588 / 010-3894-8987 |
| 교통 | 안국역 6번 출구, 종각역 3-1번 출구, 종로3가역 5번 출구 |
| 참여 작가 13명 | 권대하 김나라 김은지 김진현 김훈섭 박종석 신영진 박정렬 이영희 이정박 정해광 차영규 설경철 |
| 대표 작품 | 12점 (기존 아카이브 10점 + 신규 2점 추정: 달 이미지 등) |

### 데이터와 차이 (확인 필요)

- 신규 작가 6명: 김은지, 박종석, 신영진, 박정렬, 이영희, 설경철 → 작품 이미지·정보 수급 필요
- 아카이브엔 있는데 포스터에 없는 작가 2명: 김정희, 김준영 → 이번 행사 제외인지 확인
- 미확인 작가 작품(세계의 궤도, The World Is Broad 등)이 포스터에 실림 → 13명 중 누구 작품인지 매칭 필요
- 포스터 "Materpieces" 오타 → 웹에서는 Masterpieces
- 행사명 "ARTEYEON" ↔ 사이트 상호 "CHEONGYEON" → 상호 확정과 같이 결정
- 기존 "예술, 시간을 담다(가제) 12월 전시"와 이 행사가 같은 건지 → 같으면 하나로 합침

### 어디에 넣나

| 위치 | 내용 | 노출 기간 |
|---|---|---|
| 상단 띠 배너 (전 페이지) | "12.19 SAT · Christmas with ARTEYEON — 관람 신청하기 →" | 오픈 ~ 12/19 |
| 홈 히어로 1번 슬라이드 | 행사 키비주얼 + 신청 버튼 | 오픈 ~ 12/19 |
| 홈 04 Exhibitions | 첫 카드로 고정 (Upcoming 태그) | 자동 (날짜 기준) |
| **행사 상세** `/ko/exhibitions/christmas-2026` | 아래 섹션 구성 | 상시, 종료 후 Archive |
| 행사 신청 `/ko/exhibitions/christmas-2026/apply` | 신청 폼 | 신청 기간 중 |
| 신청 확인 `/ko/apply/check` | 이름+연락처로 조회·취소 | 상시 |
| 어드민 `/admin/registrations` | 신청자 명단·상태 변경·CSV | — |

메뉴는 늘리지 않음. 행사는 전시(Exhibitions)의 한 건으로 관리하고, 띠 배너와 히어로로 끌어온다.

### 행사 상세 페이지 섹션 순서 (포스터 흐름 그대로)

1. **히어로** — 크리스마스 키비주얼, 행사명, 날짜·장소 한 줄, [관람 신청] [신청 확인] 버튼, 남은 일수(D-day)
2. **소개** — "예술과 함께하는 크리스마스의 순간" + 소개문 3줄
3. **참여 작가 13명** — 이름 그리드. 등록된 작가는 작가 페이지로 링크, 미등록은 이름만
4. **대표 작품 미리보기** — 12점 그리드, 클릭 시 작품 상세 (작품 목록 이미지와 동일 데이터)
5. **행사 프로그램** — 시간표 (예: 11:00 오픈 / 14:00 작가와의 대화 / 16:00 크리스마스 이벤트) ← 발주처 확인
6. **전시 안내** — 일시·장소·주소·문의 (아이콘 리스트)
7. **오시는 길** — 지도(네이버/카카오 지도 링크 버튼 + 정적 약도 이미지), 지하철 출구 3개
8. **신청 CTA** — "13인의 감성이 빛나는 크리스마스 아트 페스티벌" + 신청 버튼

디자인: 사이트 기본 블루 톤 유지, 이 페이지만 네이비+골드 강조와 은은한 별(눈) 파티클 애니메이션. 포스터 이미지는 원본 그대로 "포스터 보기" 버튼으로 첨부(다운로드 가능).

### 신청 (관람 예약)

가정: 무료 사전 신청, 시간대별 정원 있음. 시간대가 없으면 "하루 정원"만 둔다.

신청 폼 항목

| 항목 | 필수 | 비고 |
|---|---|---|
| 이름 | ✓ | |
| 휴대폰 | ✓ | 신청 확인 키 |
| 이메일 | | 확인 메일용 |
| 방문 시간대 | ✓ | 11–13 / 13–15 / 15–18, 마감된 시간대는 비활성 |
| 인원 | ✓ | 1–4명 |
| 소속/관심 분야 | | 작가·컬렉터·일반·기관 |
| 남길 말 | | |
| 개인정보 수집·이용 동의 | ✓ | 행사 종료 후 3개월 내 파기 |

- 봇 방지: 기존 문의폼과 같은 허니팟 + 같은 연락처 중복 신청 차단
- 완료 화면: 신청번호(예: X26-0042), 일시·시간대, [신청 확인 바로가기]
- 이메일 입력 시 확인 메일 발송 (SMTP, W3 메일 작업과 같이). 문자(SMS)는 비용 발생 → 선택 사항

### 신청 확인 (방문자)

- `/ko/apply/check` : 이름 + 휴대폰 뒤 4자리 → 내 신청 목록
- 표시: 신청번호, 시간대, 인원, 상태(접수/확정/취소/대기)
- 버튼: [신청 취소] (행사 전날까지), [캘린더에 추가](.ics 다운로드)

### 어드민

- 신청자 목록: 시간대·상태 필터, 검색, 시간대별 신청 인원/정원 표시
- 상태 일괄 변경(확정/취소), 메모
- CSV 다운로드 (현장 체크인 명단 출력용)
- 행사 설정: 신청 열기/닫기, 시간대·정원, 신청 마감일
- 대시보드에 "행사 신청 N명" 카드

### 모델 변경

- `Exhibition`에 추가: `hours`(운영시간), `address`, `phone`, `map_url`, `poster`(포스터 이미지), `apply_open`(bool), `apply_deadline`, `slots`(시간대:정원, 텍스트 "11:00-13:00=40" 줄바꿈)
- 신규 `Registration`: exhibition_id, code, name, phone, email, slot, people, kind, message, consent, status(received/confirmed/cancelled/waiting), memo, created_at
- 전시 상세 템플릿은 `apply_open`이면 행사 섹션(프로그램·안내·오시는 길·신청)을 추가로 보여줌 → 다른 전시도 같은 기능 재사용 가능

### 작업 순서 · 예상

| 단계 | 내용 | 소요 |
|---|---|---|
| 1 | 모델·어드민(행사 설정, 신청자 목록·CSV) | 0.5일 |
| 2 | 행사 상세 페이지 + 띠 배너 + 홈 히어로 연결 | 1일 |
| 3 | 신청 폼·완료·신청 확인/취소 | 0.5일 |
| 4 | 확인 메일, .ics, 정원 마감 처리, 모바일 검수 | 0.5일 |

### 발주처에 받을 것

1. 신규 작가 6명의 작품 이미지·작품명·재료·규격, 미확인 작가 작품의 작가 매칭
2. 행사 당일 프로그램 시간표 (작가와의 대화, 이벤트 등)
3. 신청 방식: 무료/유료, 시간대 구분 여부, 시간대별 정원, 신청 마감일
4. 확인 연락 방식: 이메일만 / 문자 포함
5. 포스터 원본 파일(고해상), 키비주얼 이미지
6. 기존 12월 전시(예술, 시간을 담다)와 같은 행사인지, 행사명 표기(ARTEYEON) 확정

---

## 11. 업무 공유 공간 `/flow` 기획 (2026-11-03)

목적: 행사·전시·작품 판매 업무를 팀원끼리 나눠 맡고, 일정과 진행 상황을 한곳에서 본다. 공개 사이트·사이트 어드민과 분리된 내부 도구.

### 범위 결정

| 항목 | 결정 | 이유 |
|---|---|---|
| 위치 | 같은 Flask 앱 안 `/flow` 블루프린트 | 서버·DB·배포 하나로 끝. 작가·작품·행사·신청 데이터를 바로 연결 |
| 로그인 | `/flow` 전용 계정(아이디·비밀번호), 세션 쿠키 | 기존 `/admin`은 1계정 공용 → 누가 했는지 남지 않음 |
| 계정 생성 | 관리자만 추가 (공개 가입 없음) | 내부 도구. 초대받은 사람만 |
| 기존 `/admin` | 유지. 나중에 `/flow` 관리자 권한으로 통합 | 지금 잘 돌고 있어 건드리지 않음 |
| 외부 도구 | 안 씀 (구글 캘린더 연동은 2차) | 계정·권한·비용 문제 없이 시작 |

### 사용자와 권한

| 역할 | 할 수 있는 것 |
|---|---|
| 관리자 | 사용자 추가·비활성화·비밀번호 초기화, 모든 업무·일정 편집, 사이트 어드민 진입 |
| 팀원 | 업무 생성·내 업무 상태 변경·댓글, 일정 등록, 행사 신청자 명단 열람 |
| 열람자 (외부 협력: 작가·갤러리) | 자기에게 공유된 업무와 일정만 보기·댓글 |

- 사용자 정보: 이름, 아이디, 연락처, 역할, 표시 색(캘린더 구분용), 활성 여부
- 비밀번호는 해시 저장(werkzeug), 로그인 5회 실패 시 10분 잠금
- 비밀번호 분실 → 관리자가 임시 비밀번호 발급, 첫 로그인 때 변경 강제

### 화면 구성

```
/flow/login
/flow                 대시보드 — 오늘·이번 주 내 업무, 지연된 업무, 다가오는 일정, 최근 활동
/flow/calendar        월·주 캘린더 — 일정 + 마감일 있는 업무가 같이 표시, 담당자 색
/flow/tasks           업무 보드 — 할 일 / 진행 중 / 확인 요청 / 완료 4칸 (드래그로 이동)
/flow/tasks/<id>      업무 상세 — 설명, 담당자, 마감, 체크리스트, 댓글, 첨부, 변경 기록
/flow/projects        프로젝트 목록 — 예: "Christmas 2026", "1월 기획전", "작품 판매"
/flow/projects/<id>   프로젝트별 보드 + 일정 + 진행률
/flow/users           (관리자) 사용자 관리
/flow/me              내 정보·비밀번호 변경
```

### 핵심 기능

1. **업무(Task)**: 제목, 설명, 프로젝트, 담당자(여러 명 가능), 요청자, 마감일, 우선순위(높음·보통·낮음), 상태 4단계, 체크리스트, 댓글, 첨부파일
2. **업무 분담**: 관리자·팀원이 업무를 만들어 담당자 지정 → 담당자 대시보드 "내 업무"에 뜸. 담당자가 "확인 요청"으로 넘기면 요청자가 완료 처리
3. **캘린더**: 일정(Event) — 제목, 시작·종료, 종일 여부, 장소, 참석자, 프로젝트. 업무 마감일도 같이 표시. 월/주 보기, 담당자 필터
4. **프로젝트 템플릿**: 행사 하나 만들 때 반복되는 업무 묶음을 한 번에 생성
   - 예: "전시 행사" 템플릿 → D-30 작가 섭외 확정, D-21 포스터 확정, D-14 홈페이지 오픈·신청 시작, D-7 입금 확인 마감, D-3 현장 동선·명단 출력, D-0 현장 운영, D+3 정산·사진 정리
   - 행사 날짜만 넣으면 마감일이 자동 계산됨
5. **사이트 데이터 연결**
   - 업무에 사이트 레코드 연결(행사·작품·작가·문의)
   - 새 행사 신청·새 문의가 들어오면 "입금 확인", "문의 회신" 업무가 담당자에게 자동 생성
   - 행사 프로젝트 화면에 신청 현황(정원 대비) 표시
6. **활동 기록**: 누가 언제 무엇을 바꿨는지(상태 변경, 담당 변경, 댓글) 타임라인
7. **알림**: 1차는 사이트 안 알림(종 아이콘, 안 읽은 수). 2차로 이메일(SMTP) 또는 카카오 알림톡

### 데이터 모델

| 테이블 | 주요 필드 |
|---|---|
| user | id, login_id, name, phone, role(admin/member/viewer), color, password_hash, active, must_change_pw, last_login |
| project | id, name, kind(event/exhibition/sales/etc), start, end, exhibition_id(선택), status |
| task | id, project_id, title, body, status(todo/doing/review/done), priority, due, requester_id, sort, created_at, done_at |
| task_assignee | task_id, user_id |
| task_check | id, task_id, text, done |
| task_link | task_id, target_type(exhibition/artwork/artist/inquiry/registration), target_id |
| calendar_event | id, project_id, title, start, end, all_day, place, memo, created_by |
| event_attendee | event_id, user_id |
| comment | id, task_id, user_id, body, created_at |
| attachment | id, task_id, filename, path, size, user_id |
| activity | id, user_id, verb, target_type, target_id, detail, created_at |
| notification | id, user_id, activity_id, read |
| project_template / template_item | name / title, offset_days, default_role |

기존 테이블은 건드리지 않고 새 테이블만 추가 → 운영 중인 신청 데이터에 영향 없음. 서버에는 `create_all()`로 새 테이블만 생성(기존 테이블 미변경).

### 화면 원칙

- 공개 사이트와 다른 업무용 톤: 흰 배경, 네이비 포인트, 촘촘한 표·보드. 애니메이션 최소
- 모바일 우선 확인 화면: 대시보드와 "내 업무"는 폰에서 바로 처리 가능하게
- 캘린더는 라이브러리 FullCalendar(CDN 1개)로. 직접 만들지 않음
- 보드 드래그는 브라우저 기본 Drag API + 폴백 버튼(상태 선택)

### 단계

| 단계 | 내용 | 예상 |
|---|---|---|
| 1 | 로그인·사용자 관리·권한, 대시보드 뼈대 | 1일 |
| 2 | 프로젝트·업무 보드·업무 상세(담당·마감·체크리스트·댓글) | 1.5일 |
| 3 | 캘린더(일정 + 업무 마감), 담당자 필터 | 1일 |
| 4 | 활동 기록·사이트 내 알림, 행사 신청/문의 → 업무 자동 생성 | 1일 |
| 5 | 프로젝트 템플릿(D-day 자동 마감), 첨부파일 | 0.5일 |
| 2차 | 이메일·카카오 알림, 구글 캘린더 내보내기(.ics 구독), `/admin` 통합 | 별도 |

1단계 완료 후 바로 크리스마스 행사 프로젝트를 템플릿으로 만들어 12/19까지 실제로 써보면서 다듬는 순서를 권장.

### 정해야 할 것

1. 처음 등록할 사용자 명단과 역할 (이름·연락처)
2. 외부 작가·협력사에게도 열어줄지 (열람자 역할 필요 여부)
3. 알림 수단: 사이트 안 알림만 / 이메일 / 카카오 알림톡(건당 비용)
4. 행사 템플릿에 들어갈 반복 업무 목록 (위 예시 기준으로 수정)
5. 주소: `/flow` 그대로 / 별도 서브도메인(`flow.도메인`) — 도메인 연결 시 결정
