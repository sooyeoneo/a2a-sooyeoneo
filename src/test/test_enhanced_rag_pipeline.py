"""
test_enhanced_rag_pipeline.py
향상된 RAG 파이프라인 테스트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_pipeline.enhanced_rag_pipeline import EnhancedRAGPipeline
import json

def test_pipeline_initialization():
    """파이프라인 초기화 테스트"""
    print("=" * 50)
    print("1. 파이프라인 초기화 테스트")
    print("=" * 50)
    
    # 파이프라인 초기화
    pipeline = EnhancedRAGPipeline()
    
    # 데이터 파일 경로
    data_file_path = "src/sample_company_data.json"
    
    # 파이프라인 초기화
    init_result = pipeline.initialize_pipeline(data_file_path)
    
    if init_result["success"]:
        print(f"✅ 파이프라인 초기화 성공")
        print(f"   회사명: {init_result['company_name']}")
        print(f"   청크 수: {init_result['chunk_count']}")
        print(f"   컬렉션: {init_result['collection_name']}")
    else:
        print(f"❌ 파이프라인 초기화 실패: {init_result['error']}")
        return False
    
    return True

def test_single_field_search():
    """단일 필드 검색 테스트"""
    print("\n" + "=" * 50)
    print("2. 단일 필드 검색 테스트")
    print("=" * 50)
    
    pipeline = EnhancedRAGPipeline()
    
    # 테스트 케이스들
    test_cases = [
        {
            "company_name": "무신사",
            "field_name": "대표자",
            "query": "무신사 대표자"
        },
        {
            "company_name": "무신사",
            "field_name": "매출액",
            "query": "무신사 매출액"
        },
        {
            "company_name": "무신사",
            "field_name": "직원수",
            "query": "무신사 직원수"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 테스트 케이스 {i}: {test_case['field_name']} ---")
        
        result = pipeline.search_and_validate(
            test_case["company_name"],
            test_case["field_name"],
            test_case["query"]
        )
        
        if result["success"]:
            print(f"✅ 성공: {result['extracted_data']}")
            print(f"   신뢰도: {result['confidence']:.2f}")
            print(f"   출처: {result['source']}")
        else:
            print(f"❌ 실패: {result.get('error', '알 수 없는 오류')}")
            if result.get('retry_info'):
                print(f"   재시도 정보: {result['retry_info']['strategy']}")

def test_batch_search():
    """일괄 검색 테스트"""
    print("\n" + "=" * 50)
    print("3. 일괄 검색 테스트")
    print("=" * 50)
    
    pipeline = EnhancedRAGPipeline()
    
    # 일괄 검색할 필드들
    field_queries = [
        {"field": "대표자", "query": "무신사 대표자"},
        {"field": "매출액", "query": "무신사 매출액"},
        {"field": "직원수", "query": "무신사 직원수"},
        {"field": "설립년도", "query": "무신사 설립년도"},
        {"field": "업종", "query": "무신사 업종"}
    ]
    
    batch_result = pipeline.batch_search_and_validate("무신사", field_queries)
    
    print(f"회사명: {batch_result['company_name']}")
    print(f"처리 시간: {batch_result['processed_at']}")
    
    print("\n--- 필드별 결과 ---")
    for field_name, result in batch_result["field_results"].items():
        status = "✅" if result["success"] else "❌"
        print(f"{status} {field_name}: {result.get('extracted_data', '정보 없음')}")
        if result["success"]:
            print(f"   신뢰도: {result['confidence']:.2f}, 출처: {result['source']}")
    
    # 검증 요약
    if batch_result.get("validation_summary"):
        summary = pipeline.data_validator.get_validation_summary(batch_result["validation_summary"])
        print(f"\n--- 검증 요약 ---")
        print(f"전체 필드: {summary['total_fields']}")
        print(f"유효한 필드: {summary['valid_fields']}")
        print(f"정확도: {summary['accuracy']:.2f}")
        print(f"평균 신뢰도: {summary['avg_confidence']:.2f}")

def test_company_report_generation():
    """회사 보고서 생성 테스트"""
    print("\n" + "=" * 50)
    print("4. 회사 보고서 생성 테스트")
    print("=" * 50)
    
    pipeline = EnhancedRAGPipeline()
    
    # 보고서 생성
    report = pipeline.generate_company_report("무신사")
    
    print(f"회사명: {report['company_name']}")
    print(f"생성 시간: {report['generated_at']}")
    
    print("\n--- 보고서 내용 ---")
    for field_name, field_data in report["fields"].items():
        status = "✅" if field_data["valid"] else "❌"
        print(f"{status} {field_name}: {field_data['value']}")
        print(f"   신뢰도: {field_data['confidence']:.2f}")
        print(f"   출처: {field_data['source']}")
    
    # 검증 요약
    if report.get("validation_summary"):
        summary = report["validation_summary"]
        print(f"\n--- 검증 요약 ---")
        print(f"전체 필드: {summary['total_fields']}")
        print(f"유효한 필드: {summary['valid_fields']}")
        print(f"정확도: {summary['accuracy']:.2f}")
        print(f"평균 신뢰도: {summary['avg_confidence']:.2f}")
    
    return report

def test_pipeline_stats():
    """파이프라인 통계 테스트"""
    print("\n" + "=" * 50)
    print("5. 파이프라인 통계 테스트")
    print("=" * 50)
    
    pipeline = EnhancedRAGPipeline()
    
    stats = pipeline.get_pipeline_stats()
    
    if "error" in stats:
        print(f"❌ 통계 조회 실패: {stats['error']}")
        return
    
    print("--- 파이프라인 통계 ---")
    print(f"컬렉션명: {stats['collection_name']}")
    print(f"청크 수: {stats['chunk_count']}")
    print(f"임베딩 차원: {stats['embedding_dimension']}")
    print(f"모델명: {stats['model_name']}")
    print(f"생성 시간: {stats['created_at']}")
    print(f"유사도 임계값: {stats['similarity_threshold']}")
    print(f"최대 재시도: {stats['max_retries']}")

def test_ground_truth_update():
    """Ground Truth 업데이트 테스트"""
    print("\n" + "=" * 50)
    print("6. Ground Truth 업데이트 테스트")
    print("=" * 50)
    
    pipeline = EnhancedRAGPipeline()
    
    # 새로운 Ground Truth 데이터 추가
    new_ground_truth = {
        "삼성전자": {
            "대표자": "이재용",
            "매출액": "279조원",
            "직원수": "267,000명",
            "설립년도": "1969",
            "업종": "전자제품"
        }
    }
    
    for company_name, field_data in new_ground_truth.items():
        pipeline.update_ground_truth(company_name, field_data)
    
    print("✅ Ground Truth 업데이트 완료")
    print(f"업데이트된 회사: {list(new_ground_truth.keys())}")

def test_export_pipeline_data():
    """파이프라인 데이터 내보내기 테스트"""
    print("\n" + "=" * 50)
    print("7. 파이프라인 데이터 내보내기 테스트")
    print("=" * 50)
    
    pipeline = EnhancedRAGPipeline()
    
    export_path = "src/generated_reports/pipeline_export.json"
    export_result = pipeline.export_pipeline_data(export_path)
    
    if export_result["success"]:
        print(f"✅ 데이터 내보내기 성공")
        print(f"   경로: {export_result['export_path']}")
        print(f"   시간: {export_result['exported_at']}")
    else:
        print(f"❌ 데이터 내보내기 실패: {export_result['error']}")

def main():
    """메인 테스트 함수"""
    print("향상된 RAG 파이프라인 테스트 시작")
    print("=" * 60)
    
    # 1. 파이프라인 초기화
    if not test_pipeline_initialization():
        print("❌ 파이프라인 초기화 실패로 테스트 중단")
        return
    
    # 2. 단일 필드 검색
    test_single_field_search()
    
    # 3. 일괄 검색
    test_batch_search()
    
    # 4. 보고서 생성
    report = test_company_report_generation()
    
    # 5. 파이프라인 통계
    test_pipeline_stats()
    
    # 6. Ground Truth 업데이트
    test_ground_truth_update()
    
    # 7. 데이터 내보내기
    test_export_pipeline_data()
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main() 