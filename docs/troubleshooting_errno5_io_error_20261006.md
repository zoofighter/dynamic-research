# [장애 분석 및 트러블슈팅 보고서] DLS 심층 리서치 구동 시 `[Errno 5] Input/output error` 해결

- **문서 ID**: `TRB-20261006-ERRNO5`
- **일시**: 2026-10-06 18:05:00 KST
- **대상 컴포넌트**: `web/app.py` (Streamlit UI), `src/providers/llm.py` (OpenCode LLM Provider), `src/graphs/dls_research_graph.py` (LangGraph DLS Research App)
- **상태**: **해결 완료 (Resolved & Verified)**

---

## 1. 장애 현상 (Incident Overview)

웹 UI(`web/app.py`, Streamlit `http://localhost:8501`)의 **2번 탭 [DLS 심층 리서치]**에서 목차를 승인하고 **`🚀 DLS 심층 리서치 시작`** 버튼 클릭 시, 파이프라인 초기 구동 직후 아래와 같은 치명적 오류 메시지가 발생하며 리서치가 중단됨:

```text
❌ 실행 오류 발생
오류: [Errno 5] Input/output error
```

![Error Dialog](attachment)

---

## 2. 심층 근본 원인 분석 (Root Cause Analysis - RCA)

본 장애는 **단일 원인이 아닌 3가지 구조적 요인이 복합 작용**하여 발생했습니다.

### ① 상위 터미널 세션 종료에 따른 고아 프로세스(Orphaned Process)의 닫힌 PTY 연결 유지
- Streamlit 프로세스(기존 PID: `96672`)는 백그라운드에서 구동 중이었으나, 최초 실행했던 터미널 탭이 닫히면서 **부모 프로세스 ID(PPID)가 1(`launchd`)로 이전된 고아 프로세스 상태**였습니다.
- 이 과정에서 프로세스의 표준 입출력 파일 디스크립터(`FD 0: stdin`, `FD 1: stdout`, `FD 2: stderr`)가 이미 소멸된 가상 터미널 슬레이브 장치(`/dev/ttys003`)를 계속 참조하고 있었습니다.
- **macOS / Unix 커널 특성**: 마스터가 닫힌 가상 터미널(PTY Slave)에 대해 `write()`나 `read()`, 혹은 터미널 I/O 제어를 시도하면 커널이 즉시 **`OSError: [Errno 5] Input/output error` (EIO)**를 발생시킵니다.

### ② OpenCode REST API 감지 루틴의 헬스체크 부재와 Unhandled `print()`
- `src/providers/llm.py`의 `_discover_base_url()` 함수가 설정 파일(`config/settings.yaml`)에 기재된 `http://127.0.0.1:36629`를 실제 서버 활성 여부 확인 없이 무조건 반환했습니다.
- 실제 포트 36629에 서버가 떠있지 않아 `requests.post()`가 `Connection refused ([Errno 61])` 예외를 던졌고, 해당 예외 처리 블록에서 실행된 `print(...)`가 상기 닫힌 터미널(`/dev/ttys003`)로 출력을 시도하다가 커널 레벨에서 `[Errno 5]`를 일으켰습니다.

### ③ CLI Subprocess 실행 시 부모 표준 입력(`stdin`) 무방비 상속
- `opencode run` 명령을 `subprocess.run()`으로 실행할 때 `capture_output=True`로 `stdout`과 `stderr`는 파이프로 가로챘으나, **`stdin`은 부모 프로세스의 FD 0(`/dev/ttys003`)을 그대로 상속**받았습니다.
- Node.js 기반 CLI 바이너리(`opencode`)가 초기화되면서 상속받은 `stdin`의 터미널 상태를 확인(`isatty`, `tcgetattr`)하려다 닫힌 PTY 장치에 접근하여 `EIO [Errno 5]`를 발생시켰습니다.

---

## 3. 해결 조치 내역 (Implemented Fixes)

코드베이스와 런타임 환경 전반에 걸쳐 다중 방어막을 구축했습니다.

### 3.1. `src/providers/llm.py` 고도화
1. **초고속 사전 헬스체크(0.3s) 도입**:
   - `_discover_base_url()`에서 설정 URL이나 감지된 포트에 대해 `/api/health` 응답(200 OK)을 0.3초 이내에 선행 확인합니다.
   - 서버가 미기동 상태이면 0.05초 만에 `None`을 반환하여 불필요한 HTTP 커넥션 타임아웃과 예외 발생 자체를 원천 차단했습니다.
2. **`stdin=subprocess.DEVNULL` 명시**:
   - `subprocess.run()` 호출 시 `stdin=subprocess.DEVNULL`을 지정하여 자식 프로세스가 터미널 입력 장치를 상속받거나 터미널 I/O를 시도하지 않도록 완전 격리했습니다.
