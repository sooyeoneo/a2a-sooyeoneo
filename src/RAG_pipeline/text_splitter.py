"""
text_splitter.py
문서를 청크로 분할하는 모듈
- 다양한 분할 전략 지원
- 중복 제거 및 오버랩 설정
- 청크 품질 최적화
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib

@dataclass
class ChunkConfig:
    """청크 분할 설정"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separator: str = "\n\n"
    min_chunk_size: int = 100
    max_chunk_size: int = 2000

class TextSplitter:
    """텍스트 분할을 담당하는 클래스"""
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
    
    def split_by_sentences(self, text: str) -> List[str]:
        """
        문장 단위로 텍스트를 분할합니다.
        
        Args:
            text: 분할할 텍스트
            
        Returns:
            List[str]: 문장 리스트
        """
        # 한국어 문장 구분 패턴
        sentence_pattern = r'[.!?。！？]\s*'
        sentences = re.split(sentence_pattern, text)
        
        # 빈 문장 제거 및 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def split_by_paragraphs(self, text: str) -> List[str]:
        """
        단락 단위로 텍스트를 분할합니다.
        
        Args:
            text: 분할할 텍스트
            
        Returns:
            List[str]: 단락 리스트
        """
        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return paragraphs
    
    def split_by_tokens(self, text: str, chunk_size: Optional[int] = None) -> List[str]:
        """
        토큰 수 기준으로 텍스트를 분할합니다.
        
        Args:
            text: 분할할 텍스트
            chunk_size: 청크 크기 (토큰 수)
            
        Returns:
            List[str]: 청크 리스트
        """
        chunk_size = chunk_size or self.config.chunk_size
        
        # 간단한 토큰화 (공백 기준)
        tokens = text.split()
        chunks = []
        
        for i in range(0, len(tokens), chunk_size - self.config.chunk_overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = ' '.join(chunk_tokens)
            
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(chunk_text)
        
        return chunks
    
    def split_by_characters(self, text: str, chunk_size: Optional[int] = None) -> List[str]:
        """
        문자 수 기준으로 텍스트를 분할합니다.
        
        Args:
            text: 분할할 텍스트
            chunk_size: 청크 크기 (문자 수)
            
        Returns:
            List[str]: 청크 리스트
        """
        chunk_size = chunk_size or self.config.chunk_size
        chunks = []
        
        for i in range(0, len(text), chunk_size - self.config.chunk_overlap):
            chunk = text[i:i + chunk_size]
            
            if len(chunk) >= self.config.min_chunk_size:
                chunks.append(chunk)
        
        return chunks
    
    def split_recursive(self, text: str, separators: Optional[List[str]] = None) -> List[str]:
        """
        재귀적으로 텍스트를 분할합니다.
        
        Args:
            text: 분할할 텍스트
            separators: 구분자 리스트 (우선순위 순)
            
        Returns:
            List[str]: 청크 리스트
        """
        if separators is None:
            separators = ["\n\n", "\n", " ", ""]
        
        if len(separators) == 0:
            return [text]
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        if separator == "":
            return [text]
        
        splits = text.split(separator)
        
        if len(splits) == 1:
            return self.split_recursive(text, remaining_separators)
        
        chunks = []
        for split in splits:
            if len(split) >= self.config.min_chunk_size:
                if len(split) <= self.config.max_chunk_size:
                    chunks.append(split)
                else:
                    chunks.extend(self.split_recursive(split, remaining_separators))
        
        return chunks
    
    def remove_duplicates(self, chunks: List[str]) -> List[str]:
        """
        중복된 청크를 제거합니다.
        
        Args:
            chunks: 청크 리스트
            
        Returns:
            List[str]: 중복 제거된 청크 리스트
        """
        seen = set()
        unique_chunks = []
        
        for chunk in chunks:
            # 청크의 해시값으로 중복 체크
            chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
            
            if chunk_hash not in seen:
                seen.add(chunk_hash)
                unique_chunks.append(chunk)
        
        return unique_chunks
    
    def add_metadata(self, chunks: List[str], source_info: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        청크에 메타데이터를 추가합니다.
        
        Args:
            chunks: 청크 리스트
            source_info: 소스 정보
            
        Returns:
            List[Dict]: 메타데이터가 포함된 청크 리스트
        """
        chunk_docs = []
        
        for i, chunk in enumerate(chunks):
            chunk_doc = {
                "content": chunk,
                "chunk_id": i,
                "chunk_size": len(chunk),
                "word_count": len(chunk.split()),
                "timestamp": source_info.get("timestamp") if source_info else None,
                "source": source_info.get("source_type") if source_info else None,
                "url": source_info.get("url") if source_info else None
            }
            chunk_docs.append(chunk_doc)
        
        return chunk_docs
    
    def split_document(self, document: Dict[str, Any], strategy: str = "recursive") -> List[Dict[str, Any]]:
        """
        문서를 분할 전략에 따라 청크로 나눕니다.
        
        Args:
            document: 분할할 문서
            strategy: 분할 전략 ("sentences", "paragraphs", "tokens", "characters", "recursive")
            
        Returns:
            List[Dict]: 청크 리스트 (메타데이터 포함)
        """
        content = document.get("content", "")
        
        if strategy == "sentences":
            chunks = self.split_by_sentences(content)
        elif strategy == "paragraphs":
            chunks = self.split_by_paragraphs(content)
        elif strategy == "tokens":
            chunks = self.split_by_tokens(content)
        elif strategy == "characters":
            chunks = self.split_by_characters(content)
        else:  # recursive
            chunks = self.split_recursive(content)
        
        # 중복 제거
        chunks = self.remove_duplicates(chunks)
        
        # 메타데이터 추가
        chunk_docs = self.add_metadata(chunks, document)
        
        return chunk_docs
    
    def batch_split(self, documents: List[Dict[str, Any]], strategy: str = "recursive") -> List[Dict[str, Any]]:
        """
        여러 문서를 배치로 분할합니다.
        
        Args:
            documents: 문서 리스트
            strategy: 분할 전략
            
        Returns:
            List[Dict]: 모든 청크 리스트
        """
        all_chunks = []
        
        for document in documents:
            chunks = self.split_document(document, strategy)
            all_chunks.extend(chunks)
        
        return all_chunks

# 사용 예시
if __name__ == "__main__":
    # 설정
    config = ChunkConfig(
        chunk_size=500,
        chunk_overlap=50,
        min_chunk_size=100,
        max_chunk_size=1000
    )
    
    splitter = TextSplitter(config)
    
    # 테스트 텍스트
    test_text = """
    삼성전자는 대한민국의 대표적인 전자기업입니다.
    
    삼성전자는 반도체, 디스플레이, 모바일 등 다양한 분야에서 세계적인 경쟁력을 보유하고 있습니다.
    
    2023년 기준으로 삼성전자의 매출은 약 300조원에 달하며, 전 세계적으로 30만명 이상의 직원을 고용하고 있습니다.
    """
    
    # 다양한 전략으로 분할 테스트
    strategies = ["sentences", "paragraphs", "tokens", "recursive"]
    
    for strategy in strategies:
        chunks = splitter.split_document({"content": test_text}, strategy)
        print(f"\n{strategy} 전략으로 분할:")
        for i, chunk in enumerate(chunks):
            print(f"  청크 {i+1}: {chunk['content'][:50]}...") 