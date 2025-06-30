#!/usr/bin/env python3
"""
웹크롤링 기반 RAG 파이프라인 실행 스크립트

이 스크립트는 다음과 같은 기능을 제공합니다:
1. 잡코리아, 사람인에서 회사 정보 크롤링
2. OO.ai를 통한 데이터 보완
3. RAG 파이프라인을 통한 데이터 검증 및 추출
4. 최종 보고서 생성

사용법:
    python run_web_crawling_rag.py "회사명"
    python run_web_crawling_rag.py "삼성전자" --output-dir "reports"
    python run_web_crawling_rag.py "네이버" --verbose
"""

import os
import sys
import argparse
import json
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_pipeline.web_crawling_rag_pipeline import WebCrawlingRAGPipeline


def main():
    parser = argparse.ArgumentParser(
        description="웹크롤링 기반 RAG 파이프라인으로 회사 보고서 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python run_web_crawling_rag.py "삼성전자"
  python run_web_crawling_rag.py "네이버" --output-dir "custom_reports"
  python run_web_crawling_rag.py "카카오" --verbose
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

    args = parser.parse_args()

    # OpenAI API 키 확인
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API 키가 필요합니다.")
        print("다음 중 하나의 방법으로 설정해주세요:")
        print("1. 환경변수 설정: export OPENAI_API_KEY='your-api-key'")
        print("2. 명령행 인수: --api-key 'your-api-key'")
        sys.exit(1)

    # 출력 디렉토리 생성
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"🚀 웹크롤링 기반 RAG 파이프라인 시작")
    print(f"📊 대상 회사: {args.company_name}")
    print(f"📁 출력 디렉토리: {output_dir.absolute()}")
    print("=" * 60)

    try:
        # 웹크롤링 RAG 파이프라인 초기화
        pipeline = WebCrawlingRAGPipeline(api_key)

        # 회사 보고서 생성
        report = pipeline.generate_company_report(
            company_name=args.company_name, output_dir=str(output_dir)
        )

        if "error" in report:
            print(f"❌ 오류 발생: {report['error']}")
            sys.exit(1)

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
                status = "✅ 성공" if result["valid"] else "❌ 실패"
                print(f"  • {field}: {status}")
                if result["valid"]:
                    print(f"    데이터: {result['data']}")
                else:
                    print(f"    원인: 데이터 검증 실패")

        print(f"\n✅ 보고서 생성 완료!")
        print(f"📄 파일 위치: {output_dir.absolute()}")

    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류가 발생했습니다: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
