"""
company_data_processor.py
회사 데이터 처리 및 임베딩을 위한 모듈
- JSON 데이터를 텍스트로 변환
- 구조화된 데이터를 청크로 분할
- 임베딩 및 벡터 저장
"""
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from .text_splitter import TextSplitter, ChunkConfig
from .embedding_manager import EmbeddingManager

class CompanyDataProcessor:
    """회사 데이터 처리를 담당하는 클래스"""
    
    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.text_splitter = TextSplitter(ChunkConfig(
            chunk_size=512,
            chunk_overlap=100,
            min_chunk_size=100,
            max_chunk_size=1000
        ))
        self.embedding_manager = EmbeddingManager(model_name=embedding_model)
        
    def load_company_data(self, file_path: str) -> Dict[str, Any]:
        """
        JSON 파일에서 회사 데이터를 로드합니다.
        
        Args:
            file_path: JSON 파일 경로
            
        Returns:
            Dict: 회사 데이터
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ 회사 데이터 로드 완료: {file_path}")
            return data
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            return {}
    
    def convert_to_text_chunks(self, company_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        회사 데이터를 텍스트 청크로 변환합니다.
        
        Args:
            company_data: 회사 데이터
            
        Returns:
            List[Dict]: 텍스트 청크 리스트
        """
        chunks = []
        
        # 1. 기본 정보 청크
        basic_info = f"""
        회사명: {company_data.get('name', '정보 없음')}
        설립년도: {company_data.get('established_year', '정보 없음')}
        회사유형: {company_data.get('company_type', '정보 없음')}
        상장여부: {'상장' if company_data.get('is_listed') else '비상장'}
        홈페이지: {company_data.get('homepage', '정보 없음')}
        주소: {company_data.get('address', '정보 없음')}
        업종: {company_data.get('industry', '정보 없음')}
        """
        chunks.append({
            "content": basic_info.strip(),
            "field_type": "basic_info",
            "company_name": company_data.get('name', ''),
            "chunk_id": len(chunks)
        })
        
        # 2. 대표자 정보 청크
        if company_data.get('key_executive'):
            executive_info = f"""
            대표자: {company_data.get('key_executive')}
            회사명: {company_data.get('name', '')}
            """
            chunks.append({
                "content": executive_info.strip(),
                "field_type": "executive",
                "company_name": company_data.get('name', ''),
                "chunk_id": len(chunks)
            })
        
        # 3. 직원 정보 청크
        if company_data.get('employee_count'):
            employee_info = f"""
            직원수: {company_data.get('employee_count')}
            회사명: {company_data.get('name', '')}
            """
            chunks.append({
                "content": employee_info.strip(),
                "field_type": "employee",
                "company_name": company_data.get('name', ''),
                "chunk_id": len(chunks)
            })
        
        # 4. 매출 정보 청크
        if company_data.get('latest_revenue'):
            revenue_info = f"""
            최신 매출액: {company_data.get('latest_revenue')}
            최신 영업이익: {company_data.get('latest_operating_income', '정보 없음')}
            최신 순이익: {company_data.get('latest_net_income', '정보 없음')}
            회계연도: {company_data.get('latest_fiscal_year', '정보 없음')}
            회사명: {company_data.get('name', '')}
            """
            chunks.append({
                "content": revenue_info.strip(),
                "field_type": "financial",
                "company_name": company_data.get('name', ''),
                "chunk_id": len(chunks)
            })
        
        # 5. 재무 이력 청크
        if company_data.get('financial_history'):
            financial_history = company_data['financial_history']
            for year, data in financial_history.items():
                year_info = f"""
                연도: {year}
                영업이익: {data.get('영업이익', '정보 없음')}
                자산합계: {data.get('자산 합계', '정보 없음')}
                회사명: {company_data.get('name', '')}
                """
                chunks.append({
                    "content": year_info.strip(),
                    "field_type": "financial_history",
                    "company_name": company_data.get('name', ''),
                    "year": year,
                    "chunk_id": len(chunks)
                })
        
        # 6. 회사 설명 청크 (긴 텍스트는 분할)
        if company_data.get('description'):
            description_chunks = self.text_splitter.split_by_characters(
                company_data['description'], 
                chunk_size=500
            )
            for i, chunk in enumerate(description_chunks):
                chunks.append({
                    "content": f"회사 설명: {chunk}",
                    "field_type": "description",
                    "company_name": company_data.get('name', ''),
                    "chunk_id": len(chunks)
                })
        
        # 7. 제품/서비스 청크
        if company_data.get('products_services'):
            products_info = f"""
            제품/서비스: {company_data.get('products_services')}
            회사명: {company_data.get('name', '')}
            """
            chunks.append({
                "content": products_info.strip(),
                "field_type": "products",
                "company_name": company_data.get('name', ''),
                "chunk_id": len(chunks)
            })
        
        print(f"✅ 텍스트 청크 생성 완료: {len(chunks)}개 청크")
        return chunks
    
    def create_vector_store(self, chunks: List[Dict[str, Any]], 
                           collection_name: str = "company_data") -> Dict[str, Any]:
        """
        청크들을 벡터 스토어에 저장합니다.
        
        Args:
            chunks: 청크 리스트
            collection_name: 컬렉션 이름
            
        Returns:
            Dict: 벡터 스토어 정보
        """
        return self.embedding_manager.create_vector_store(chunks, collection_name)
    
    def process_company_data(self, file_path: str, collection_name: str = "company_data") -> Dict[str, Any]:
        """
        회사 데이터를 전체 처리합니다.
        
        Args:
            file_path: JSON 파일 경로
            collection_name: 벡터 스토어 컬렉션 이름
            
        Returns:
            Dict: 처리 결과
        """
        # 1. 데이터 로드
        company_data = self.load_company_data(file_path)
        if not company_data:
            return {"error": "데이터 로드 실패"}
        
        # 2. 텍스트 청크 변환
        chunks = self.convert_to_text_chunks(company_data)
        
        # 3. 벡터 스토어 생성
        vector_store = self.create_vector_store(chunks, collection_name)
        
        return {
            "company_name": company_data.get('name', ''),
            "chunk_count": len(chunks),
            "vector_store": vector_store,
            "processed_at": datetime.now().isoformat()
        } 