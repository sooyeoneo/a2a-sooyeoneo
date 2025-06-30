#!/usr/bin/env python3
"""
웹크롤링 RAG 파이프라인 테스트 스크립트

이 스크립트는 웹크롤링 RAG 파이프라인의 각 구성 요소를 테스트합니다.
"""

import os
import sys
import json
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.web_crawling.jobkorea_crawler import smart_crawl_jobkorea
from src.web_crawling.saramin_crawler import crawl_from_saramin
from src.web_crawling.ooai_crawler import enrich_company_data
from src.web_crawling.data_integration import merge_company_info, filtering_company_info
from src.rag_pipeline.web_crawling_rag_pipeline import WebCrawlingRAGPipeline


def test_web_crawling_components():
    """웹크롤링 구성 요소들을 개별적으로 테스트"""
    print("🧪 웹크롤링 구성 요소 테스트 시작...")

    company_name = "삼성전자"

    # 1. 잡코리아 크롤링 테스트
    print(f"\n1️⃣ 잡코리아 크롤링 테스트: {company_name}")
    try:
        jobkorea_data = smart_crawl_jobkorea(company_name)
        print(f"✅ 잡코리아 데이터 수집 성공")
        print(f"   - 회사명: {jobkorea_data.get('name', 'N/A')}")
        print(f"   - 대표자: {jobkorea_data.get('key_executive', 'N/A')}")
        print(f"   - 직원수: {jobkorea_data.get('employee_count', 'N/A')}")
    except Exception as e:
        print(f"❌ 잡코리아 크롤링 실패: {e}")
        jobkorea_data = {}

    # 2. 사람인 크롤링 테스트
    print(f"\n2️⃣ 사람인 크롤링 테스트: {company_name}")
    try:
        saramin_data = crawl_from_saramin(company_name)
        print(f"✅ 사람인 데이터 수집 성공")
        print(f"   - 회사명: {saramin_data.get('name', 'N/A')}")
        print(f"   - 대표자: {saramin_data.get('key_executive', 'N/A')}")
        print(f"   - 직원수: {saramin_data.get('employee_count', 'N/A')}")
    except Exception as e:
        print(f"❌ 사람인 크롤링 실패: {e}")
        saramin_data = {}

    # 3. 데이터 통합 테스트
    print(f"\n3️⃣ 데이터 통합 테스트")
    try:
        merged_data = merge_company_info(jobkorea_data, saramin_data)
        print(f"✅ 데이터 통합 성공")
        print(f"   - 통합된 회사명: {merged_data.get('name', 'N/A')}")
        print(f"   - 통합된 대표자: {merged_data.get('key_executive', 'N/A')}")
        print(f"   - 통합된 직원수: {merged_data.get('employee_count', 'N/A')}")
    except Exception as e:
        print(f"❌ 데이터 통합 실패: {e}")
        merged_data = {}

    # 4. OO.ai 보완 테스트 (선택적)
    print(f"\n4️⃣ OO.ai 데이터 보완 테스트")
    try:
        enriched_data = enrich_company_data(company_name, merged_data)
        print(f"✅ OO.ai 데이터 보완 성공")
        print(f"   - 목표 고객층: {enriched_data.get('target_customers', 'N/A')}")
        print(f"   - 주요 경쟁사: {enriched_data.get('competitors', 'N/A')}")
    except Exception as e:
        print(f"❌ OO.ai 데이터 보완 실패: {e}")
        enriched_data = merged_data

    # 5. 데이터 정제 테스트
    print(f"\n5️⃣ 데이터 정제 테스트")
    try:
        filtered_data = filtering_company_info(enriched_data)
        print(f"✅ 데이터 정제 성공")
        print(f"   - 정제된 직원수: {filtered_data.get('employee_count', 'N/A')}")
        print(f"   - 정제된 매출액: {filtered_data.get('latest_revenue', 'N/A')}")
    except Exception as e:
        print(f"❌ 데이터 정제 실패: {e}")
        filtered_data = enriched_data

    return filtered_data