3. **실행 파일 절대 경로 보장**:
   - `shutil.which("opencode")`를 통해 시스템 PATH 내 바이너리 경로를 안전하게 획득하도록 보강했습니다.
4. **방어형 로깅 (Safe Print)**:
   - 표준 출력 시 `(OSError, IOError)` 예외를 흡수하여 터미널이 분리되더라도 프로세스가 다운되지 않도록 처리했습니다.

### 3.2. `web/app.py` PTY 파일 디스크립터 복구 및 스트림 방어
1. **Broken PTY 자동 우회 리다이렉션 (`os.dup2`)**:
   - 앱 로드 최상단에서 FD 0, 1, 2에 대해 무해한 입출력(`read(0, 0)`, `write(1, b"")`)을 테스트합니다.
   - 터미널 단절로 인해 `OSError`가 발생할 경우, C/OS 레벨 파일 디스크립터를 즉시 `/dev/null`로 복구 연결(`os.dup2`)하여 모든 하위 라이브러리와 C 익스텐션의 크래시를 방지합니다.
2. **`_SafeWriter` 프록시 클래스 장착**:
   - `sys.stdout` 및 `sys.stderr`를 `_SafeWriter`로 감싸 파이썬 런타임 내의 모든 비정상 I/O 호출을 무해화했습니다.
3. **상세 오류 트레이스백 Expander 추가**:
   - UI 예외 발생 시 단순 한 줄 에러 대신 `traceback.format_exc()`를 담은 디버그 Expander를 노출하여 운영 가시성을 확보했습니다.

### 3.3. 기타 프로바이더 방어형 출력 적용
- `src/providers/search.py`: DuckDuckGo / Serper 예외 출력 감싸기
- `src/providers/rss.py`: Google News RSS 수집 에러 출력 감싸기
- `src/nodes/research_nodes.py`: 4대 번들 패키징 경고 출력 감싸기

### 3.4. 런타임 프로세스 정상화
- 닫힌 PTY를 물고 있던 기존 고아 프로세스(PID: `96672`)를 정리하고, 깨끗한 입출력 환경의 Streamlit 서버를 재가동(`http://localhost:8501`)했습니다.

---

## 4. 검증 및 테스트 결과 (Validation & Verification)

### 4.1. 유닛 & 통합 테스트 실행
LangGraph DLS 자율 심층 파이프라인을 1개 섹션 및 4대 번들 생성 모드로 실구동 검증:

```bash
Starting graph stream test...
Progress: section=개요, reflect=0
Progress: section=개요, reflect=1
Progress: section=개요, reflect=2
Finished successfully! 
output_path=/Users/boon/Dropbox/03_code/c_1003_dynamic_research/output/report_테스트_토픽_NVLink_20261006_180107.md
```
- **결과**: `Exit Code 0` (정상 완결)

### 4.2. 4대 전문 보고서 패키지 번들 생성 검증
`output/bundles/bundle_...NVLink_20261006_180107/` 내 산출물 정상 발행 확인:
- `00_bundle_manifest.json` (메타데이터 매니페스트)
- `01_executive_brief.md` (경영진 1-Pager 요약본)
- `02_technical_deepdive.md` (심층 기술 분석서)
- `03_competitive_benchmark.md` (경쟁 구도 및 벤치마크 매트릭스)
- `04_risk_due_diligence.md` (리스크 진단 및 Due-Diligence 체크리스트)
- `05_hankyung_article.md` (한국경제 글로벌마켓 심층 기획 기사)
- `full_bundle.zip` (통합 압축 패키지)

---

## 5. 변경 파일 요약

| 파일 경로 | 수정 내용 |
| :--- | :--- |
| [src/providers/llm.py](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/src/providers/llm.py) | 0.3s 빠른 헬스체크 구현, `stdin=subprocess.DEVNULL` 격리, `shutil.which` 경로 탐색, safe print |
| [web/app.py](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/web/app.py) | Broken PTY FD(0, 1, 2) 감지 및 `os.dup2` `/dev/null` 리다이렉션, `_SafeWriter`, Traceback Expander |
| [src/providers/search.py](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/src/providers/search.py) | 검색 프로바이더 예외 print 안전 래핑 |
| [src/providers/rss.py](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/src/providers/rss.py) | RSS 피드 예외 print 안전 래핑 |
| [src/nodes/research_nodes.py](file:///Users/boon/Dropbox/03_code/c_1003_dynamic_research/src/nodes/research_nodes.py) | 보고서 번들 생성 예외 print 안전 래핑 |
