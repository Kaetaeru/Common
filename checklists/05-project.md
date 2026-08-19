# 05. 데스크탑 앱과 프로젝트 설정

설치가 끝난 뒤 실제 워크숍 프로젝트를 사용할 준비를 합니다.

## 체크리스트

- [ ] Google Chrome이 설치되어 있다
- [ ] Claude Desktop이 설치되어 있다
- [ ] Antigravity Desktop 설치 여부를 확인했다
- [ ] Mark 설치 여부를 확인했다
- [ ] 프로젝트 저장소 또는 프로젝트 폴더를 받았다
- [ ] 필요한 경우 `.env.sample`을 `.env`로 복사했다
- [ ] 운영자가 요구한 설정값만 입력했다
- [ ] Python 프로젝트라면 `uv`를 사용할 수 있다

## 데스크탑 앱 확인

Windows 시작 메뉴에서 아래 프로그램을 검색해 실행 여부를 확인합니다.

- Google Chrome
- Claude Desktop
- Antigravity Desktop
- Mark

일부 항목은 자동 설치되지 않을 수 있으므로 운영자 안내가 있으면 수동 설치합니다.

## 프로젝트 환경 설정

`co-develop` 또는 `co-consult` variant를 사용하는 프로젝트에서 `.env.sample`이 있다면:

```powershell
copy .env.sample .env
```

또는 파일 탐색기에서 `.env.sample`을 복사해 `.env`로 이름을 바꿔도 됩니다.

`.env` 파일에는 운영자가 안내한 값만 입력합니다.

## API Key 주의

API Key는 기본 준비사항이 아닙니다.

Claude Pro/Max 및 Gemini Advanced 구독과 별도로 API 연동이 꼭 필요한 경우에만 운영자 안내를 따라 입력합니다.

## Python 프로젝트

`uv`가 정상 설치되어 있는지 확인:

```powershell
uv --version
```

`pyproject.toml` 기반 프로젝트:

```powershell
uv sync
```

`requirements.txt` 기반 프로젝트:

```powershell
uv pip install -r requirements.txt
```

## 영상에서 꼭 설명할 것

### `.env`는 화면에 내용이 노출되지 않게 주의
실제 API Key나 비밀번호가 들어간다면 녹화 화면에 그대로 노출하지 않습니다.

### 프로젝트마다 필요한 설정은 다를 수 있음
이 문서에서 임의의 API Key를 만들거나 값을 추측해서 넣지 않습니다. 운영자가 제공한 값만 사용합니다.

### Docker는 선택 사항
프로젝트 또는 운영자가 별도로 요구하는 경우에만 설치 및 실행 여부를 확인합니다.