def test_rag_pipeline():
    """RAG 파이프라인 테스트"""
    print("\n🧪 RAG 파이프라인 테스트 시작...")

    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API 키가 필요합니다. 환경변수 OPENAI_API_KEY를 설정해주세요.")
        return

    company_name = "삼성전자"

    try:
        # 웹크롤링 RAG 파이프라인 초기화
        pipeline = WebCrawlingRAGPipeline(api_key)

        # 회사 데이터 크롤링
        print(f"\n📊 '{company_name}' 회사 데이터 크롤링...")
        company_data = pipeline.crawl_company_data(company_name)

        if not company_data or not company_data.get("name"):
            print("❌ 크롤링된 데이터가 없습니다.")
            return

        # RAG용 문서 준비
        print(f"\n📝 RAG용 문서 준비...")
        documents = pipeline.prepare_rag_data(company_data)
        print(f"✅ {len(documents)}개의 문서가 준비되었습니다.")

        # 문서 분할 테스트
        print(f"\n✂️ 문서 분할 테스트...")
        chunks = []
        for doc in documents:
            doc_chunks = pipeline.text_splitter.split_by_characters(doc["content"])
            for chunk in doc_chunks:
                chunks.append({"content": chunk, "metadata": doc["metadata"]})
        print(f"✅ {len(chunks)}개의 청크로 분할되었습니다.")

        # 임베딩 생성 테스트 (첫 번째 청크만)
        if chunks:
            print(f"\n🔢 임베딩 생성 테스트...")
            first_chunk = chunks[0]
            embedding = pipeline.embedding_manager.get_single_embedding(
                first_chunk["content"]
            )
            print(f"✅ 임베딩 생성 성공 (차원: {len(embedding)})")

        print(f"\n✅ RAG 파이프라인 테스트 완료!")

    except Exception as e:
        print(f"❌ RAG 파이프라인 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


def test_full_pipeline():
    """전체 파이프라인 테스트"""
    print("\n🧪 전체 파이프라인 테스트 시작...")

    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API 키가 필요합니다. 환경변수 OPENAI_API_KEY를 설정해주세요.")
        return

    company_name = "삼성전자"

    try:
        # 웹크롤링 RAG 파이프라인 초기화
        pipeline = WebCrawlingRAGPipeline(api_key)

        # 전체 보고서 생성
        print(f"\n🚀 '{company_name}' 전체 보고서 생성...")
        report = pipeline.generate_company_report(
            company_name=company_name, output_dir="test_reports"
        )

        if "error" in report:
            print(f"❌ 보고서 생성 실패: {report['error']}")
            return

        # 결과 출력
        print(f"\n📋 생성된 보고서 요약:")
        summary = report.get("summary", {})
        print(f"   - 검색된 필드 수: {summary.get('total_fields_searched', 0)}")
        print(
            f"   - 성공적으로 추출된 필드: {summary.get('successful_extractions', 0)}"
        )
        print(f"   - 추출 실패한 필드: {summary.get('failed_extractions', 0)}")

        # 추출된 정보 출력
        extracted_info = report.get("extracted_information", {})
        if extracted_info:
            print(f"\n📊 추출된 정보:")
            for field, data in extracted_info.items():
                print(f"   • {field}: {data}")

        print(f"\n✅ 전체 파이프라인 테스트 완료!")

    except Exception as e:
        print(f"❌ 전체 파이프라인 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🧪 웹크롤링 RAG 파이프라인 테스트 스위트")
    print("=" * 60)

    # 1. 웹크롤링 구성 요소 테스트
    test_web_crawling_components()

    # 2. RAG 파이프라인 테스트
    test_rag_pipeline()

    # 3. 전체 파이프라인 테스트 (선택적)
    print(f"\n" + "=" * 60)
    print("전체 파이프라인 테스트를 실행하시겠습니까? (y/n): ", end="")
    response = input().lower().strip()

    if response in ["y", "yes", "예"]:
        test_full_pipeline()

    print(f"\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
