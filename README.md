# CAD Agentic Workflow Prototype

![CAD 도면 해석 Agentic Workflow](<assets/agentic workflow.jpg>)

AWS 기술 블로그의 CAD 도면 분석용 Agentic Workflow 구조를 로컬에서 실행 가능한 Python 프로토타입으로 구현한 예제입니다. 이 프로젝트는 실제 CAD 도면을 바로 분석하는 완성형 제품이라기보다는, 블로그에서 설명한 에이전트 역할, 데이터 흐름, self-correction 루프, 최종 추론 구조를 코드로 재현한 기준 구현입니다.

현재 구현은 실제 Amazon Bedrock, AgentCore, Claude 호출 대신 deterministic mock reasoner를 사용합니다. 그래서 네트워크나 API 키 없이도 전체 흐름을 이해하고 테스트할 수 있습니다. DXF 파서, 이미지 렌더러, VLM/LLM 호출부는 인터페이스로 분리되어 있어 나중에 `ezdxf`, `matplotlib`, Amazon Bedrock Converse API, AgentCore Runtime 등으로 교체할 수 있습니다.

## 프로젝트 목표

이 프로젝트의 목표는 CAD 기반 설비 계통도에서 관제점과 연결 기기를 자동으로 이해하는 Agentic Workflow의 뼈대를 구현하는 것입니다.

예를 들어 AHU 계통도에서 다음과 같은 질문에 답하는 구조를 만듭니다.

- 이 도면은 공통정보 도면인가, 개별 계통도 도면인가?
- 범례와 장비표에는 어떤 심볼과 기기명이 정의되어 있는가?
- 도면을 어떤 패치 단위로 잘라야 분석하기 좋은가?
- 패치에 제목, 표, 주변 요소가 잘 포함되었는가?
- 누락된 정보가 있으면 어떤 방식으로 패치를 보정해야 하는가?
- 각 관제점은 어떤 기기에 연결되어 있는가?
- 같은 심볼이라도 덕트 문맥에 따라 다른 의미를 갖는가?
- 최종적으로 관제점별 기기, 기능, 신뢰도, 판단 근거를 어떻게 테이블화할 것인가?

## 전체 구조

```text
agentic_cad_workflow/
  __init__.py      # 패키지 진입점
  agents.py        # Orchestrator, patching, extraction, reasoning agents
  models.py        # 워크플로우 데이터 모델
  reasoners.py     # VLM/LLM 어댑터 인터페이스와 mock 구현
  sample_data.py   # 샘플 CAD 문서와 암묵지 규칙
  workflow.py      # end-to-end 실행 함수
  cli.py           # 명령행 실행 진입점
tests/
  test_workflow.py # 핵심 동작 검증 테스트
```

## 실행 방법

샘플 데이터로 실행하려면 다음 명령을 사용합니다.

```powershell
python -m agentic_cad_workflow.cli
```

JSON 입력 파일을 사용하려면 다음처럼 실행합니다.

```powershell
python -m agentic_cad_workflow.cli --input sample.json --output result.json
```

입력 JSON은 `CadDocument` 스키마를 따릅니다. 현재는 실제 DXF 파일을 직접 읽지 않고, DXF에서 추출된 중간 표현을 입력으로 받는 구조입니다. 실제 운영 버전에서는 이 앞단에 DXF 파서와 이미지 패치 렌더러를 연결하면 됩니다.

## 핵심 파일 설명

### `models.py`

워크플로우 전체에서 사용하는 데이터 모델을 정의합니다. 이 파일은 프로젝트의 공용 언어 역할을 합니다.

주요 모델은 다음과 같습니다.

