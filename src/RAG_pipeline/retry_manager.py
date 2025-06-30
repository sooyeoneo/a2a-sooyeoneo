"""
retry_manager.py
LLM 재호출 및 Web Search 관리 모듈
- 검증 실패 시 LLM 재호출
- Web Search API 연동
- Function Calling 활용
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class RetryManager:
    """LLM 재호출 및 Web Search를 담당하는 클래스"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_client = None
        self.max_retries = 3
        self.retry_delay = 1  # 초
        
        if OPENAI_AVAILABLE:
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                print("✅ OpenAI 클라이언트 초기화 완료")
            else:
                print("⚠️ OpenAI API 키가 설정되지 않았습니다.")
        else:
            print("⚠️ OpenAI 라이브러리가 설치되지 않았습니다.")
    
    def retry_with_llm(self, company_name: str, field_name: str, 
                       original_query: str, validation_error: str) -> Dict[str, Any]:
        """
        LLM을 사용하여 데이터를 재검색합니다.
        
        Args:
            company_name: 회사명
            field_name: 필드명
            original_query: 원본 쿼리
            validation_error: 검증 오류 메시지
            
        Returns:
            Dict: 재검색 결과
        """
        if not self.openai_client:
            return {
                "success": False,
                "error": "OpenAI 클라이언트가 초기화되지 않았습니다.",
                "retry_count": 0
            }
        
        # 재검색 프롬프트
        retry_prompt = f"""
        다음 회사 정보를 정확하게 찾아주세요:
        
        회사명: {company_name}
        찾고자 하는 정보: {field_name}
        원본 쿼리: {original_query}
        검증 오류: {validation_error}
        
        위 정보를 바탕으로 정확한 {field_name} 정보를 찾아주세요.
        만약 정보를 찾을 수 없다면 "정보 없음"으로 응답하세요.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 정확한 회사 정보를 제공하는 전문가입니다. JSON 형식으로 응답해주세요."},
                    {"role": "user", "content": retry_prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            # 응답 파싱
            content = response.choices[0].message.content
            if content is None:
                return {
                    "success": False,
                    "error": "응답이 없습니다.",
                    "retry_count": 1
                }
            
            # JSON 응답 파싱 시도
            try:
                import json
                import re
                
                # JSON 부분 추출
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    args = json.loads(json_match.group())
                    return {
                        "success": True,
                        "extracted_data": args.get("field_value"),
                        "confidence": args.get("confidence", 0.0),
                        "source": args.get("source", "LLM 재검색"),
                        "retry_count": 1,
                        "retried_at": datetime.now().isoformat()
                    }
            except (json.JSONDecodeError, KeyError):
                pass
            
            # 일반 텍스트 응답 처리
            content = content.strip()
            if "정보 없음" in content or "확인할 수 없" in content:
                return {
                    "success": True,
                    "extracted_data": None,
                    "confidence": 0.0,
                    "source": "LLM 재검색",
                    "retry_count": 1,
                    "retried_at": datetime.now().isoformat()
                }
            
            return {
                "success": True,
                "extracted_data": content,
                "confidence": 0.7,
                "source": "LLM 재검색",
                "retry_count": 1,
                "retried_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"LLM 재호출 실패: {str(e)}",
                "retry_count": 1
            }
    
    def retry_with_web_search(self, company_name: str, field_name: str, 
                             original_query: str) -> Dict[str, Any]:
        """
        Web Search를 사용하여 데이터를 재검색합니다.
        
        Args:
            company_name: 회사명
            field_name: 필드명
            original_query: 원본 쿼리
            
        Returns:
            Dict: Web Search 결과
        """
        # 실제로는 Web Search API를 연동해야 함
        # 여기서는 시뮬레이션으로 구현
        
        search_query = f"{company_name} {field_name}"
        
        # 시뮬레이션된 Web Search 결과
        mock_results = {
            "무신사": {
                "대표자": "박준모",
                "매출액": "1조 1,005억원",
                "직원수": "510명",
                "설립년도": "2012"
            }
        }
        
        company_data = mock_results.get(company_name, {})
        field_value = company_data.get(field_name, "정보 없음")
        
        return {
            "success": True,
            "extracted_data": field_value if field_value != "정보 없음" else None,
            "confidence": 0.9 if field_value != "정보 없음" else 0.0,
            "source": "Web Search",
            "search_query": search_query,
            "retry_count": 1,
            "retried_at": datetime.now().isoformat()
        }
    
    def retry_with_enhanced_prompt(self, company_name: str, field_name: str, 
                                  original_query: str, context: str) -> Dict[str, Any]:
        """
        향상된 프롬프트로 LLM을 재호출합니다.
        
        Args:
            company_name: 회사명
            field_name: 필드명
            original_query: 원본 쿼리
            context: 추가 컨텍스트
            
        Returns:
            Dict: 재검색 결과
        """
        if not self.openai_client:
            return {
                "success": False,
                "error": "OpenAI 클라이언트가 초기화되지 않았습니다.",
                "retry_count": 0
            }
        
        enhanced_prompt = f"""
        다음 회사 정보를 정확하게 찾아주세요. 
        기존 정보와 컨텍스트를 참고하여 가장 정확한 답변을 제공해주세요.
        
        회사명: {company_name}
        찾고자 하는 정보: {field_name}
        원본 쿼리: {original_query}
        추가 컨텍스트: {context}
        
        주의사항:
        1. 정확한 정보만 제공하세요
        2. 확실하지 않은 정보는 "정보 없음"으로 응답하세요
        3. 숫자 정보는 정확한 단위와 함께 제공하세요
        4. 한국어로 응답하세요
        
        {field_name} 정보를 찾아서 간단명료하게 답변해주세요.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 정확한 회사 정보를 제공하는 전문가입니다. 확실하지 않은 정보는 제공하지 마세요."},
                    {"role": "user", "content": enhanced_prompt}
                ],
                temperature=0.1,  # 낮은 temperature로 일관성 확보
                max_tokens=100
            )
            
            extracted_data = response.choices[0].message.content
            if extracted_data is None:
                return {
                    "success": True,
                    "extracted_data": None,
                    "confidence": 0.0,
                    "source": "LLM 향상된 프롬프트",
                    "retry_count": 1,
                    "retried_at": datetime.now().isoformat()
                }
            
            extracted_data = extracted_data.strip()
            
            # "정보 없음" 체크
            if "정보 없음" in extracted_data or "확인할 수 없" in extracted_data:
                return {
                    "success": True,
                    "extracted_data": None,
                    "confidence": 0.0,
                    "source": "LLM 향상된 프롬프트",
                    "retry_count": 1,
                    "retried_at": datetime.now().isoformat()
                }
            
            return {
                "success": True,
                "extracted_data": extracted_data,
                "confidence": 0.8,
                "source": "LLM 향상된 프롬프트",
                "retry_count": 1,
                "retried_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"향상된 프롬프트 재호출 실패: {str(e)}",
                "retry_count": 1
            }
    
    def execute_retry_strategy(self, company_name: str, field_name: str, 
                              original_query: str, validation_error: str,
                              context: str = "") -> Dict[str, Any]:
        """
        재시도 전략을 실행합니다.
        
        Args:
            company_name: 회사명
            field_name: 필드명
            original_query: 원본 쿼리
            validation_error: 검증 오류
            context: 추가 컨텍스트
            
        Returns:
            Dict: 재시도 결과
        """
        retry_results = []
        
        # 1단계: 향상된 프롬프트로 재시도
        result1 = self.retry_with_enhanced_prompt(company_name, field_name, original_query, context)
        retry_results.append(result1)
        
        if result1["success"] and result1["extracted_data"]:
            return {
                "final_result": result1,
                "retry_history": retry_results,
                "strategy": "enhanced_prompt"
            }
        
        # 2단계: Function Calling으로 재시도
        result2 = self.retry_with_llm(company_name, field_name, original_query, validation_error)
        retry_results.append(result2)
        
        if result2["success"] and result2["extracted_data"]:
            return {
                "final_result": result2,
                "retry_history": retry_results,
                "strategy": "function_calling"
            }
        
        # 3단계: Web Search로 재시도
        result3 = self.retry_with_web_search(company_name, field_name, original_query)
        retry_results.append(result3)
        
        return {
            "final_result": result3,
            "retry_history": retry_results,
            "strategy": "web_search"
        }
    
    def get_retry_summary(self, retry_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        재시도 결과 요약을 반환합니다.
        
        Args:
            retry_results: 재시도 결과
            
        Returns:
            Dict: 재시도 요약
        """
        retry_history = retry_results.get("retry_history", [])
        final_result = retry_results.get("final_result", {})
        
        total_retries = len(retry_history)
        successful_retries = sum(1 for r in retry_history if r["success"])
        final_success = final_result.get("success", False)
        final_data = final_result.get("extracted_data")
        
        return {
            "total_retries": total_retries,
            "successful_retries": successful_retries,
            "final_success": final_success,
            "final_data": final_data,
            "strategy_used": retry_results.get("strategy", "none"),
            "retry_efficiency": successful_retries / total_retries if total_retries > 0 else 0
        } 