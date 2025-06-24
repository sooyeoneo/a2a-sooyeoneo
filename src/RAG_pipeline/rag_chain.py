"""
rag_chain.py
RAG(Retrieval-Augmented Generation) 체인 통합 모듈
- 문서 로딩 → 분할 → 임베딩 → 검색 → 프롬프트 → LLM → 할루시네이션 감지
"""
from typing import List, Dict, Any, Optional, Tuple
import time
from datetime import datetime
from dataclasses import dataclass

# 기존 모듈들 import
from rag_pipeline.document_loader import DocumentLoader
from rag_pipeline.text_splitter import TextSplitter, ChunkConfig
from rag_pipeline.embedding_manager import EmbeddingManager
from rag_pipeline.prompt_manager import PromptManager, OutputParser, HallucinationDetector, AnswerType

try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

@dataclass
class RAGConfig:
    """RAG 체인 설정"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    confidence_threshold: float = 0.7
    max_context_length: int = 4000
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model: str = "gpt-4o"

class RAGChain:
    """RAG 체인을 관리하는 클래스"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        
        # 컴포넌트 초기화
        self.document_loader = DocumentLoader()
        self.text_splitter = TextSplitter(ChunkConfig(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        ))
        self.embedding_manager = EmbeddingManager(self.config.embedding_model)
        self.prompt_manager = PromptManager()
        self.output_parser = OutputParser()
        self.hallucination_detector = HallucinationDetector(self.config.confidence_threshold)
        
        # LLM 초기화
        self.llm = None
        if LLM_AVAILABLE:
            try:
                self.llm = ChatOpenAI(model=self.config.llm_model)
                print(f"✅ LLM 초기화 완료: {self.config.llm_model}")
            except Exception as e:
                print(f"❌ LLM 초기화 실패: {e}")
    
    def process_company_query(self, company_name: str, question: str) -> Dict[str, Any]:
        """
        회사 관련 질문을 처리하는 메인 파이프라인
        
        Args:
            company_name: 회사명
            question: 질문
            
        Returns:
            Dict: 처리 결과
        """
        start_time = time.time()
        
        try:
            # 1. 문서 로딩
            print(f"📥 문서 로딩 중: {company_name}")
            documents = self.document_loader.load_company_data(company_name)
            
            if not documents:
                return self._create_error_response("문서를 로드할 수 없습니다.")
            
            # 2. 텍스트 분할
            print(f"✂️ 텍스트 분할 중: {len(documents)}개 문서")
            chunks = self.text_splitter.batch_split(documents, strategy="recursive")
            
            if not chunks:
                return self._create_error_response("텍스트 분할에 실패했습니다.")
            
            # 3. 임베딩 생성 및 벡터 스토어 생성
            print(f"🔢 임베딩 생성 중: {len(chunks)}개 청크")
            collection_name = f"{company_name}_{int(time.time())}"
            vector_store = self.embedding_manager.create_vector_store(chunks, collection_name)
            
            # 4. 유사도 검색
            print(f"🔍 유사도 검색 중: '{question}'")
            similar_chunks = self.embedding_manager.search_similar(
                question, collection_name, self.config.top_k
            )
            
            if not similar_chunks:
                return self._create_not_found_response(question)
            
            # 5. 컨텍스트 구성
            context = [chunk["content"] for chunk in similar_chunks]
            context_text = "\n\n".join(context)
            
            # 6. 프롬프트 생성
            prompt = self.prompt_manager.create_rag_prompt(question, context, company_name)
            
            # 7. LLM 호출
            if not self.llm:
                return self._create_error_response("LLM이 초기화되지 않았습니다.")
            
            print(f"🤖 LLM 응답 생성 중...")
            llm_response = self.llm.invoke(prompt)
            answer = str(llm_response.content)
            
            # 8. 응답 분석
            confidence = self.output_parser.parse_confidence_score(answer)
            answer_type = self.output_parser.parse_answer_type(answer)
            citations = self.output_parser.extract_citations(answer)
            
            # 9. 할루시네이션 감지
            detection = self.hallucination_detector.detect_hallucination(
                answer, context_text, confidence
            )
            
            # 10. 결과 구성
            processing_time = time.time() - start_time
            
            result = {
                "success": True,
                "company_name": company_name,
                "question": question,
                "answer": answer,
                "confidence_score": confidence,
                "answer_type": answer_type.value,
                "citations": citations,
                "hallucination_detected": detection["is_hallucination"],
                "hallucination_risk": detection["risk_level"],
                "context_chunks": len(similar_chunks),
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "chunk_count": len(chunks),
                    "embedding_model": self.config.embedding_model,
                    "llm_model": self.config.llm_model,
                    "top_k": self.config.top_k
                }
            }
            
            # 할루시네이션 감지 시 수정 제안
            if detection["is_hallucination"]:
                correction = self.hallucination_detector.suggest_correction(
                    answer, context_text, detection
                )
                result["correction_suggestion"] = correction
            
            print(f"✅ 처리 완료: {processing_time:.2f}초")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            return self._create_error_response(f"처리 중 오류 발생: {str(e)}", processing_time)
    
    def generate_company_report(self, company_name: str, 
                              fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        회사 리포트를 생성하는 파이프라인
        
        Args:
            company_name: 회사명
            fields: 생성할 필드 리스트
            
        Returns:
            Dict: 리포트 생성 결과
        """
        if fields is None:
            fields = [
                "company_summary", "industry_keywords", "target_customers", 
                "financial_info", "recent_trends", "competitors", 
                "strengths", "risk_factors", "key_executives"
            ]
        
        start_time = time.time()
        
        try:
            # 1. 문서 로딩
            print(f"📥 회사 데이터 로딩 중: {company_name}")
            documents = self.document_loader.load_company_data(company_name)
            
            if not documents:
                return self._create_error_response("회사 데이터를 로드할 수 없습니다.")
            
            # 2. 텍스트 분할
            chunks = self.text_splitter.batch_split(documents, strategy="recursive")
            
            # 3. 임베딩 생성
            collection_name = f"{company_name}_report_{int(time.time())}"
            vector_store = self.embedding_manager.create_vector_store(chunks, collection_name)
            
            # 4. 각 필드별 정보 추출
            report_data: Dict[str, Any] = {"company_name": company_name}
            
            for field in fields:
                print(f"📊 {field} 정보 추출 중...")
                
                # 필드별 검색 쿼리 생성
                field_queries = {
                    "company_summary": f"{company_name} 회사 개요 요약",
                    "industry_keywords": f"{company_name} 주요 산업 분야",
                    "target_customers": f"{company_name} 타겟 고객",
                    "financial_info": f"{company_name} 재무 정보 매출",
                    "recent_trends": f"{company_name} 최신 동향 뉴스",
                    "competitors": f"{company_name} 경쟁사",
                    "strengths": f"{company_name} 강점 차별점",
                    "risk_factors": f"{company_name} 리스크 위험요인",
                    "key_executives": f"{company_name} 대표자 CEO"
                }
                
                query = field_queries.get(field, f"{company_name} {field}")
                similar_chunks = self.embedding_manager.search_similar(
                    query, collection_name, top_k=3
                )
                
                if similar_chunks:
                    context = "\n\n".join([chunk["content"] for chunk in similar_chunks])
                    
                    # 필드별 프롬프트 생성
                    prompt = self.prompt_manager.create_company_report_prompt(
                        company_name, field, context
                    )
                    
                    # LLM 호출
                    if self.llm:
                        try:
                            llm_response = self.llm.invoke(prompt)
                            response_text = str(llm_response.content)
                            
                            # JSON 파싱
                            parsed_data = self.output_parser.parse_json_response(response_text)
                            if parsed_data and field in parsed_data:
                                report_data[field] = parsed_data[field]
                            else:
                                report_data[field] = None
                        except Exception as e:
                            print(f"❌ {field} 처리 실패: {e}")
                            report_data[field] = None
                    else:
                        report_data[field] = None
                else:
                    report_data[field] = None
            
            processing_time = time.time() - start_time
            
            result = {
                "success": True,
                "company_name": company_name,
                "report_data": report_data,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "fields_processed": len(fields),
                "fields_with_data": sum(1 for v in report_data.values() if v is not None)
            }
            
            print(f"✅ 리포트 생성 완료: {processing_time:.2f}초")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            return self._create_error_response(f"리포트 생성 중 오류: {str(e)}", processing_time)
    
    def _create_error_response(self, error_message: str, processing_time: float = 0.0) -> Dict[str, Any]:
        """오류 응답 생성"""
        return {
            "success": False,
            "error": error_message,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_not_found_response(self, question: str) -> Dict[str, Any]:
        """정보 없음 응답 생성"""
        return {
            "success": True,
            "question": question,
            "answer": "제공된 정보에서 해당 내용을 찾을 수 없습니다.",
            "confidence_score": 0.0,
            "answer_type": AnswerType.NOT_FOUND.value,
            "citations": [],
            "hallucination_detected": False,
            "processing_time": 0.0,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_chain_stats(self) -> Dict[str, Any]:
        """체인 통계 정보 반환"""
        return {
            "embedding_model": self.config.embedding_model,
            "llm_model": self.config.llm_model,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "top_k": self.config.top_k,
            "confidence_threshold": self.config.confidence_threshold,
            "llm_available": self.llm is not None
        }

# 사용 예시
if __name__ == "__main__":
    # RAG 체인 초기화
    rag_chain = RAGChain()
    
    # 회사 질문 처리 테스트
    company_name = "삼성전자"
    question = "삼성전자의 2023년 매출은?"
    
    print(f"🔍 질문 처리: {question}")
    result = rag_chain.process_company_query(company_name, question)
    
    if result["success"]:
        print(f"✅ 답변: {result['answer']}")
        print(f"📊 신뢰도: {result['confidence_score']:.3f}")
        print(f"⚠️ 할루시네이션: {result['hallucination_detected']}")
    else:
        print(f"❌ 오류: {result['error']}")
    
    # 체인 통계
    stats = rag_chain.get_chain_stats()
    print(f"\n 체인 통계: {stats}") 