#!/usr/bin/env python3
"""
웹크롤링 기반 RAG 파이프라인 실행 스크립트 (개선된 HTML 생성 기능)

이 스크립트는 다음과 같은 기능을 제공합니다:
1. 잡코리아, 사람인에서 회사 정보 크롤링
2. OO.ai를 통한 데이터 보완
3. RAG 파이프라인을 통한 데이터 검증 및 추출
4. 최종 보고서 생성
5. HTML 보고서 자동 생성 (개선된 버전)

사용법:
    python src/run/run_web_crawling_rag.py "회사명"
    python src/run/run_web_crawling_rag.py "삼성전자" --output-dir "reports"
    python src/run/run_web_crawling_rag.py "네이버" --verbose
"""

# LangSmith/LangChain 트레이싱을 위한 환경변수 설정 (가장 먼저!)
from dotenv import load_dotenv
import os

load_dotenv()  # .env에서 키 로드

# LangSmith/LangChain 트레이싱 활성화
os.environ["LANGCHAIN_TRACING_V2"] = "true"
langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
if langsmith_api_key:
    os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
os.environ["LANGCHAIN_PROJECT"] = "LEADSCOUT"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

# OpenAI API 키도 미리 세팅
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    os.environ["OPENAI_API_KEY"] = openai_api_key

# 상태 확인 및 출력
api_key = os.getenv("LANGCHAIN_API_KEY")
if api_key:
    print("✅ LangSmith 추적이 활성화되었습니다.")
    print(f"📊 프로젝트: {os.getenv('LANGCHAIN_PROJECT')}")
    print(f"🌐 엔드포인트: {os.getenv('LANGCHAIN_ENDPOINT')}")
else:
    print("⚠️ LANGSMITH_API_KEY가 설정되지 않았습니다.")
    print("   .env 파일에 LANGSMITH_API_KEY를 추가하거나")
    print("   환경변수로 설정해주세요.")

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
import re
import traceback

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from rag_pipeline.web_crawling_rag_pipeline import WebCrawlingRAGPipeline
except ImportError as e:
    print(f"❌ RAG 파이프라인 모듈을 찾을 수 없습니다: {e}")
    print("프로젝트 구조를 확인해주세요.")
    sys.exit(1)


def init_langsmith_tracing():
    """LangSmith 추적 초기화 (이미 스크립트 상단에서 설정됨)"""
    # 환경변수는 이미 스크립트 상단에서 설정되었으므로 상태만 확인
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if api_key:
        print("✅ LangSmith 추적이 활성화되었습니다.")
        print(f"📊 프로젝트: {os.getenv('LANGCHAIN_PROJECT')}")
        print(f"🌐 엔드포인트: {os.getenv('LANGCHAIN_ENDPOINT')}")
    else:
        print("⚠️ LANGSMITH_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 LANGSMITH_API_KEY를 추가하거나")
        print("   환경변수로 설정해주세요.")


def sanitize_filename(filename):
    """파일명에서 특수문자를 제거하여 안전한 파일명으로 변환"""
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


def format_currency(amount_str):
    """금액 문자열을 포맷팅"""
    if not amount_str or amount_str == "정보 없음" or str(amount_str).strip() == "":
        return "정보 없음"
    return str(amount_str)


def parse_financial_data(financial_str):
    """재무 데이터 문자열을 파싱하여 리스트로 변환"""
    if not financial_str or financial_str == "정보 없음":
        return ["정보 없음"]
    if isinstance(financial_str, str):
        lines = financial_str.split("\n") if "\n" in financial_str else [financial_str]
        return [line.strip() for line in lines if line.strip()]
    return [str(financial_str)]


# ------------------[ PATCH: 필드 매핑 및 값 추출 함수 추가 ]------------------

