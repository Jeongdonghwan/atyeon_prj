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
