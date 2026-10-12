# 항공권 조건 알림 (GitHub Actions)

`alerts.yaml`에 적은 조건으로 GitHub Actions가 **매시간** 구글 항공권을 검색하고,
조건에 맞는 항공편이 새로 나오거나 더 싸지면 휴대폰으로 구글·네이버 항공권 링크와 함께 알림을 보냅니다.
서버나 켜둔 컴퓨터가 필요 없고, 조건은 휴대폰 GitHub 앱에서 `alerts.yaml`만 고치면 됩니다.

## 처음 설정 (한 번만)

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

## 조건 바꾸기
`alerts.yaml`을 편집해서 커밋하면 바로 한 번 검색합니다. 휴대폰 GitHub 앱에서도 파일 → 편집으로 할 수 있어요.
항목 설명은 파일 맨 위 주석에 있습니다. 알림을 여러 개 만들려면 `- name:` 블록을 복사해 추가하세요.

## 알아둘 점
- **알림 규칙**: 날짜 조합(가는 날~오는 날)별 최저가 기준으로, 처음 발견했거나 이전에 알린 가격보다 싸졌을 때만 알림. 한 번에 최대 5개를 묶어 보냅니다. 알린 기록은 `state.json`에 자동 커밋됩니다.
- **실행 시각**: GitHub 예약 실행은 몇 분~수십 분 늦어질 수 있습니다. 주기를 바꾸려면 `.github/workflows/check.yml`의 `cron`을 수정하세요 (예: 3시간마다 `17 */3 * * *`).
- **검색 실패 시**: 구글이 GitHub 서버에서 오는 요청을 막으면 모든 검색이 실패하고 워크플로가 빨간색(실패)으로 표시되며 GitHub가 메일을 보냅니다. `RESULTS.md`의 실패 내역을 확인하세요.
- **데이터 출처**: 구글 항공권은 공식 API가 없어 오픈소스 `fast-flights`로 검색 결과를 읽습니다. 수하물 개수를 넣으면 수하물 요금이 포함된 가격입니다. 네이버 항공권은 직접 수집하지 않고 같은 날짜 검색 링크만 함께 보냅니다.
- 한 알림당 최대 40개 날짜 조합까지만 검색합니다 (요청 사이 2~5초 간격).

## 로컬에서 실행해 보기 (선택)
```bash
pip install -r requirements.txt
set NTFY_TOPIC=flight-deer-8k3j2x      # PowerShell: $env:NTFY_TOPIC="flight-deer-8k3j2x"
python check.py
```
