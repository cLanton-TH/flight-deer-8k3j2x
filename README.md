# 항공권 조건 알림 (GitHub Actions)

휴대폰 설정 페이지(또는 `alerts.json`)에 정한 조건으로 GitHub Actions가 **매시간** 구글 항공권을 검색하고,
조건에 맞는 항공편이 새로 나오거나 더 싸지면 휴대폰으로 구글·네이버 항공권 링크와 함께 알림을 보냅니다.
서버나 켜둔 컴퓨터가 필요 없고, 조건은 휴대폰 설정 페이지에서 바꿉니다.

## 내 것으로 만들어 쓰기 (친구용, 5분)
GitHub 계정만 있으면 됩니다. 서버나 PC는 필요 없어요.

1. 이 저장소 오른쪽 위 **Use this template** → **Create a new repository** → 이름 아무거나, **Public** → Create.
   (버튼이 안 보이면 **Fork**로 만든 뒤, 내 저장소의 **Actions** 탭에서 워크플로 사용을 켜주세요)
2. 휴대폰에 **ntfy** 앱 설치 → `+` → 남이 추측하기 어려운 토픽 이름 구독 (예: `flight-minsu-7q2k9z`).
3. 내 저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** → Name `NTFY_TOPIC`, 값은 2번 토픽 이름.
4. 내 저장소 → **Settings** → **Pages** → Branch `main`, 폴더 `/docs` → Save.
5. https://github.com/settings/personal-access-tokens/new 에서 토큰 생성: Repository access는 **Only select repositories**로 내 저장소만, Permissions에서 **Contents: Read and write**.
6. 휴대폰으로 `https://<내아이디>.github.io/<내저장소이름>/` 접속 → 연결 설정에 토큰 붙여넣기 → 기존 예시 알림을 내 조건으로 고치고 **저장하고 바로 검색**.

이후 매시간 자동 검색하고, 조건에 맞는 항공편이 나오면 휴대폰으로 알림이 옵니다.

## 처음 설정 (직접 PC에서 올리는 경우)

### 1. 휴대폰 알림 앱 준비 (ntfy)
1. 휴대폰에 **ntfy** 앱 설치 (Play 스토어 / App Store).
2. 앱에서 `+` → 남이 추측하기 어려운 토픽 이름 입력 후 구독. 예: `flight-deer-8k3j2x`
   (공개 서버라 토픽 이름을 아는 사람은 알림을 볼 수 있으니 길고 랜덤하게)

### 2. GitHub 저장소 만들기
1. https://github.com/new 에서 저장소 이름(예: `flight-alert`) 입력, **Public** 선택, 다른 옵션은 체크하지 않고 **Create repository**.
2. 이 폴더에서 아래 명령 실행 (`<아이디>`는 본인 GitHub 아이디):
   ```bash
   git init -b main
   git add .
   git commit -m "항공권 알림 시작"
   git remote add origin https://github.com/<아이디>/flight-alert.git
   git push -u origin main
   ```

### 3. 알림 토픽을 Secret으로 등록
저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
- Name: `NTFY_TOPIC`, Secret: 1번에서 만든 토픽 이름

(텔레그램을 쓰려면 `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`도 같은 방법으로 추가)

### 4. 동작 확인
1. 저장소 → **Actions** 탭 → 왼쪽 **항공권 검색** → **Run workflow** → "검색 대신 테스트 알림만 보내기" 체크 → Run.
   휴대폰에 테스트 알림이 오면 연결 성공.
2. 한 번 더 **Run workflow** (체크 없이) → 실제 검색. 끝나면 `RESULTS.md`에 결과가 표로 올라옵니다.

이후로는 매시간 자동으로 돌아갑니다.

## 조건 바꾸기 (휴대폰)
`https://<아이디>.github.io/<저장소이름>/` 페이지에서 여행 일수, 검색 기간(달력), 수하물, 최대 가격, 가는 날·오는 날 출발 시간을 고르고 **저장하고 바로 검색**을 누르면 됩니다.
저장하면 `alerts.json`이 커밋되고 바로 한 번 검색한 뒤, 그 뒤로는 매시간 검색합니다. 페이지에 최근 검색 결과도 같이 보여요.

처음 한 번만 설정:
1. 저장소 → **Settings** → **Pages** → Source: **Deploy from a branch**, Branch: `main`, 폴더: `/docs` → Save.
2. GitHub → 프로필 → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
   - Repository access: **Only select repositories** → 이 저장소
   - Permissions → Repository permissions → **Contents: Read and write**
   - 만료 기간은 원하는 대로 (만료되면 새로 만들어 넣으면 됨)
3. 휴대폰에서 페이지를 열고 **연결 설정**에 토큰을 붙여넣고 **연결**. 토큰은 그 휴대폰 브라우저에만 저장됩니다.
4. 홈 화면에 추가해 두면 앱처럼 쓸 수 있어요.

조건 항목
- **검색 기간**: 여행 전체(가는 날~오는 날)가 이 기간 안에 들어가는 날짜만 검색
- **여행 일수**: 2박3일 = 3일. 여러 개 고르면 모두 검색
- **최대 가격**: 1인당 가격 기준 (여러 명이면 총액 ÷ 인원으로 비교, 알림에는 총액도 표시)
- **수하물**: 없음 / 기내 1개 / 위탁 1개 / 위탁 2개 (선택한 수하물 요금이 포함된 가격으로 비교)
- **출발 시간**: 시작 시~끝 시 (예: 12시~17시면 12:00~17:59 출발)
- 날짜 조합이 60개를 넘으면 한 번에 60개씩 나눠서, 몇 시간에 걸쳐 전체 기간을 돌아가며 검색합니다.

## 알아둘 점
- **알림 규칙**: 날짜 조합(가는 날~오는 날)별 최저가 기준으로, 처음 발견했거나 이전에 알린 가격보다 싸졌을 때만 알림. 한 번에 최대 5개를 묶어 보냅니다. 알린 기록은 `state.json`에 자동 커밋됩니다.
- **실행 시각**: GitHub 예약 실행은 몇 분~수십 분 늦어질 수 있습니다. 주기를 바꾸려면 `.github/workflows/check.yml`의 `cron`을 수정하세요 (예: 3시간마다 `17 */3 * * *`).
- **검색 실패 시**: 구글이 GitHub 서버에서 오는 요청을 막으면 모든 검색이 실패하고 워크플로가 빨간색(실패)으로 표시되며 GitHub가 메일을 보냅니다. `RESULTS.md`의 실패 내역을 확인하세요.
- **데이터 출처**: 구글 항공권은 공식 API가 없어 오픈소스 `fast-flights`로 검색 결과를 읽습니다. 수하물 개수를 넣으면 수하물 요금이 포함된 가격입니다. 네이버 항공권은 직접 수집하지 않고 같은 날짜 검색 링크만 함께 보냅니다.

## 로컬에서 실행해 보기 (선택)
```bash
pip install -r requirements.txt
set NTFY_TOPIC=flight-deer-8k3j2x      # PowerShell: $env:NTFY_TOPIC="flight-deer-8k3j2x"
python check.py
```