- `CadDocument`: 하나의 CAD 문서를 표현합니다. 파일명, 문서 ID, 섹션 목록, 공통정보 도면 여부를 포함합니다.
- `Section`: CAD 문서 안의 논리적 영역입니다. 범례, 장비표, AHU 계통도 같은 구역을 표현합니다.
- `Bounds`: 도면 안의 좌표와 크기를 표현합니다. 패치 영역을 확장할 때 `expand()`를 사용합니다.
- `ControlPoint`: 관제점을 표현합니다. `AI`, `AO`, `DI`, `DO` 같은 포인트 타입, 라벨, 위치, 연결 심볼, 덕트 문맥을 포함합니다.
- `Patch`: 분석을 위해 잘라낸 도면 조각입니다. 블로그에서 말하는 patching 결과물입니다.
- `ExtractionResult`: 범례, 장비표, 관제점, 문맥 정보를 모은 중간 결과입니다.
- `AnalysisRow`: 최종 분석 결과 한 줄입니다. 관제점 ID, 연결 기기, 기능, 신뢰도, 판단 근거를 담습니다.
- `WorkflowResult`: 전체 실행 결과입니다. 패치 목록, 추출 결과, 최종 분석 테이블, trace 로그를 포함합니다.

### `agents.py`

블로그의 Agentic Workflow를 에이전트 클래스 단위로 구현한 핵심 파일입니다.

현재 구현된 에이전트는 다음과 같습니다.

- `OrchestratorAgent`: 입력 문서를 공통정보 문서와 개별 도면 문서로 분류합니다.
- `CommonInfoAggregatorAgent`: 범례와 장비표에서 심볼, 기기 매핑 정보를 수집합니다.
- `ExampleAnalyzerAgent`: 좋은 패치 기준을 학습하는 역할입니다. 현재는 mock reasoner를 통해 기준을 반환합니다.
- `SectionSplitterAgent`: 도면 섹션을 분석 가능한 `Patch`로 변환합니다.
- `PatchEvaluatorAgent`: 생성된 패치가 충분한지 평가합니다. 예를 들어 외부 제목 누락 여부를 검사합니다.
- `StrategyPlannerAgent`: 평가 실패 원인을 보고 수정 전략을 만듭니다.
- `CodeModifierAgent`: 수정 전략을 실제 패치 데이터에 반영합니다.
- `SelfCorrectingPatchAgent`: 평가, 계획, 수정을 반복하는 self-correction 루프입니다.
- `DxfInfoAggregatorAgent`: 도면에서 관제점과 덕트 문맥 정보를 수집합니다.
- `DetailedInfoAggregatorAgent`: 심볼, 장비표, 관제점 타입, 덕트 문맥, 암묵지 규칙을 결합해 최종 분석 결과를 만듭니다.

이 파일이 실제 업무 로직의 중심입니다. 향후 실제 VLM, DXF 파서, Bedrock 호출이 붙더라도 에이전트 책임 구조는 대부분 유지할 수 있습니다.

### `reasoners.py`

LLM/VLM 호출부를 추상화한 파일입니다. 현재는 실제 모델 호출 대신 `MockVisionReasoner`를 사용합니다.

- `VisionReasoner`: 에이전트들이 기대하는 모델 기능을 정의한 인터페이스입니다.
- `MockVisionReasoner`: 로컬 테스트용 deterministic reasoner입니다.

나중에 실제 Claude Opus나 Bedrock Converse API를 붙일 때는 이 파일에 `BedrockClaudeReasoner` 같은 구현체를 추가하면 됩니다. 그러면 에이전트 코드는 크게 바꾸지 않고 모델 호출부만 교체할 수 있습니다.

### `workflow.py`

전체 에이전트 실행 순서를 조립하는 오케스트레이션 파일입니다.

`run_workflow()` 함수가 다음 순서로 전체 파이프라인을 실행합니다.

1. 문서 분류
2. 공통정보 수집
3. 패치 기준 생성
4. 도면 섹션 패치화
5. self-correction으로 패치 보정
6. 관제점 정보 수집
7. 공통정보와 도면정보 병합
8. 상세 추론
9. `WorkflowResult` 반환

즉 `workflow.py`는 개별 에이전트의 내부 로직을 담기보다, 각 에이전트를 어떤 순서로 연결할지 결정합니다.

### `sample_data.py`

실제 DXF 파일 없이도 워크플로우를 실행할 수 있게 만든 샘플 데이터 파일입니다.

포함된 데이터는 크게 두 가지입니다.

- 공통정보 문서: `EC_FAN`, `FILTER`, `DM` 같은 심볼과 장비 매핑을 포함합니다.
- AHU 개별 도면: `CP-001`, `CP-002`, `CP-003`, `CP-004` 같은 관제점과 덕트 문맥을 포함합니다.

