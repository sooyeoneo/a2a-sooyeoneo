import json
import os
from typing import Dict, List, Any, Optional
from decimal import Decimal

from ..web_crawling.jobkorea_crawler import smart_crawl_jobkorea
from ..web_crawling.saramin_crawler import crawl_from_saramin
from ..web_crawling.ooai_crawler import enrich_company_data
from ..web_crawling.data_integration import merge_company_info, filtering_company_info
from .enhanced_rag_pipeline import EnhancedRAGPipeline
from .company_data_processor import CompanyDataProcessor
from .embedding_manager import EmbeddingManager
from .text_splitter import TextSplitter
from .similarity_search import SimilaritySearch
from .data_validator import DataValidator
from .retry_manager import RetryManager

class WebCrawlingRAGPipeline:
    """
    웹크롤링 데이터를 기반으로 RAG 파이프라인을 실행하는 클래스
    """
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.rag_pipeline = EnhancedRAGPipeline(openai_api_key)
        self.data_processor = CompanyDataProcessor()
        self.embedding_manager = EmbeddingManager()
        self.text_splitter = TextSplitter()
        self.similarity_search = SimilaritySearch(self.embedding_manager)
        self.data_validator = DataValidator()
        self.retry_manager = RetryManager(openai_api_key)
        
    def crawl_company_data(self, company_name: str) -> Dict[str, Any]:
        """
        여러 소스에서 회사 데이터를 크롤링하고 통합
        """
        print(f"🔍 '{company_name}' 회사 데이터 크롤링 시작...")
        
        # 1. 잡코리아에서 데이터 수집
        print("📊 잡코리아에서 데이터 수집 중...")
        jobkorea_data = smart_crawl_jobkorea(company_name)
        
        # 2. 사람인에서 데이터 수집
        print("📊 사람인에서 데이터 수집 중...")
        saramin_data = crawl_from_saramin(company_name)
        
        # 3. 데이터 통합
        print("🔄 데이터 통합 중...")
        merged_data = merge_company_info(jobkorea_data, saramin_data)
        
        # 4. OO.ai를 통한 데이터 보완
        print("🔍 OO.ai를 통한 데이터 보완 중...")
        enriched_data = enrich_company_data(company_name, merged_data)
        
        # 5. 데이터 정제
        print("🧹 데이터 정제 중...")
        filtered_data = filtering_company_info(enriched_data)
        
        return filtered_data
    
    def prepare_rag_data(self, company_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        회사 데이터를 RAG 파이프라인에서 사용할 수 있는 형태로 변환
        """
        documents = []
        
        # 기본 정보
        if company_data.get('name'):
            documents.append({
                'content': f"회사명: {company_data['name']}",
                'metadata': {'field': 'name', 'type': 'basic_info'}
            })
        
        if company_data.get('description'):
            documents.append({
                'content': f"회사 설명: {company_data['description']}",
                'metadata': {'field': 'description', 'type': 'basic_info'}
            })
        
        if company_data.get('industry'):
            documents.append({
                'content': f"산업 분야: {company_data['industry']}",
                'metadata': {'field': 'industry', 'type': 'basic_info'}
            })
        
        if company_data.get('products_services'):
            documents.append({
                'content': f"제품/서비스: {company_data['products_services']}",
                'metadata': {'field': 'products_services', 'type': 'basic_info'}
            })
        
        # 경영진 정보
        if company_data.get('key_executive'):
            documents.append({
                'content': f"대표자: {company_data['key_executive']}",
                'metadata': {'field': 'key_executive', 'type': 'management'}
            })
        
        # 직원 정보
        if company_data.get('employee_count'):
            documents.append({
                'content': f"직원 수: {company_data['employee_count']}명",
                'metadata': {'field': 'employee_count', 'type': 'employment'}
            })
        
        # 재무 정보
        if company_data.get('latest_revenue'):
            documents.append({
                'content': f"최근 매출액: {company_data['latest_revenue']}원",
                'metadata': {'field': 'latest_revenue', 'type': 'financial'}
            })
        
        if company_data.get('latest_operating_income'):
            documents.append({
                'content': f"최근 영업이익: {company_data['latest_operating_income']}원",
                'metadata': {'field': 'latest_operating_income', 'type': 'financial'}
            })
        
        if company_data.get('latest_net_income'):
            documents.append({
                'content': f"최근 순이익: {company_data['latest_net_income']}원",
                'metadata': {'field': 'latest_net_income', 'type': 'financial'}
            })
        
        # 재무 히스토리
        if company_data.get('financial_history'):
            try:
                financial_history = json.loads(company_data['financial_history']) if isinstance(company_data['financial_history'], str) else company_data['financial_history']
                for year, data in financial_history.items():
                    for metric, value in data.items():
                        if value:
                            documents.append({
                                'content': f"{year}년 {metric}: {value}",
                                'metadata': {'field': f'financial_{year}_{metric}', 'type': 'financial_history', 'year': year}
                            })
            except:
                pass
        
        # OO.ai 보완 데이터
        if company_data.get('target_customers'):
            documents.append({
                'content': f"주요 목표 고객층: {company_data['target_customers']}",
                'metadata': {'field': 'target_customers', 'type': 'market_analysis'}
            })
        
        if company_data.get('competitors'):
            documents.append({
                'content': f"주요 경쟁사: {company_data['competitors']}",
                'metadata': {'field': 'competitors', 'type': 'market_analysis'}
            })
        
        if company_data.get('strengths'):
            documents.append({
                'content': f"강점: {company_data['strengths']}",
                'metadata': {'field': 'strengths', 'type': 'analysis'}
            })
        
        if company_data.get('risk_factors'):
            documents.append({
                'content': f"위험 요인: {company_data['risk_factors']}",
                'metadata': {'field': 'risk_factors', 'type': 'analysis'}
            })
        
        if company_data.get('recent_trends'):
            documents.append({
                'content': f"최근 동향: {company_data['recent_trends']}",
                'metadata': {'field': 'recent_trends', 'type': 'analysis'}
            })
        
        return documents
    
    def generate_company_report(self, company_name: str, output_dir: str = "generated_reports") -> Dict[str, Any]:
        """
        웹크롤링 데이터를 기반으로 회사 보고서 생성
        """
        print(f"🚀 '{company_name}' 회사 보고서 생성 시작...")
        
        # 1. 웹크롤링으로 데이터 수집
        company_data = self.crawl_company_data(company_name)
        
        # 2. RAG용 문서 준비
        documents = self.prepare_rag_data(company_data)
        
        if not documents:
            print("⚠️ 크롤링된 데이터가 없습니다.")
            return {"error": "크롤링된 데이터가 없습니다."}
        
        # 3. 문서를 텍스트 청크로 분할
        print("📝 문서 분할 중...")
        chunks = []
        for doc in documents:
            doc_chunks = self.text_splitter.split_by_characters(doc['content'])
            for chunk in doc_chunks:
                chunks.append({
                    'content': chunk,
                    'metadata': doc['metadata']
                })
        
        # 4. 임베딩 생성
        print("🔢 임베딩 생성 중...")
        embeddings = []
        for chunk in chunks:
            embedding = self.embedding_manager.get_single_embedding(chunk['content'])
            embeddings.append({
                'content': chunk['content'],
                'embedding': embedding,
                'metadata': chunk['metadata']
            })
        
        # 5. RAG 파이프라인 실행
        print("🔍 RAG 파이프라인 실행 중...")
        
        # 검색할 필드들
        search_fields = [
            "대표자", "직원 수", "매출액", "설립년도", "업종"
        ]
        
        results = {}
        
        for field in search_fields:
            print(f"🔍 '{field}' 검색 중...")
            
            # 유사도 검색
            relevant_docs = self.similarity_search.search_company_info(field)
            
            # 데이터 추출
            extracted_data = self.similarity_search.extract_field_data(relevant_docs, field)
            
            # 데이터 검증
            validation_result = self.data_validator.validate_field(company_name, field, extracted_data or "")
            is_valid = validation_result['valid']
            
            if not is_valid:
                # 재시도 로직
                retry_result = self.retry_manager.retry_with_llm(
                    company_name, field, field, validation_result['reason']
                )
                if retry_result['success']:
                    extracted_data = retry_result['extracted_data']
                    is_valid = True
            
            results[field] = {
                'data': extracted_data,
                'valid': is_valid,
                'source': 'web_crawling'
            }
        
        # 6. 보고서 생성
        print("📄 보고서 생성 중...")
        report = self._generate_report(company_name, company_data, results)
        
        # 7. 결과 저장
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, f"{company_name}_web_crawling_report.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ 보고서가 {report_path}에 저장되었습니다.")
        
        return report
    
    def _generate_report(self, company_name: str, company_data: Dict[str, Any], rag_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        최종 보고서 생성
        """
        report = {
            'company_name': company_name,
            'generation_method': 'web_crawling_rag',
            'raw_data': company_data,
            'rag_results': rag_results,
            'summary': {
                'total_fields_searched': len(rag_results),
                'successful_extractions': sum(1 for result in rag_results.values() if result['valid']),
                'failed_extractions': sum(1 for result in rag_results.values() if not result['valid'])
            },
            'extracted_information': {}
        }
        
        # 성공적으로 추출된 정보만 정리
        for field, result in rag_results.items():
            if result['valid']:
                report['extracted_information'][field] = result['data']
        
        return report 