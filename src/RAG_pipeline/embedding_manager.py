"""
embedding_manager.py
임베딩 관리를 담당하는 모듈
- 다양한 임베딩 모델 지원
- 벡터 저장 및 검색
- 유사도 계산 최적화
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, cast
import pickle
import os
from datetime import datetime
import json

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class EmbeddingManager:
    """임베딩 관리를 담당하는 클래스"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", 
                 cache_dir: str = "./embeddings_cache"):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.embeddings_model = None
        self.vector_store = {}
        
        # 캐시 디렉토리 생성
        os.makedirs(cache_dir, exist_ok=True)
        
        # 임베딩 모델 초기화
        self._initialize_model()
    
    def _initialize_model(self):
        """임베딩 모델을 초기화합니다."""
        try:
            if "sentence-transformers" in self.model_name and SENTENCE_TRANSFORMERS_AVAILABLE:
                self.embeddings_model = SentenceTransformer(self.model_name)
                print(f"✅ Sentence Transformers 모델 로드: {self.model_name}")
            elif "text-embedding" in self.model_name and OPENAI_AVAILABLE:
                self.embeddings_model = OpenAIEmbeddings(model=self.model_name)
                print(f"✅ OpenAI 임베딩 모델 로드: {self.model_name}")
            else:
                raise ValueError(f"지원하지 않는 모델: {self.model_name}")
        except Exception as e:
            print(f"❌ 모델 초기화 실패: {e}")
            # 기본 모델로 폴백
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.embeddings_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                print("✅ 기본 모델로 폴백")
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 리스트를 임베딩으로 변환합니다.
        
        Args:
            texts: 임베딩할 텍스트 리스트
            
        Returns:
            List[List[float]]: 임베딩 벡터 리스트
        """
        if not self.embeddings_model:
            raise ValueError("임베딩 모델이 초기화되지 않았습니다.")
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE and isinstance(self.embeddings_model, SentenceTransformer):
                # Sentence Transformers
                model = cast(SentenceTransformer, self.embeddings_model)
                embeddings = model.encode(texts, convert_to_tensor=False)
                # numpy array일 경우 리스트로 변환
                if hasattr(embeddings, 'tolist'):
                    return embeddings.tolist()
                return list(embeddings)
            elif OPENAI_AVAILABLE and isinstance(self.embeddings_model, OpenAIEmbeddings):
                # OpenAI Embeddings
                embeddings = self.embeddings_model.embed_documents(texts)
                return embeddings
            else:
                raise ValueError("지원하지 않는 임베딩 모델입니다.")
        except Exception as e:
            print(f"❌ 임베딩 생성 실패: {e}")
            # 더미 임베딩 반환
            return [[0.0] * 384 for _ in texts]
    
    def get_single_embedding(self, text: str) -> List[float]:
        """
        단일 텍스트를 임베딩으로 변환합니다.
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            List[float]: 임베딩 벡터
        """
        return self.get_embeddings([text])[0]
    
    def calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        두 벡터 간의 코사인 유사도를 계산합니다.
        
        Args:
            vec1: 첫 번째 벡터
            vec2: 두 번째 벡터
            
        Returns:
            float: 코사인 유사도 (0~1)
        """
        arr1 = np.array(vec1)
        arr2 = np.array(vec2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        similarity = np.dot(arr1, arr2) / (norm1 * norm2)
        return float(similarity)
    
    def find_similar_chunks(self, query_embedding: List[float], 
                           chunk_embeddings: List[List[float]], 
                           top_k: int = 5) -> List[Tuple[int, float]]:
        """
        쿼리와 가장 유사한 청크들을 찾습니다.
        
        Args:
            query_embedding: 쿼리 임베딩
            chunk_embeddings: 청크 임베딩 리스트
            top_k: 반환할 상위 k개
            
        Returns:
            List[Tuple[int, float]]: (청크 인덱스, 유사도) 리스트
        """
        similarities = []
        
        for i, chunk_embedding in enumerate(chunk_embeddings):
            similarity = self.calculate_similarity(query_embedding, chunk_embedding)
            similarities.append((i, similarity))
        
        # 유사도 기준으로 정렬
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def create_vector_store(self, chunks: List[Dict[str, Any]], 
                           collection_name: str = "default") -> Dict[str, Any]:
        """
        청크들을 벡터 스토어에 저장합니다.
        
        Args:
            chunks: 청크 리스트 (메타데이터 포함)
            collection_name: 컬렉션 이름
            
        Returns:
            Dict: 벡터 스토어 정보
        """
        # 텍스트 추출
        texts = [chunk["content"] for chunk in chunks]
        
        # 임베딩 생성
        embeddings = self.get_embeddings(texts)
        
        # 벡터 스토어 구성
        vector_store = {
            "collection_name": collection_name,
            "chunks": chunks,
            "embeddings": embeddings,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "model_name": self.model_name,
                "chunk_count": len(chunks),
                "embedding_dimension": len(embeddings[0]) if embeddings else 0
            }
        }
        
        # 메모리에 저장
        self.vector_store[collection_name] = vector_store
        
        # 파일로 저장
        self._save_vector_store(vector_store, collection_name)
        
        return vector_store
    
    def _save_vector_store(self, vector_store: Dict[str, Any], collection_name: str):
        """벡터 스토어를 파일로 저장합니다."""
        try:
            file_path = os.path.join(self.cache_dir, f"{collection_name}.pkl")
            with open(file_path, 'wb') as f:
                pickle.dump(vector_store, f)
            print(f"✅ 벡터 스토어 저장: {file_path}")
        except Exception as e:
            print(f"❌ 벡터 스토어 저장 실패: {e}")
    
    def load_vector_store(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """벡터 스토어를 파일에서 로드합니다."""
        try:
            file_path = os.path.join(self.cache_dir, f"{collection_name}.pkl")
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    vector_store = pickle.load(f)
                self.vector_store[collection_name] = vector_store
                print(f"✅ 벡터 스토어 로드: {file_path}")
                return vector_store
        except Exception as e:
            print(f"❌ 벡터 스토어 로드 실패: {e}")
        
        return None
    
    def search_similar(self, query: str, collection_name: str = "default", 
                      top_k: int = 5) -> List[Dict[str, Any]]:
        """
        쿼리와 유사한 청크들을 검색합니다.
        
        Args:
            query: 검색 쿼리
            collection_name: 컬렉션 이름
            top_k: 반환할 상위 k개
            
        Returns:
            List[Dict]: 유사한 청크 리스트 (메타데이터 포함)
        """
        # 벡터 스토어 로드
        if collection_name not in self.vector_store:
            self.load_vector_store(collection_name)
        
        if collection_name not in self.vector_store:
            return []
        
        vector_store = self.vector_store[collection_name]
        chunks = vector_store["chunks"]
        embeddings = vector_store["embeddings"]
        
        # 쿼리 임베딩 생성
        query_embedding = self.get_single_embedding(query)
        
        # 유사한 청크 찾기
        similar_indices = self.find_similar_chunks(query_embedding, embeddings, top_k)
        
        # 결과 구성
        results = []
        for idx, similarity in similar_indices:
            chunk = chunks[idx].copy()
            chunk["similarity_score"] = similarity
            results.append(chunk)
        
        return results
    
    def get_embedding_stats(self, collection_name: str = "default") -> Dict[str, Any]:
        """임베딩 통계 정보를 반환합니다."""
        if collection_name not in self.vector_store:
            return {}
        
        vector_store = self.vector_store[collection_name]
        embeddings = vector_store["embeddings"]
        
        if not embeddings:
            return {}
        
        # 통계 계산
        embeddings_array = np.array(embeddings)
        stats = {
            "collection_name": collection_name,
            "chunk_count": len(embeddings),
            "embedding_dimension": embeddings_array.shape[1],
            "mean_norm": float(np.mean(np.linalg.norm(embeddings_array, axis=1))),
            "std_norm": float(np.std(np.linalg.norm(embeddings_array, axis=1))),
            "model_name": vector_store["metadata"]["model_name"]
        }
        
        return stats

# 사용 예시
if __name__ == "__main__":
    # 임베딩 매니저 초기화
    embedding_manager = EmbeddingManager()
    
    # 테스트 청크
    test_chunks = [
        {"content": "삼성전자는 대한민국의 대표적인 전자기업입니다.", "chunk_id": 0},
        {"content": "삼성전자는 반도체, 디스플레이, 모바일 분야에서 세계적인 경쟁력을 보유합니다.", "chunk_id": 1},
        {"content": "2023년 삼성전자의 매출은 약 300조원에 달합니다.", "chunk_id": 2}
    ]
    
    # 벡터 스토어 생성
    vector_store = embedding_manager.create_vector_store(test_chunks, "samsung_test")
    
    # 유사도 검색 테스트
    query = "삼성전자 매출"
    similar_chunks = embedding_manager.search_similar(query, "samsung_test", top_k=2)
    
    print(f"\n쿼리: '{query}'")
    for chunk in similar_chunks:
        print(f"유사도: {chunk['similarity_score']:.3f} - {chunk['content']}")
    
    # 통계 정보
    stats = embedding_manager.get_embedding_stats("samsung_test")
    print(f"\n임베딩 통계: {stats}") 