FIELD_MAP = {
    "주요_산업": ["industry"],
    "회사_주소_위치": ["address"],
    "대표자": ["key_executive"],
    "설립일": ["established_year"],
    "기업_요약": ["description"],
    "주요_서비스_제품": ["products_services"],
    "임직원_수": ["employee_count"],
    "재무_상태": ["financial_history"],
    "최신_매출": ["latest_revenue"],
    "최신_영업이익": ["latest_operating_income"],
    "최신_순이익": ["latest_net_income"],
    "목표_고객": ["target_customers"],
    "주요_경쟁사": ["competitors"],
    "강점": ["strengths"],
    "위험_요인": ["risk_factors"],
    "최근_동향": ["recent_trends"],
    "홈페이지": ["homepage"],
}

def is_empty(value):
    """값이 null/빈문자/빈리스트/정보 없음이면 True"""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.strip() == "정보 없음"
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False

def get_report_value(extracted_information, raw_data, key):
    # 1. 우선 extracted_information 값
    value = extracted_information.get(key, None)
    if not is_empty(value):
        return value
    # 2. 없으면 매핑된 raw_data 필드에서 가져오기
    for raw_key in FIELD_MAP.get(key, []):
        raw_value = raw_data.get(raw_key, None)
        if not is_empty(raw_value):
            return raw_value
    # 3. 최종적으로 없으면 "정보 없음"
    return "정보 없음"

# ---------------------------------------------------------------------------

