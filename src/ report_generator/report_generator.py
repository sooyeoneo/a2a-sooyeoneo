import json
import os
from jinja2 import Template

# 1. 데이터 파일 경로
DATA_PATH = os.path.join(os.path.dirname(__file__), '../sample_company_data.json')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'company_report.html')

# 2. HTML 템플릿 (기존 기업 보고서 템플릿)
report_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>{{ name }} 기업 정보</title>
    <style>
        body { max-width: 900px; margin: 0 auto; padding: 20px; box-sizing: border-box; font-family: 'Noto Sans KR', sans-serif; color: #3b3b3b; background-color: #e1e1e1; }
        header { border-bottom: 1px solid #3b3b3b; }
        header .report-header { display: flex; align-items: center; gap: 10px; }
        .logo { max-width: 100px; max-height: 100px; margin-right: 20px; }
        .company-title h1 { margin-bottom: 5px; }
        main { background-image: url('https://web-portfolio-files.s3.ap-northeast-2.amazonaws.com/a2a-logo.png'); background-repeat: no-repeat; background-position: left bottom; background-size: 400px auto; }
        section { border-bottom: 1px solid #3b3b3b; }
        .info-item { display: flex; align-items: baseline; gap: 30px; border-bottom: solid #d9d9d9; }
        .info-item h3 { min-width: 150px; font-size: 15px; color: #3b3b3b; font-weight: 600; }
        .info-item p, .info-item ul { color: #595858; font-size: 15px; }
        .double-item { display: flex; flex-direction: row; gap: 50px; }
        .inline-pair { display: flex; align-items: baseline; gap: 30px; }
        .highlight { color: #4708dc; font-weight: bold; }
        .text-bold { font-weight: bold; }
        .half-flex { flex: 1; }
        @media print { section, .info-item { page-break-inside: avoid; } header, main, section { border-bottom: none; } body { border: 1px solid #d9d9d9; } }
    </style>
</head>
<body>
<header class="header">
    <div class="company-title">
        <p class="report-header">
            <img src="https://web-portfolio-files.s3.ap-northeast-2.amazonaws.com/peak-logo.png" alt="logo" class="logo-small"/>
            기업 분석 리포트
        </p>
        <h1>{{ name or '회사명 없음' }}</h1>
        <p>{{ industry or '정보 없음' }}</p>
    </div>
</header>
<main>
    <section class="section-basic-info">
        <div>
            <div class="info-item"><h3>주요 산업</h3><p>{{ industry or '정보 없음' }}</p></div>
            <div class="info-item"><h3>회사 주소/위치</h3><p>{{ address or '정보 없음' }}</p></div>
            <div class="double-item info-item">
                <div class="inline-pair"><h3>대표자</h3><p>{{ key_executive or '정보 없음' }}</p></div>
                <div class="inline-pair"><h3>설립일</h3><p style="min-width: 100px">{{ established_year or '정보 없음' }}</p></div>
            </div>
            <div class="info-item"><h3>기업 요약</h3><p>{{ description or '정보 없음' }}</p></div>
            <div class="info-item"><h3>주요 서비스/제품</h3><p>{{ products_services or '정보 없음' }}</p></div>
            <div class="info-item"><h3>임직원 수</h3><p>{{ employee_count or '정보 없음' }}</p></div>
            <div class="info-item"><h3>재무 상태</h3>
                <div>
                    {% if financial_history %}
                    <ul>
                        {% for year, info in financial_history.items() %}
                        <li>{{ year }}: {{ info['영업이익'] }} / {{ info['자산 합계'] }}</li>
                        {% endfor %}
                    </ul>
                    {% else %}
                    <p>정보 없음</p>
                    {% endif %}
                </div>
            </div>
            <div class="info-item"><h3>최신 매출</h3><p>{{ latest_revenue or '정보 없음' }}</p></div>
            <div class="info-item"><h3>최신 영업이익</h3><p>{{ latest_operating_income or '정보 없음' }}</p></div>
            <div class="info-item"><h3>최신 순이익</h3><p>{{ latest_net_income or '정보 없음' }}</p></div>
        </div>
    </section>
</main>
</body>
</html>
"""

if __name__ == "__main__":
    # 1. 데이터 로드
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 2. 템플릿 렌더링
    template = Template(report_template)
    html_output = template.render(**data)

    # 3. 파일로 저장
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_output)

    print(f"✅ HTML 리포트가 성공적으로 생성되었습니다: {OUTPUT_PATH}") 