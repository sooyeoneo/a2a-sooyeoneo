#!/usr/bin/env python3
"""
run_enhanced_rag.py
향상된 RAG 파이프라인 실행 스크립트
"""
import sys
import os
import argparse
from datetime import datetime

# src 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from rag_pipeline.enhanced_rag_pipeline import EnhancedRAGPipeline

def main():
    parser = argparse.ArgumentParser(description='향상된 RAG 파이프라인 실행')
    parser.add_argument('--company', '-c', type=str, default='무신사', 
                       help='분석할 회사명 (기본값: 무신사)')
    parser.add_argument('--data-file', '-d', type=str, 
                       default='src/sample_company_data.json',
                       help='회사 데이터 파일 경로')
    parser.add_argument('--fields', '-f', nargs='+', 
                       default=['대표자', '매출액', '직원수', '설립년도', '업종'],
                       help='검색할 필드들')
    parser.add_argument('--output', '-o', type=str, 
                       default='src/generated_reports',
                       help='결과 저장 디렉토리')
    parser.add_argument('--openai-key', type=str, 
                       help='OpenAI API 키 (환경변수 OPENAI_API_KEY 사용 가능)')
    
    args = parser.parse_args()
    
    print("🚀 향상된 RAG 파이프라인 실행 시작")
    print("=" * 60)
    print(f"회사명: {args.company}")
    print(f"데이터 파일: {args.data_file}")
    print(f"검색 필드: {', '.join(args.fields)}")
    print(f"결과 저장: {args.output}")
    print("=" * 60)
    
    try:
        # 1. 파이프라인 초기화
        print("\n🔄 파이프라인 초기화 중...")
        pipeline = EnhancedRAGPipeline(openai_api_key=args.openai_key)
        
        init_result = pipeline.initialize_pipeline(args.data_file)
        if not init_result["success"]:
            print(f"❌ 파이프라인 초기화 실패: {init_result['error']}")
            return 1
        
        print(f"✅ 파이프라인 초기화 완료: {init_result['chunk_count']}개 청크")
        
        # 2. 회사 보고서 생성
        print(f"\n📊 {args.company} 회사 보고서 생성 중...")
        report = pipeline.generate_company_report(args.company, args.fields)
        
        # 3. 결과 출력
        print(f"\n📋 {args.company} 회사 보고서")
        print("-" * 40)
        print(f"생성 시간: {report['generated_at']}")
        print()
        
        for field_name, field_data in report["fields"].items():
            status = "✅" if field_data["valid"] else "❌"
            print(f"{status} {field_name}: {field_data['value']}")
            if field_data["valid"]:
                print(f"   신뢰도: {field_data['confidence']:.2f}")
                print(f"   출처: {field_data['source']}")
            print()
        
        # 4. 검증 요약 출력
        if report.get("validation_summary"):
            summary = report["validation_summary"]
            print("📈 검증 요약")
            print("-" * 40)
            print(f"전체 필드: {summary['total_fields']}")
            print(f"유효한 필드: {summary['valid_fields']}")
            print(f"정확도: {summary['accuracy']:.2f}")
            print(f"평균 신뢰도: {summary['avg_confidence']:.2f}")
            print()
        
        # 5. 결과 저장
        os.makedirs(args.output, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{args.company}_report_{timestamp}.json"
        report_path = os.path.join(args.output, report_filename)
        
        import json
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"💾 보고서 저장 완료: {report_path}")
        
        # 6. 파이프라인 통계 출력
        print(f"\n📊 파이프라인 통계")
        print("-" * 40)
        stats = pipeline.get_pipeline_stats()
        if "error" not in stats:
            print(f"컬렉션: {stats['collection_name']}")
            print(f"청크 수: {stats['chunk_count']}")
            print(f"임베딩 차원: {stats['embedding_dimension']}")
            print(f"모델: {stats['model_name']}")
            print(f"유사도 임계값: {stats['similarity_threshold']}")
        
        print("\n✅ 향상된 RAG 파이프라인 실행 완료!")
        return 0
        
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main()) 