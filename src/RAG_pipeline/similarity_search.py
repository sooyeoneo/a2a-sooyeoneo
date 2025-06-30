"""
similarity_search.py
유사도 기반 검색 모듈
- 쿼리 임베딩 및 유사도 검색
- 필드별 데이터 추출
- 검색 결과 랭킹 및 필터링
"""
from typing import List, Dict, Any, Optional, Tuple
import re

from .embedding_manager import EmbeddingManager

class SimilaritySearch:
    """유사도 기반 검색을 담당하는 클래스"""
    
    def __init__(self, embedding_manager: EmbeddingManager):
        self.embedding_manager = embedding_manager
        self.similarity_threshold = 0.7  # 유사도 임계값
        
    def search_company_info(self, query: str, collection_name: str = "company_data", 
                           top_k: int = 5) -> List[Dict[str, Any]]:
        """
        회사 정보를 검색합니다.
        
        Args:
            query: 검색 쿼리
            collection_name: 벡터 스토어 컬렉션 이름
            top_k: 반환할 상위 k개 결과
            
        Returns:
            List[Dict]: 검색 결과 리스트
        """
        # 벡터 스토어 로드
        vector_store = self.embedding_manager.load_vector_store(collection_name)
        if not vector_store:
            print(f"❌ 벡터 스토어를 찾을 수 없습니다: {collection_name}")
            return []
        
        # 쿼리 임베딩
        query_embedding = self.embedding_manager.get_single_embedding(query)
        
        # 유사도 검색
        similar_chunks = self.embedding_manager.find_similar_chunks(
            query_embedding, 
            vector_store["embeddings"], 
            top_k * 2  # 필터링을 위해 더 많은 결과 가져오기
        )
        
        # 결과 필터링 및 포맷팅
        results = []
        for chunk_idx, similarity in similar_chunks:
            if similarity >= self.similarity_threshold:
                chunk = vector_store["chunks"][chunk_idx]
                result = {
                    "content": chunk["content"],
                    "similarity": similarity,
                    "field_type": chunk.get("field_type", "unknown"),
                    "company_name": chunk.get("company_name", ""),
                    "chunk_id": chunk.get("chunk_id", chunk_idx),
                    "metadata": {k: v for k, v in chunk.items() 
                               if k not in ["content", "field_type", "company_name", "chunk_id"]}
                }
                results.append(result)
        
        # 유사도 기준으로 정렬
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results[:top_k]
    
    def extract_field_data(self, search_results: List[Dict[str, Any]], 
                          field_name: str) -> Optional[str]:
        """
        검색 결과에서 특정 필드의 데이터를 추출합니다.
        
        Args:
            search_results: 검색 결과 리스트
            field_name: 추출할 필드명
            
        Returns:
            Optional[str]: 추출된 데이터
        """
        if not search_results:
            return None
        
        # 필드별 추출 로직
        field_patterns = {
            "대표자": [
                r"대표자:\s*([^\n]+)",
                r"CEO:\s*([^\n]+)",
                r"대표:\s*([^\n]+)"
            ],
            "매출액": [
                r"매출액:\s*([^\n]+)",
                r"최신 매출액:\s*([^\n]+)",
                r"매출:\s*([^\n]+)"
            ],
            "직원수": [
                r"직원수:\s*([^\n]+)",
                r"직원:\s*([^\n]+)",
                r"인원:\s*([^\n]+)"
            ],
            "회사명": [
                r"회사명:\s*([^\n]+)",
                r"기업명:\s*([^\n]+)",
                r"회사:\s*([^\n]+)"
            ],
            "설립년도": [
                r"설립년도:\s*([^\n]+)",
                r"설립:\s*([^\n]+)",
                r"창립:\s*([^\n]+)"
            ]
        }
        
        patterns = field_patterns.get(field_name, [])
        if not patterns:
            return None
        
        # 가장 유사도가 높은 결과에서 추출
        for result in search_results:
            content = result["content"]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    extracted_value = match.group(1).strip()
                    if extracted_value and extracted_value != "정보 없음":
                        return extracted_value
        
        return None
    
    def search_and_extract(self, query: str, field_name: str, 
                          collection_name: str = "company_data") -> Dict[str, Any]:
        """
        검색과 데이터 추출을 한번에 수행합니다.
        
        Args:
            query: 검색 쿼리
            field_name: 추출할 필드명
            collection_name: 벡터 스토어 컬렉션 이름
            
        Returns:
            Dict: 검색 및 추출 결과
        """
        # 검색 수행
        search_results = self.search_company_info(query, collection_name)
        
        # 데이터 추출
        extracted_data = self.extract_field_data(search_results, field_name)
        
        # 결과 구성
        result = {
            "query": query,
            "field_name": field_name,
            "extracted_data": extracted_data,
            "search_results": search_results,
            "confidence": search_results[0]["similarity"] if search_results else 0.0,
            "found": extracted_data is not None
        }
        
        return result
    
    def batch_search(self, queries: List[Dict[str, str]], 
                     collection_name: str = "company_data") -> List[Dict[str, Any]]:
        """
        여러 쿼리를 일괄 처리합니다.
        
        Args:
            queries: 쿼리 리스트 [{"query": "...", "field": "..."}]
            collection_name: 벡터 스토어 컬렉션 이름
            
        Returns:
            List[Dict]: 일괄 처리 결과
        """
        results = []
        for query_info in queries:
            result = self.search_and_extract(
                query_info["query"], 
                query_info["field"], 
                collection_name
            )
            results.append(result)
        
        return results
    
    def get_search_stats(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        검색 결과 통계를 반환합니다.
        
        Args:
            search_results: 검색 결과 리스트
            
        Returns:
            Dict: 검색 통계
        """
        if not search_results:
            return {
                "total_results": 0,
                "avg_similarity": 0.0,
                "max_similarity": 0.0,
                "field_types": {},
                "companies": set()
            }
        
        similarities = [r["similarity"] for r in search_results]
        field_types = {}
        companies = set()
        
        for result in search_results:
            field_type = result.get("field_type", "unknown")
            field_types[field_type] = field_types.get(field_type, 0) + 1
            
            company_name = result.get("company_name", "")
            if company_name:
                companies.add(company_name)
        
        return {
            "total_results": len(search_results),
            "avg_similarity": sum(similarities) / len(similarities),
            "max_similarity": max(similarities),
            "min_similarity": min(similarities),
            "field_types": field_types,
            "companies": list(companies)
        } 