또 `TACIT_RULES`에는 설비 도면 해석에 필요한 암묵지 규칙이 들어 있습니다. 예를 들어 `EC_FAN`에 연결된 `DI`는 상태 감시점으로 해석하는 식입니다.

### `cli.py`

터미널에서 워크플로우를 실행하기 위한 진입점입니다.

입력 파일이 없으면 샘플 데이터를 사용하고, `--input` 옵션이 있으면 JSON을 읽어 `CadDocument` 모델로 변환한 뒤 워크플로우를 실행합니다. `--output`을 지정하면 결과를 JSON 파일로 저장합니다.

### `tests/test_workflow.py`

핵심 시나리오가 깨지지 않는지 검증하는 테스트입니다.

현재 테스트는 다음을 확인합니다.

- self-correction 루프가 외부 제목을 포함하기 위해 패치 여백을 추가하는지
- mixed section의 table metadata 처리가 반영되는지
- `EC_FAN + SA + DI` 조합이 `SF`의 `status`로 해석되는지
- 같은 `DM` 심볼이 덕트 문맥에 따라 다른 댐퍼로 해석되는지

## 블로그 구조

![AWS 기반 CAD Agent 시스템 아키텍처](assets/CAD%20agent%20system.jpg)

### 1. Orchestrator Agent

Orchestrator는 전체 문서를 처음 받아서 공통정보 파일과 개별 계통도 파일을 분류합니다. 이후 공통정보 집계, 개별정보 집계, 상세 분석 순서를 조율합니다.

현재 코드에서는 `OrchestratorAgent.split_documents()`가 이 역할을 담당합니다.

### 2. CAD 구조 이해 및 패칭

![지능형 분할 에이전트 및 피드백 루프](assets/agentic%20workflow%20korean.jpg)

이 단계는 도면을 분석 가능한 단위로 나누는 과정입니다.

- `ExampleAnalyzerAgent`는 좋은 패치 기준을 학습합니다.
- `SectionSplitterAgent`는 섹션을 패치로 변환합니다.
- `PatchEvaluatorAgent`는 패치 품질을 평가합니다.
- `StrategyPlannerAgent`는 실패 원인에 따른 수정 전략을 만듭니다.
- `CodeModifierAgent`는 패치 영역이나 metadata를 수정합니다.
- `SelfCorrectingPatchAgent`는 이 과정을 반복합니다.

예를 들어 섹션 제목이 패치 바깥에 있으면 `missing_external_title` 문제로 판단하고, `add_top_title_margin` 전략을 적용해 패치 영역을 위쪽으로 확장합니다.

### 3. 정보 추출

이 단계에서는 공통정보와 개별도면 정보를 분리해서 수집합니다.

- 범례와 장비표에서는 심볼 카탈로그와 기기 매핑을 추출합니다.
- 개별 도면에서는 관제점 후보, 연결 심볼, 덕트 문맥을 추출합니다.

현재 구현에서는 실제 DXF 파싱 대신 `sample_data.py`에 구조화된 데이터를 넣어두었고, `CommonInfoAggregatorAgent`와 `DxfInfoAggregatorAgent`가 이를 수집합니다.

### 4. 심화 추론

최종 단계에서는 전체 계통도 맥락, 패치 추출 정보, 범례, 장비표, 암묵지 규칙을 결합합니다.

예를 들어 같은 `DM` 심볼이라도 덕트 문맥이 `EA_BYPASS`이면 `External By-pass Damper`, `MIXED`이면 `Mixed Damper`로 해석합니다. `EC_FAN` 심볼은 공급공기 덕트 문맥과 결합해 `SF`로 판단할 수 있습니다.

이 역할은 `DetailedInfoAggregatorAgent`가 담당합니다.

## 현재 구현의 한계

현재 코드는 구조 검증용 프로토타입이기 때문에 다음 기능은 아직 포함되어 있지 않습니다.

- 실제 DXF 파일 파싱
- CAD 도면 이미지 렌더링
- 도면 패치 이미지 생성
- 실제 Claude Opus 또는 Bedrock VLM 호출
- AgentCore Runtime 배포
- 장기 메모리, 관측성, 실패 재시도 저장소
- 실제 설비 도면별 암묵지 룰셋 관리
- 대량 처리용 큐, 배치, 캐싱 계층

