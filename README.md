# CAD Agentic Workflow Prototype

AWS 기술 블로그의 CAD 도면 분석용 Agentic Workflow 구조를 로컬에서 실행 가능한 Python 프로토타입으로 구현한 예제입니다.

이 구현은 실제 Bedrock/AgentCore 호출 대신 deterministic mock reasoner를 사용합니다. DXF 파서, 이미지 렌더러, VLM 호출부는 인터페이스로 분리되어 있어 나중에 `ezdxf`, `matplotlib`, Amazon Bedrock Converse API, AgentCore Runtime 등으로 교체할 수 있습니다.

## 구조

```text
agentic_cad_workflow/
  agents.py       # Orchestrator, patching, extraction, reasoning agents
  models.py       # 워크플로우 데이터 모델
  reasoners.py    # VLM/LLM 어댑터 인터페이스와 mock 구현
  sample_data.py  # 샘플 CAD 문서
  workflow.py     # end-to-end 실행 함수
  cli.py          # CLI
tests/
  test_workflow.py
```

## 실행

```powershell
python -m agentic_cad_workflow.cli
```

JSON 입력 파일을 쓰려면:

```powershell
python -m agentic_cad_workflow.cli --input sample.json --output result.json
```

입력 JSON은 `CadDocument` 스키마를 따릅니다. 실제 DXF를 직접 읽는 구현은 아직 포함하지 않았고, DXF에서 추출된 중간 표현을 입력으로 받는 형태입니다.

## 구현된 블로그 구조

1. Orchestrator Agent
   - common info 파일과 개별 계통도 파일을 분류합니다.
   - 공통 정보 집계, 개별 정보 집계, 상세 분석 순서를 조율합니다.

2. CAD 구조 이해 및 패칭
   - Example Analyzer가 좋은 패치 기준을 학습합니다.
   - Section Splitter가 섹션 패치를 만듭니다.
   - Evaluator/Error Analyzer/Strategy Planner/Code Modifier 루프가 누락 제목, 테이블 혼재 같은 실패를 수정합니다.

3. 정보 추출
   - 범례와 기기 목록을 텍스트 JSON과 심볼 카탈로그로 분리합니다.
   - 패치별 관제점 후보와 연결 기기를 추출합니다.

4. 심화 추론
   - 전체 계통도 맥락, 패치 추출 정보, 암묵지 규칙을 결합합니다.
   - 관제점별 연결기기와 기능을 최종 테이블로 산출합니다.

## Claude Opus 사용 시 건당 비용 추정

2026년 5월 기준 Claude Opus 4.7 공개 단가는 입력 토큰 5$ / 100만 토큰, 출력 토큰 25$ / 100만 토큰 수준입니다. 이미지는 입력 토큰으로 과금되며, 일반적인 이미지 토큰은 대략 `width * height / 750`으로 계산됩니다. Opus 4.7의 고해상도 이미지 처리에서는 이미지당 토큰이 더 커질 수 있으므로, 실제 비용은 렌더링 해상도와 패치 수에 크게 좌우됩니다.

대략적인 1건 처리 비용은 다음처럼 잡을 수 있습니다.

| 규모 | 가정 | Opus 4.7만 사용 시 추정 |
| --- | --- | --- |
| 소형 | 공통정보 1장 + 도면 1장, 패치 10개 내외 | 1 ~ 3$ |
| 중형 | 도면 3~5장, 패치 30~70개, self-correction 2회 내외 | 8 ~ 20$ |
| 대형 | 도면 10~20장, 패치 150개 이상, 고해상도/재시도 많음 | 50 ~ 150$+ |

비용을 키우는 주요 요인은 다음입니다.

- 패치별 VLM 호출 횟수
- self-correction 루프 반복 횟수
- 고해상도 이미지 패치 수
- 상세 추론 단계에서 생성되는 긴 JSON/표 출력
- 같은 범례, 장비표, 도메인 지식을 매 요청마다 반복 주입하는 방식

운영 환경에서는 모든 단계를 Opus로 돌리기보다 모델을 혼합하는 편이 현실적입니다. 예를 들어 분류, 단순 추출, 1차 검증은 Sonnet/Haiku 또는 규칙 기반 코드로 처리하고, Opus는 최종 추론이나 애매한 연결기기 판단, self-correction 실패 케이스에만 사용하는 방식입니다. 혹은 내부 방침으로 외부 모델 API를 연결하기 어렵다면 VLM모델의 관련 엔지니어링 도메인 지식이 충분한지 검증하고 충분하지 않다면 
로컬에서 돌릴 수 있는 오픈소스 모델에 파인튜닝, RAG 등을 통해 지식을 보충해 주어야 합니다. 
그리고 prompt caching, 공통정보 캐싱, batch processing을 적용하면 중형 도면 기준 비용을 대략 2 ~ 8$ 수준까지 낮출 여지가 있습니다.
