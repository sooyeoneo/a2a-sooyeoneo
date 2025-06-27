"""
web_report_agent.py
웹 검색 + LLM 기반 기업 보고서 자동 생성 에이전트
"""
import os
import requests
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from jinja2 import Template
import json

# 1. DuckDuckGo 웹 검색 함수 (무료, API 키 불필요)
def web_search(query: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    DuckDuckGo 검색 API를 이용해 쿼리 결과를 반환합니다.
    """
    import urllib.parse
    
    # DuckDuckGo Instant Answer API 사용
    base_url = "https://api.duckduckgo.com/"
    params = {
        'q': query,
        'format': 'json',
        'no_html': '1',
        'skip_disambig': '1'
    }
    
    try:
        # DuckDuckGo API 호출
        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        ddg_data = resp.json()
        
        # 검색 결과 구조화
        search_results = {
            "query": query,
            "abstract": ddg_data.get("Abstract", ""),
            "abstract_text": ddg_data.get("AbstractText", ""),
            "related_topics": [topic.get("Text", "") for topic in ddg_data.get("RelatedTopics", [])],
            "results": []
        }
        
        # 관련 주제에서 추가 정보 추출
        for topic in ddg_data.get("RelatedTopics", []):
            if isinstance(topic, dict) and "Text" in topic:
                search_results["results"].append({
                    "title": topic.get("Text", ""),
                    "snippet": topic.get("Text", "")
                })
        
        # 추상 정보도 결과에 추가
        if ddg_data.get("Abstract"):
            search_results["results"].append({
                "title": "주요 정보",
                "snippet": ddg_data.get("Abstract", "")
            })
        
        return search_results
        
    except Exception as e:
        # 에러 발생 시 더미 데이터 반환
        return {
            "query": query,
            "abstract": f"{query}에 대한 정보를 찾을 수 없습니다.",
            "abstract_text": "",
            "related_topics": [],
            "results": [
                {
                    "title": "검색 결과 없음",
                    "snippet": f"{query}에 대한 정보를 가져오는 중 오류가 발생했습니다: {str(e)}"
                }
            ]
        }

# 2. 리포트 생성 프롬프트 템플릿
def get_field_format_description(field: str) -> str:
    format_rules = {
        "company_summary": "2~3문장 자유 서술",
        "industry_keywords": "상위 5개 키워드 리스트",
        "target_customers": "3~5개 키워드 리스트",
        "financial_info": "연도:금액 쌍의 객체 (금액은 단일 문자열로 표기)",
        "recent_trends": "3~5개 키워드 리스트",
        "competitors": "{경쟁사: 주요 경쟁 분야} 쌍의 **객체**",
        "strengths": "3~5개 리스트",
        "risk_factors": "3~5개 리스트",
        "key_executives": "이름만 포함한 **단일 문자열**"
    }
    return format_rules.get(field, "단일 문자열 (또는 리스트)")

def get_report_prompt(company_name: str, field: str, combined_content: str) -> str:
    format_description = get_field_format_description(field)
    return f"""
    당신은 회사 분석 전문가입니다. '{company_name}'의 '{field}' 항목을 다음 규칙에 따라 **한 가지** JSON 값으로 반환하세요.
    확실한 정보만 응답하세요.
    없는 정보는 **추측하지 말고** null 을 반환하세요.

            출력 양식: "{format_description}"
            
            회사명: "{company_name}"
            요청 항목: "{field}"

            ### 참고 텍스트:
            {combined_content}

            ### 출력은 오직 아래처럼 JSON만:
            ```json
            {{
            "{field}": ...  // 위 규칙에 맞춘 값
            }}
    """

# 3. LLM을 이용해 각 항목별로 정보 추출
def extract_report_fields(
    company_name: str,
    search_results: Dict[str, Any],
    llm: Any,
    fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    if fields is None:
        fields = [
            "company_summary", "industry_keywords", "target_customers", "financial_info",
            "recent_trends", "competitors", "strengths", "risk_factors", "key_executives"
        ]
    combined_content = json.dumps(search_results, ensure_ascii=False, indent=2)
    report = {}
    for field in fields:
        prompt = get_report_prompt(company_name, field, combined_content)
        response = llm.invoke(prompt)
        try:
            json_str = response.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            data = json.loads(json_str)
            report[field] = data.get(field)
        except Exception as e:
            report[field] = None
    report["company_name"] = company_name
    return report

# 4. HTML 템플릿 (Jinja2)
report_template = """
<!DOCTYPE html>
<html lang="ko">

<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>{{ company_name }} 기업 정보</title>
    <style>
        body {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            box-sizing: border-box;
            font-family: "Noto Sans KR", sans-serif;
            color: #3b3b3b;
            background-color: #e1e1e1;
        }

        header {
            border-bottom: 1px solid #3b3b3b;
        }

        header .report-header {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .logo {
            max-width: 100px;
            max-height: 100px;
            margin-right: 20px;
        }

        .company-title h1 {
            margin-bottom: 5px;
        }

        main {
            /* A2A 이미지 속성 */
            background-image: url("https://web-portfolio-files.s3.ap-northeast-2.amazonaws.com/a2a-logo.png");
            background-repeat: no-repeat;
            background-position: left bottom;
            background-size: 400px auto;
        }

        section {
            border-bottom: 1px solid #3b3b3b;
        }

        .info-item {
            display: flex;
            align-items: baseline;
            gap: 30px;
            border-bottom: solid #d9d9d9;
        }

        .info-item h3 {
            min-width: 150px;
            font-size: 15px;
            color: #3b3b3b;
            font-weight: 600;
        }

        .info-item p, .info-item ul {
            color: #595858;
            font-size: 15px;
        }

        .double-item {
            display: flex;
            flex-direction: row;
            gap: 50px;
        }

        .inline-pair {
            display: flex;
            align-items: baseline;
            gap: 30px;
        }

        .highlight {
            color: #4708dc;
            font-weight: bold;
        }

        .text-bold {
            font-weight: bold;
        }

        .half-flex {
            flex: 1;
        }

        /* ▼▼▼ PDF 페이지 나눔 방지 스타일 추가 ▼▼▼ */
        @media print {
            section, .info-item {
                page-break-inside: avoid;
            }

            header, main, section {
                /* 페이지 나눔 시 경계선이 잘리는 것을 방지 */
                border-bottom: none;
            }

            /* 리포트 전체에 테두리를 주어 깔끔하게 보이도록 설정 */
            body {
                border: 1px solid #d9d9d9;
            }
        }

        /* ▲▲▲ PDF 페이지 나눔 방지 스타일 추가 ▲▲▲ */

    </style>
</head>

<body>
<header class="header">
    <div class="company-title">
        <p class="report-header">
            <img src="https://web-portfolio-files.s3.ap-northeast-2.amazonaws.com/peak-logo.png" alt="logo"
                 class="logo-small"/>
            기업 분석 리포트
        </p>
        <h1>{{ company_name or '회사명 없음' }}</h1>
        <p>
            {% if industry_keywords and industry_keywords|length > 0 %}
            {{ industry_keywords|join(", ") }}
            {% else %}
            정보 없음
            {% endif %}
        </p>
    </div>
</header>

<main>
    <section class="section-basic-info">
        <div>
            <div class="info-item">
                <h3>주요 산업 키워드</h3>
                <p>
                    {% if industry_keywords and industry_keywords|length > 0 %}
                    {{ industry_keywords|join(", ") }}
                    {% else %}
                    정보 없음
                    {% endif %}
                </p>
            </div>
            <div class="info-item">
                <h3>회사 주소/위치</h3>
                <p>{{ company_address or '정보 없음' }}</p>
            </div>
            <div class="double-item info-item">
                <div class="inline-pair">
                    <h3>대표자</h3>
                    <p>{{ key_executives or '정보 없음' }}</p>
                </div>
                <div class="inline-pair">
                    <h3>설립일</h3>
                    <p style="min-width: 100px">{{ founded_date or '정보 없음' }}</p>
                </div>
            </div>

            <div class="info-item">
                <h3>기업 요약</h3>
                <p>{{ company_summary or '정보 없음' }}</p>
            </div>
            <div class="info-item">
                <h3>타겟 고객군</h3>
                <p>
                    {% if target_customers and target_customers|length > 0 %}
                    {{ target_customers|join(", ") }}
                    {% else %}
                    정보 없음
                    {% endif %}
                </p>
            </div>
            <div class="info-item">
                <h3>재무 상태</h3>
                <div>
                    {% if financial_info and financial_info|length > 0 %}
                    <ul>
                        {% for year, price in financial_info.items() %}
                        <li>{{ year }} : {{ price }}</li>
                        {% endfor %}
                    </ul>
                    {% else %}
                    <p>정보 없음</p>
                    {% endif %}
                </div>
            </div>
            <div class="info-item">
                <h3>최신 동향</h3>
                <p>
                    {% if recent_trends and recent_trends|length > 0 %}
                    {{ recent_trends|join(", ") }}
                    {% else %}
                    정보 없음
                    {% endif %}
                </p>
            </div>
        </div>
    </section>

    <section class="section-business">
        <div class="double-item info-item">
            <div class="half-flex">
                <h3>경쟁사</h3>
                {% if competitors and competitors|length > 0 %}
                <ul>
                    {% for name, area in competitors.items() %}
                    <li>{{ name }}</li>
                    {% endfor %}
                </ul>
                {% else %}
                <p>정보 없음</p>
                {% endif %}
            </div>
            <div class="half-flex">
                <h3>주요 경쟁 분야</h3>
                {% if competitors and competitors|length > 0 %}
                <ul>
                    {% for name, area in competitors.items() %}
                    <li>{{ area }}</li>
                    {% endfor %}
                </ul>
                {% else %}
                <p>정보 없음</p>
                {% endif %}
            </div>
        </div>
    </section>

    <section class="section-strength info-item">
        <h3>강점 및 차별점</h3>
        <div>
            {% if strengths and strengths|length > 0 %}
            <ul>
                {% for strength in strengths %}
                <li>{{ strength }}</li>
                {% endfor %}
            </ul>
            {% else %}
            <p>정보 없음</p>
            {% endif %}
        </div>
    </section>

    <section class="section-sales">
        <div class="info-item">
            <h3>리스크 요인</h3>
            <div class="text-bold">
                {% if risk_factors and risk_factors|length > 0 %}
                <ul>
                    {% for risk in risk_factors %}
                    <li>{{ risk }}</li>
                    {% endfor %}
                </ul>
                {% else %}
                <p>정보 없음</p>
                {% endif %}
            </div>
        </div>
    </section>

    <section>
        <div class="info-item">
            <h3>참고 링크</h3>
            <div>
                {% if news and news|length > 0 %}
                <ul>
                    {% for link in news %}
                    <li>
                        <a href="{{ link.url }}" target="_blank">{{ link.title }}</a>
                    </li>
                    {% endfor %}
                </ul>
                {% else %}
                <p>관련 뉴스가 없습니다.</p>
                {% endif %}
            </div>
        </div>
    </section>
    <div class="border-line"></div>
</main>
</body>

</html>
"""

# 5. 전체 파이프라인 함수
def generate_company_report(
    company_name: str,
    llm: Any,
    search_api_key: Optional[str] = None,
    fields: Optional[List[str]] = None
) -> str:
    """
    기업명, LLM 객체를 받아 HTML 리포트 반환
    DuckDuckGo API는 무료이므로 API 키가 필요하지 않습니다.
    """
    search_results = web_search(company_name + " 기업 정보")
    info = extract_report_fields(company_name, search_results, llm, fields)
    template = Template(report_template)
    html = template.render(**info)
    return html

# 6. 예시 데이터를 사용한 테스트 함수
def generate_sample_report():
    """
    예시 데이터를 사용하여 HTML 리포트를 생성합니다.
    """
    import datetime
    
    # 예시 데이터
    data = {
        "company_name": "에이아이코리아",
        "industry_keywords": ["인공지능", "헬스케어", "데이터 분석"],
        "company_address": "서울특별시 강남구 테헤란로 123",
        "key_executives": "홍길동",
        "founded_date": "2017-06-15",
        "company_summary": "AI 기반 헬스케어 솔루션 제공 기업",
        "target_customers": ["병원", "의료기기 기업", "정부기관"],
        "financial_info": {
            "2023": "12억원",
            "2022": "9억원"
        },
        "recent_trends": ["AI 진단 정확도 98% 달성", "글로벌 진출 발표"],
        "competitors": {
            "메디AI": "진단 보조",
            "닥터봇": "의료 상담"
        },
        "strengths": ["정확도 높은 진단 알고리즘", "풍부한 의료 데이터", "전문가 집단 보유"],
        "risk_factors": ["의료법 개정 리스크", "AI 윤리 이슈"],
        "news": [
            {"title": "AI로 암 조기 진단 성공", "url": "https://example.com/news1"},
            {"title": "에이아이코리아, 미국 시장 진출", "url": "https://example.com/news2"}
        ]
    }

    # 템플릿 렌더링
    template = Template(report_template)
    html_output = template.render(**data)

    # 파일로 저장
    with open("company_report.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    print("✅ HTML 리포트가 성공적으로 생성되었습니다.")

if __name__ == "__main__":
    print("이 모듈은 import 하여 사용하세요. 테스트는 test_web_report_agent.py에서 별도 수행합니다.")
    print("예시 데이터로 테스트하려면: generate_sample_report() 함수를 호출하세요.")