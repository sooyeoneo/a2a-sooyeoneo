"""
document_loader.py
다양한 소스에서 문서를 로드하는 모듈
- 웹 크롤링
- API 호출
- 파일 로딩
- 데이터베이스 연결
"""
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import json
import os
from datetime import datetime
import time

class DocumentLoader:
    """문서 로딩을 담당하는 클래스"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def load_from_web(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """
        웹 페이지에서 문서를 로드합니다.
        
        Args:
            url: 크롤링할 URL
            timeout: 요청 타임아웃 (초)
            
        Returns:
            Dict: 로드된 문서 정보
        """
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            return {
                "url": url,
                "content": response.text,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "timestamp": datetime.now().isoformat(),
                "source_type": "web"
            }
        except Exception as e:
            return {
                "url": url,
                "content": "",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "source_type": "web"
            }
    
    def load_from_api(self, api_url: str, params: Optional[Dict] = None, 
                     headers: Optional[Dict] = None) -> Dict[str, Any]:
        """
        API에서 데이터를 로드합니다.
        
        Args:
            api_url: API 엔드포인트 URL
            params: 쿼리 파라미터
            headers: 요청 헤더
            
        Returns:
            Dict: API 응답 데이터
        """
        try:
            response = self.session.get(api_url, params=params, headers=headers)
            response.raise_for_status()
            
            return {
                "url": api_url,
                "content": response.json(),
                "status_code": response.status_code,
                "timestamp": datetime.now().isoformat(),
                "source_type": "api"
            }
        except Exception as e:
            return {
                "url": api_url,
                "content": {},
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "source_type": "api"
            }
    
    def load_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        파일에서 문서를 로드합니다.
        
        Args:
            file_path: 파일 경로
            
        Returns:
            Dict: 파일 내용
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "file_path": file_path,
                "content": content,
                "file_size": len(content),
                "timestamp": datetime.now().isoformat(),
                "source_type": "file"
            }
        except Exception as e:
            return {
                "file_path": file_path,
                "content": "",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "source_type": "file"
            }
    
    def load_company_data(self, company_name: str) -> List[Dict[str, Any]]:
        """
        특정 회사에 대한 데이터를 다양한 소스에서 로드합니다.
        
        Args:
            company_name: 회사명
            
        Returns:
            List[Dict]: 로드된 문서 리스트
        """
        documents = []
        
        # 1. 웹 검색 결과 로드
        search_urls = [
            f"https://www.google.com/search?q={company_name}+회사+정보",
            f"https://www.naver.com/search.naver?query={company_name}+기업+분석"
        ]
        
        for url in search_urls:
            doc = self.load_from_web(url)
            if doc.get("content"):
                documents.append(doc)
            time.sleep(1)  # 크롤링 간격 조절
        
        # 2. API 데이터 로드 (예: 기업 정보 API)
        api_urls = [
            f"https://api.example.com/company/{company_name}",
            f"https://api.finance.example.com/company/{company_name}/financials"
        ]
        
        for api_url in api_urls:
            doc = self.load_from_api(api_url)
            if doc.get("content"):
                documents.append(doc)
        
        return documents
    
    def batch_load(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        여러 소스에서 배치로 문서를 로드합니다.
        
        Args:
            sources: 소스 정보 리스트
                [{"type": "web", "url": "..."}, {"type": "file", "path": "..."}]
                
        Returns:
            List[Dict]: 로드된 문서 리스트
        """
        documents = []
        
        for source in sources:
            source_type = source.get("type", "")
            
            if source_type == "web":
                doc = self.load_from_web(source["url"])
            elif source_type == "api":
                doc = self.load_from_api(source["url"], source.get("params"), source.get("headers"))
            elif source_type == "file":
                doc = self.load_from_file(source["path"])
            else:
                continue
                
            if doc.get("content"):
                documents.append(doc)
        
        return documents

# 사용 예시RA
if __name__ == "__main__":
    loader = DocumentLoader()
    
    # 단일 웹 페이지 로드
    doc = loader.load_from_web("https://www.example.com")
    print(f"웹 문서 로드: {len(doc.get('content', ''))} 문자")
    
    # 회사 데이터 로드
    company_docs = loader.load_company_data("삼성전자")
    print(f"회사 문서 {len(company_docs)}개 로드 완료") 