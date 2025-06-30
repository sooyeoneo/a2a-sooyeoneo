"""
enhanced_rag_pipeline.py
향상된 RAG 파이프라인
- 데이터 임베딩 및 Chunking
- 유사도 기반 검색
- 데이터 검증
- LLM 재호출 및 Web Search
"""
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from .company_data_processor import CompanyDataProcessor
from .similarity_search import SimilaritySearch
from .data_validator import DataValidator
from .retry_manager import RetryManager
from .embedding_manager import EmbeddingManager

class EnhancedRAGPipeline:
    """향상된 RAG 파이프라인을 담당하는 클래스"""
    
    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 openai_api_key: Optional[str] = None):
        # 각 단계별 컴포넌트 초기화
        self.data_processor = CompanyDataProcessor(embedding_model)
        self.embedding_manager = EmbeddingManager(embedding_model)
        self.similarity_search = SimilaritySearch(self.embedding_manager)
        self.data_validator = DataValidator()
        self.retry_manager = RetryManager(openai_api_key)
        
        # 파이프라인 설정
        self.collection_name = "company_data"
        self.similarity_threshold = 0.7
        self.max_retries = 3
        
        print("✅ 향상된 RAG 파이프라인 초기화 완료")
    
    def initialize_pipeline(self, data_file_path: str) -> Dict[str, Any]:
        """
        파이프라인을 초기화합니다.
        
        Args:
            data_file_path: 데이터 파일 경로
            
        Returns:
            Dict: 초기화 결과
        """
        print("🔄 파이프라인 초기화 시작...")
        
        # 1. 데이터 처리 및 벡터 스토어 생성
        processing_result = self.data_processor.process_company_data(
            data_file_path, 
            self.collection_name
        )
        
        if "error" in processing_result:
            return {"success": False, "error": processing_result["error"]}
        
        print(f"✅ 벡터 스토어 생성 완료: {processing_result['chunk_count']}개 청크")
        
        return {
            "success": True,
            "company_name": processing_result["company_name"],
            "chunk_count": processing_result["chunk_count"],
            "collection_name": self.collection_name,
            "initialized_at": datetime.now().isoformat()
        }
    
    def search_and_validate(self, company_name: str, field_name: str, 
                           query: str) -> Dict[str, Any]:
        """
        검색과 검증을 수행합니다.
        
        Args:
            company_name: 회사명
            field_name: 필드명
            query: 검색 쿼리
            
        Returns:
            Dict: 검색 및 검증 결과
        """
        print(f"🔍 검색 및 검증 시작: {company_name} - {field_name}")
        
        # 1. 유사도 검색 및 데이터 추출
        search_result = self.similarity_search.search_and_extract(
            query, field_name, self.collection_name
        )
        
        if not search_result["found"]:
            print(f"❌ 검색 실패: {field_name} 정보를 찾을 수 없음")
            return {
                "success": False,
                "stage": "search",
                "error": "검색 결과 없음",
                "search_result": search_result
            }
        
        extracted_data = search_result["extracted_data"]
        print(f"✅ 검색 완료: {extracted_data} (신뢰도: {search_result['confidence']:.2f})")
        
        # 2. 데이터 검증
        validation_result = self.data_validator.validate_field(
            company_name, field_name, extracted_data
        )
        
        print(f"🔍 검증 결과: {'✅' if validation_result['valid'] else '❌'} {validation_result['reason']}")
        
        # 3. 검증 실패 시 재시도
        retry_result = None
        if not validation_result["valid"] and validation_result["needs_retry"]:
            print("🔄 검증 실패로 인한 재시도 시작...")
            retry_result = self.retry_manager.execute_retry_strategy(
                company_name, field_name, query, validation_result["reason"]
            )
            
            # 재시도 결과로 검증 재수행
            if retry_result["final_result"]["success"] and retry_result["final_result"]["extracted_data"]:
                retry_data = retry_result["final_result"]["extracted_data"]
                validation_result = self.data_validator.validate_field(
                    company_name, field_name, retry_data
                )
                
                # 재시도 결과로 업데이트
                search_result["extracted_data"] = retry_data
                search_result["source"] = retry_result["final_result"]["source"]
                search_result["confidence"] = retry_result["final_result"]["confidence"]
        
        return {
            "success": validation_result["valid"],
            "extracted_data": search_result["extracted_data"],
            "confidence": search_result["confidence"],
            "source": search_result.get("source", "RAG 검색"),
            "validation_result": validation_result,
            "search_result": search_result,
            "retry_info": retry_result if retry_result else None
        }
    
    def batch_search_and_validate(self, company_name: str, 
                                 field_queries: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        여러 필드를 일괄 검색 및 검증합니다.
        
        Args:
            company_name: 회사명
            field_queries: 필드별 쿼리 리스트 [{"field": "...", "query": "..."}]
            
        Returns:
            Dict: 일괄 처리 결과
        """
        print(f"🔄 일괄 검색 및 검증 시작: {company_name}")
        
        results = {}
        validation_summary = {}
        
        for field_query in field_queries:
            field_name = field_query["field"]
            query = field_query["query"]
            
            result = self.search_and_validate(company_name, field_name, query)
            results[field_name] = result
        
        # 전체 검증 요약
        field_data = {field: result["extracted_data"] 
                     for field, result in results.items() 
                     if result["success"]}
        
        if field_data:
            validation_summary = self.data_validator.validate_multiple_fields(
                company_name, field_data
            )
        
        return {
            "company_name": company_name,
            "field_results": results,
            "validation_summary": validation_summary,
            "processed_at": datetime.now().isoformat()
        }
    
    def generate_company_report(self, company_name: str, 
                               required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        회사 보고서를 생성합니다.
        
        Args:
            company_name: 회사명
            required_fields: 필요한 필드 리스트
            
        Returns:
            Dict: 보고서 데이터
        """
        if required_fields is None:
            required_fields = ["대표자", "매출액", "직원수", "설립년도", "업종"]
        
        # 필드별 쿼리 구성
        field_queries = []
        for field in required_fields:
            query = f"{company_name} {field}"
            field_queries.append({"field": field, "query": query})
        
        # 일괄 검색 및 검증
        batch_result = self.batch_search_and_validate(company_name, field_queries)
        
        # 보고서 데이터 구성
        report_data = {
            "company_name": company_name,
            "generated_at": datetime.now().isoformat(),
            "fields": {}
        }
        
        for field_name, result in batch_result["field_results"].items():
            report_data["fields"][field_name] = {
                "value": result.get("extracted_data", "정보 없음"),
                "confidence": result.get("confidence", 0.0),
                "source": result.get("source", "알 수 없음"),
                "valid": result.get("success", False)
            }
        
        # 검증 요약 추가
        if batch_result["validation_summary"]:
            report_data["validation_summary"] = self.data_validator.get_validation_summary(
                batch_result["validation_summary"]
            )
        
        return report_data
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        파이프라인 통계를 반환합니다.
        
        Returns:
            Dict: 파이프라인 통계
        """
        vector_store = self.embedding_manager.load_vector_store(self.collection_name)
        
        if not vector_store:
            return {"error": "벡터 스토어를 찾을 수 없습니다."}
        
        stats = {
            "collection_name": self.collection_name,
            "chunk_count": vector_store["metadata"]["chunk_count"],
            "embedding_dimension": vector_store["metadata"]["embedding_dimension"],
            "model_name": vector_store["metadata"]["model_name"],
            "created_at": vector_store["metadata"]["created_at"],
            "similarity_threshold": self.similarity_threshold,
            "max_retries": self.max_retries
        }
        
        return stats
    
    def update_ground_truth(self, company_name: str, field_data: Dict[str, str]):
        """
        Ground truth 데이터를 업데이트합니다.
        
        Args:
            company_name: 회사명
            field_data: 필드별 데이터
        """
        if company_name not in self.data_validator.ground_truth:
            self.data_validator.ground_truth[company_name] = {}
        
        self.data_validator.ground_truth[company_name].update(field_data)
        print(f"✅ Ground truth 업데이트 완료: {company_name}")
    
    def export_pipeline_data(self, export_path: str) -> Dict[str, Any]:
        """
        파이프라인 데이터를 내보냅니다.
        
        Args:
            export_path: 내보낼 경로
            
        Returns:
            Dict: 내보내기 결과
        """
        try:
            # 벡터 스토어 정보
            vector_store = self.embedding_manager.load_vector_store(self.collection_name)
            
            # Ground truth 데이터
            ground_truth = self.data_validator.ground_truth
            
            # 파이프라인 설정
            pipeline_config = {
                "collection_name": self.collection_name,
                "similarity_threshold": self.similarity_threshold,
                "max_retries": self.max_retries,
                "exported_at": datetime.now().isoformat()
            }
            
            export_data = {
                "pipeline_config": pipeline_config,
                "vector_store_metadata": vector_store["metadata"] if vector_store else None,
                "ground_truth": ground_truth
            }
            
            import json
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "export_path": export_path,
                "exported_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            } 