즉 지금 버전은 Agentic Workflow의 뼈대와 책임 분리를 보여주는 구현입니다. 실제 운영형 시스템으로 확장하려면 DXF 처리, VLM 호출, 비용 최적화, trace 저장을 추가해야 합니다.

## 향후 확장 방향

운영 수준으로 확장하려면 다음 순서가 자연스럽습니다.

1. DXF 파서 추가
   - `ezdxf`를 사용해 block, text, line, polyline, layer 정보를 읽습니다.
   - 읽은 결과를 `CadDocument`, `Section`, `ControlPoint`로 변환합니다.

2. 이미지 렌더러 추가
   - DXF 좌표계를 이미지 좌표계로 변환합니다.
   - 섹션별 또는 패치별 PNG 이미지를 생성합니다.

3. 실제 VLM/LLM 연결
   - `reasoners.py`에 Bedrock Claude 구현체를 추가합니다.
   - `VisionReasoner` 인터페이스를 유지하면 에이전트 코드는 크게 바꾸지 않아도 됩니다.

4. 캐싱 계층 추가
   - 범례, 장비표, 암묵지 규칙은 반복 사용되므로 캐싱합니다.
   - prompt caching과 batch processing을 함께 고려합니다.

5. AgentCore 또는 워크플로우 엔진 연동
   - 각 에이전트를 독립 실행 단위로 만들 수 있습니다.
   - trace, retry, timeout, 상태 저장을 운영 관점에서 관리합니다.

## Claude Opus 사용 시 건당 비용 추정

2026년 5월 기준 Claude Opus 4.7 공개 단가는 입력 토큰 $5 / 100만 토큰, 출력 토큰 $25 / 100만 토큰 수준입니다. 이미지는 입력 토큰으로 과금되며, 일반적인 이미지 토큰은 대략 `width * height / 750`으로 계산됩니다. Opus 4.7의 고해상도 이미지 처리에서는 이미지당 토큰이 더 커질 수 있으므로, 실제 비용은 렌더링 해상도와 패치 수에 크게 좌우됩니다.

대략적인 1건 처리 비용은 다음처럼 잡을 수 있습니다.

| 규모 | 가정 | Opus 4.7만 사용 시 추정 |
| --- | --- | --- |
| 소형 | 공통정보 1장 + 도면 1장, 패치 10개 내외 | $1 ~ $3 |
| 중형 | 도면 3~5장, 패치 30~70개, self-correction 2회 내외 | $8 ~ $20 |
| 대형 | 도면 10~20장, 패치 150개 이상, 고해상도/재시도 많음 | $50 ~ $150+ |

비용을 키우는 주요 요인은 다음입니다.

- 패치별 VLM 호출 횟수
- self-correction 루프 반복 횟수
- 고해상도 이미지 패치 수
- 상세 추론 단계에서 생성되는 긴 JSON/표 출력
- 같은 범례, 장비표, 도메인 지식을 매 요청마다 반복 주입하는 방식

운영 환경에서는 모든 단계를 Opus로 돌리기보다 모델을 혼합하는 편이 현실적입니다. 예를 들어 분류, 단순 추출, 1차 검증은 Sonnet/Haiku 또는 규칙 기반 코드로 처리하고, Opus는 최종 추론이나 애매한 연결기기 판단, self-correction 실패 케이스에만 사용하는 방식입니다.

또한 prompt caching, 공통정보 캐싱, batch processing을 적용하면 중형 도면 기준 비용을 대략 $2 ~ $8 수준까지 낮출 여지가 있습니다.

## 요약

이 프로젝트는 CAD 도면 분석을 위한 Agentic Workflow의 최소 실행 구조입니다. 현재는 mock 기반이지만, 에이전트 책임 분리와 데이터 흐름은 실제 시스템으로 확장하기 좋게 구성되어 있습니다.

가장 중요한 확장 포인트는 `reasoners.py`와 DXF 입력 파이프라인입니다. 이 두 부분을 실제 구현으로 교체하면 현재 구조를 유지한 채 Bedrock/Claude 기반 CAD 분석 시스템으로 발전시킬 수 있습니다.