def generate_html_report(company_name, report_data, output_dir):
    """
    회사 보고서 데이터를 기반으로 HTML 보고서를 생성합니다.

    Args:
        company_name (str): 회사명
        report_data (dict): 보고서 데이터
        output_dir (str): 출력 디렉토리 경로

    Returns:
        str: 생성된 HTML 파일의 경로
    """

    print(f"🔧 HTML 보고서 생성 시작: {company_name}")
    print(f"📊 보고서 데이터 키: {list(report_data.keys())}")

    # 추출된 정보 가져오기
    extracted_info = report_data.get("extracted_information", {})
    raw_data = report_data.get("raw_data", {})  # PATCH: raw_data 추가

    # PATCH: 필드별로 값을 새로 채움 (extracted_information → raw_data → "정보 없음" 순)
    defaults = {}
    for field in FIELD_MAP:
        value = get_report_value(extracted_info, raw_data, field)
        # 특수 처리: int/float도 문자열로 변환
        if isinstance(value, (int, float)):
            value = str(value)
        defaults[field] = format_currency(value) if "매출" in field or "이익" in field or "순이익" in field else value
        print(f"  ✅ {field}: {defaults[field]}")

    # 재무 데이터 파싱
    financial_data = parse_financial_data(defaults["재무_상태"])

    # 영업이익이 음수인지 확인
    operating_profit_class = ""
    if defaults["최신_영업이익"] and "-" in str(defaults["최신_영업이익"]):
        operating_profit_class = "negative"

    # 순이익이 음수인지 확인
    net_profit_class = ""
    if defaults["최신_순이익"] and "-" in str(defaults["최신_순이익"]):
        net_profit_class = "negative"

    # 홈페이지 링크 생성
    homepage_html = "정보 없음"
    if defaults["홈페이지"] != "정보 없음" and defaults["홈페이지"]:
        homepage_url = str(defaults["홈페이지"])
        if not homepage_url.startswith(("http://", "https://")):
            homepage_url = "http://" + homepage_url
        homepage_html = (
            f'<a href="{homepage_url}" target="_blank">{defaults["홈페이지"]}</a>'
        )

    # HTML 템플릿
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>{company_name} 기업 정보</title>
    <style>
        body {{ max-width: 900px; margin: 0 auto; padding: 20px; box-sizing: border-box; font-family: 'Noto Sans KR', sans-serif; color: #3b3b3b; background-color: #e1e1e1; }}
        header {{ border-bottom: 1px solid #3b3b3b; margin-bottom: 20px; }}
        header .report-header {{ display: flex; align-items: center; gap: 10px; }}
        .logo {{ max-width: 100px; max-height: 100px; margin-right: 20px; }}
        .company-title h1 {{ margin-bottom: 5px; }}
        main {{ background-image: url('https://web-portfolio-files.s3.ap-northeast-2.amazonaws.com/a2a-logo.png'); background-repeat: no-repeat; background-position: left bottom; background-size: 400px auto; }}
        section {{ border-bottom: 1px solid #3b3b3b; padding-bottom: 20px; margin-bottom: 20px; }}
        .info-item {{ display: flex; align-items: baseline; gap: 30px; border-bottom: 1px solid #d9d9d9; padding: 10px 0; }}
        .info-item h3 {{ min-width: 150px; font-size: 15px; color: #3b3b3b; font-weight: 600; margin: 0; }}
        .info-item p, .info-item ul {{ color: #595858; font-size: 15px; margin: 0; flex: 1; }}
        .double-item {{ display: flex; flex-direction: row; gap: 50px; }}
        .inline-pair {{ display: flex; align-items: baseline; gap: 30px; }}
        .highlight {{ color: #4708dc; font-weight: bold; }}
        .text-bold {{ font-weight: bold; }}
        .half-flex {{ flex: 1; }}
        .negative {{ color: #d32f2f; }}
        ul {{ list-style-type: disc; padding-left: 20px; }}
        li {{ margin-bottom: 5px; }}
        a {{ color: #4708dc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        @media print {{ section, .info-item {{ page-break-inside: avoid; }} header, main, section {{ border-bottom: none; }} body {{ border: 1px solid #d9d9d9; }} }}
    </style>
</head>
<body>
<header class="header">
    <div class="company-title">
        <p class="report-header">
            <img src="https://web-portfolio-files.s3.ap-northeast-2.amazonaws.com/peak-logo.png" alt="logo" class="logo-small"/>
            기업 분석 리포트
        </p>
        <h1>{company_name}</h1>
        <p>{defaults["주요_산업"]}</p>
    </div>
</header>
<main>
    <section class="section-basic-info">
        <div>
            <div class="info-item"><h3>주요 산업</h3><p>{defaults["주요_산업"]}</p></div>
            <div class="info-item"><h3>회사 주소/위치</h3><p>{defaults["회사_주소_위치"]}</p></div>
            <div class="double-item info-item">
                <div class="inline-pair half-flex"><h3>대표자</h3><p>{defaults["대표자"]}</p></div>
                <div class="inline-pair half-flex"><h3>설립일</h3><p>{defaults["설립일"]}</p></div>
            </div>
            <div class="info-item"><h3>기업 요약</h3><p>{defaults["기업_요약"]}</p></div>
            <div class="info-item"><h3>주요 서비스/제품</h3><p>{defaults["주요_서비스_제품"]}</p></div>
            <div class="info-item"><h3>임직원 수</h3><p>{defaults["임직원_수"]}</p></div>
            <div class="info-item"><h3>재무 상태</h3>
                <div>
                    <ul>
                        {''.join([f"<li>{item}</li>" for item in financial_data])}
                    </ul>
                </div>
            </div>
            <div class="info-item"><h3>최신 매출</h3><p>{defaults["최신_매출"]}</p></div>
            <div class="info-item"><h3>최신 영업이익</h3><p class="{operating_profit_class}">{defaults["최신_영업이익"]}</p></div>
            <div class="info-item"><h3>최신 순이익</h3><p class="{net_profit_class}">{defaults["최신_순이익"]}</p></div>
            <div class="info-item"><h3>목표 고객</h3><p>{defaults["목표_고객"]}</p></div>
            <div class="info-item"><h3>주요 경쟁사</h3><p>{defaults["주요_경쟁사"]}</p></div>
            <div class="info-item"><h3>강점</h3><p>{defaults["강점"]}</p></div>
            <div class="info-item"><h3>위험 요인</h3><p>{defaults["위험_요인"]}</p></div>
            <div class="info-item"><h3>최근 동향</h3><p>{defaults["최근_동향"]}</p></div>
            <div class="info-item"><h3>홈페이지</h3><p>{homepage_html}</p></div>
        </div>
    </section>
</main>
<footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #d9d9d9; text-align: center; color: #999; font-size: 12px;">
    <p>생성일: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</p>
    <p>본 보고서는 웹크롤링 기반 RAG 파이프라인을 통해 자동으로 생성되었습니다.</p>
</footer>
</body>
</html>"""

    # 파일명 생성 (특수문자 제거)
    safe_company_name = sanitize_filename(company_name)
    filename = f"{safe_company_name}_report.html"

    # 출력 디렉토리 확인 및 생성
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # HTML 파일 저장
    html_file_path = output_path / filename

    try:
        print(f"💾 HTML 파일 저장 시도: {html_file_path}")
        with open(html_file_path, "w", encoding="utf-8") as f:
            f.write(html_template)

        # 파일 생성 확인
        if html_file_path.exists():
            file_size = html_file_path.stat().st_size
            print(f"✅ HTML 보고서가 성공적으로 생성되었습니다!")
            print(f"📄 파일 경로: {html_file_path}")
            print(f"📊 파일 크기: {file_size} bytes")
            return str(html_file_path)
        else:
            print(f"❌ HTML 파일이 생성되지 않았습니다.")
            return None

    except Exception as e:
        print(f"❌ HTML 보고서 생성 중 오류 발생: {e}")
        traceback.print_exc()
        return None


def create_fallback_html_report(company_name, output_dir):
    """
    RAG 파이프라인이 실패한 경우 기본 HTML 보고서를 생성합니다.
    """
    print("🔄 기본 HTML 보고서 생성 중...")

    fallback_data = {
        "extracted_information": {
            "주요_산업": f"{company_name} 관련 업종",
            "회사_주소_위치": "정보 수집 필요",
            "대표자": "정보 수집 필요",
            "설립일": "정보 수집 필요",
            "기업_요약": f"{company_name}에 대한 상세 정보를 수집하지 못했습니다.",
            "주요_서비스_제품": "정보 수집 필요",
            "임직원_수": "정보 수집 필요",
            "재무_상태": "정보 수집 필요",
            "최신_매출": "정보 수집 필요",
            "최신_영업이익": "정보 수집 필요",
            "최신_순이익": "정보 수집 필요",
            "목표_고객": "정보 수집 필요",
            "주요_경쟁사": "정보 수집 필요",
            "강점": "정보 수집 필요",
            "위험_요인": "정보 수집 필요",
            "최근_동향": "정보 수집 필요",
            "홈페이지": "정보 수집 필요",
        }
    }

    return generate_html_report(company_name, fallback_data, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="웹크롤링 기반 RAG 파이프라인으로 회사 보고서 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python src/run/run_web_crawling_rag.py "삼성전자"
  python src/run/run_web_crawling_rag.py "네이버" --output-dir "custom_reports"
  python src/run/run_web_crawling_rag.py "카카오" --verbose
        """,
    )

    parser.add_argument(
        "company_name", help="분석할 회사명 (예: 삼성전자, 네이버, 카카오)"
    )

    parser.add_argument(
        "--output-dir",
        default="generated_reports",
        help="보고서 저장 디렉토리 (기본값: generated_reports)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="상세한 로그 출력")

    parser.add_argument(
        "--api-key", help="OpenAI API 키 (환경변수 OPENAI_API_KEY가 설정되지 않은 경우)"
    )

    parser.add_argument(
        "--html-only",
        action="store_true",
        help="HTML 보고서만 생성 (RAG 파이프라인 건너뛰기)",
    )

    args = parser.parse_args()

    # 프로젝트 루트 기준으로 출력 디렉토리 설정
    if not os.path.isabs(args.output_dir):
        # 상대 경로인 경우 프로젝트 루트의 src 디렉토리 기준으로 설정
        output_dir = project_root / args.output_dir
    else:
        output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"🚀 웹크롤링 기반 RAG 파이프라인 시작")
    print(f"📊 대상 회사: {args.company_name}")
    print(f"📁 출력 디렉토리: {output_dir.absolute()}")
    print(f"🔧 프로젝트 루트: {project_root}")
    print("=" * 60)

    # HTML만 생성하는 테스트 모드
    if args.html_only:
        print("🧪 HTML 전용 모드: RAG 파이프라인을 건너뛰고 기본 HTML만 생성합니다.")
        html_file_path = create_fallback_html_report(args.company_name, str(output_dir))
        if html_file_path:
            print(f"✅ 테스트 HTML 파일이 생성되었습니다: {html_file_path}")
        return

    # OpenAI API 키 확인
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API 키가 필요합니다.")
        print("다음 중 하나의 방법으로 설정해주세요:")
        print("1. 환경변수 설정: export OPENAI_API_KEY='your-api-key'")
        print("2. 명령행 인수: --api-key 'your-api-key'")
        print("3. 또는 --html-only 옵션으로 테스트용 HTML만 생성")
        sys.exit(1)

    try:
        # 웹크롤링 RAG 파이프라인 초기화
        pipeline = WebCrawlingRAGPipeline(api_key)

        # 회사 보고서 생성
        report = pipeline.generate_company_report(
            company_name=args.company_name, output_dir=str(output_dir)
        )

        if "error" in report:
            print(f"❌ RAG 파이프라인 오류 발생: {report['error']}")
            print("🔄 기본 HTML 보고서를 생성합니다...")
            html_file_path = create_fallback_html_report(
                args.company_name, str(output_dir)
            )
            if html_file_path:
                print(f"✅ 기본 HTML 파일이 생성되었습니다: {html_file_path}")
            return

        # HTML 보고서 생성
        print("\n" + "=" * 60)
        print("📋 HTML 보고서 생성 중...")
        print("=" * 60)

        html_file_path = generate_html_report(
            company_name=args.company_name,
            report_data=report,
            output_dir=str(output_dir),
        )

        # 결과 요약 출력
        print("\n" + "=" * 60)
        print("📋 생성된 보고서 요약")
        print("=" * 60)

        summary = report.get("summary", {})
        print(f"🔍 검색된 필드 수: {summary.get('total_fields_searched', 0)}")
        print(f"✅ 성공적으로 추출된 필드: {summary.get('successful_extractions', 0)}")
        print(f"❌ 추출 실패한 필드: {summary.get('failed_extractions', 0)}")

        # 추출된 정보 출력
        extracted_info = report.get("extracted_information", {})
        if extracted_info:
            print(f"\n📊 추출된 정보:")
            for field, data in extracted_info.items():
                print(f"  • {field}: {data}")

        # RAG 결과 상세 출력 (verbose 모드)
        if args.verbose:
            print(f"\n🔍 RAG 파이프라인 상세 결과:")
            rag_results = report.get("rag_results", {})
            for field, result in rag_results.items():
                status = "✅ 성공" if result.get("valid", False) else "❌ 실패"
                print(f"  • {field}: {status}")
                if result.get("valid", False):
                    print(f"    데이터: {result.get('data', 'N/A')}")
                else:
                    print(f"    원인: 데이터 검증 실패")

        print(f"\n✅ 보고서 생성 완료!")
        print(f"📁 저장 디렉토리: {output_dir.absolute()}")
        if html_file_path:
            print(f"📄 HTML 파일: {html_file_path}")

    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류가 발생했습니다: {e}")
        if args.verbose:
            traceback.print_exc()

        # 오류 발생 시에도 기본 HTML 생성 시도
        print("🔄 오류 발생으로 인해 기본 HTML 보고서를 생성합니다...")
        try:
            html_file_path = create_fallback_html_report(
                args.company_name, str(output_dir)
            )
            if html_file_path:
                print(f"✅ 기본 HTML 파일이 생성되었습니다: {html_file_path}")
        except Exception as fallback_error:
            print(f"❌ 기본 HTML 생성도 실패했습니다: {fallback_error}")

        sys.exit(1)


if __name__ == "__main__":
    init_langsmith_tracing()  # LangSmith 추적 초기화
    main()
