"""
prompt_manager.py
할루시네이션 방지를 위한 프롬프트 관리 모듈
- 정확도 향상 프롬프트 설계
- OutputParser 구조화
- "정보 없으면 모른다고 답변" 로직
"""
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import json
import re
from enum import Enum

class AnswerType(Enum):
    """답변 타입 정의"""
    CONFIRMED = "confirmed"      # 확실한 정보
    UNCERTAIN = "uncertain"      # 불확실한 정보
    NOT_FOUND = "not_found"      # 정보 없음
    ERROR = "error"              # 오류

@dataclass
class PromptConfig:
    """프롬프트 설정"""
    max_context_length: int = 4000
    confidence_threshold: float = 0.7
    require_citation: bool = True
    allow_uncertainty: bool = True
    language: str = "ko"

class PromptManager:
    """프롬프트 관리를 담당하는 클래스"""
    
    def __init__(self, config: Optional[PromptConfig] = None):
        self.config = config or PromptConfig()
    
    def create_base_prompt(self, task_description: str) -> str:
        """
        기본 프롬프트 템플릿을 생성합니다.
        
        Args:
            task_description: 작업 설명
            
        Returns:
            str: 기본 프롬프트
        """
        return f"""
당신은 정확하고 신뢰할 수 있는 정보만을 제공하는 AI 어시스턴트입니다.

## 작업: {task_description}

## 핵심 원칙:
1. **확실한 정보만 답변**: 제공된 컨텍스트에서 명확히 확인된 정보만 답변
2. **추측 금지**: 확실하지 않은 정보는 절대 추측하지 않음
3. **정보 없음 표시**: 컨텍스트에 없는 정보는 "정보가 없습니다"라고 명시
4. **출처 명시**: 답변의 근거가 되는 컨텍스트 부분을 인용

## 답변 형식:
- 확실한 정보: "확실합니다. [답변] (출처: [컨텍스트 인용])"
- 불확실한 정보: "확실하지 않지만, [답변] (출처: [컨텍스트 인용])"
- 정보 없음: "제공된 정보에서 해당 내용을 찾을 수 없습니다."

한국어로 답변하세요.
"""
    
    def create_rag_prompt(self, question: str, context: List[str], 
                         company_name: str = "") -> str:
        """
        RAG(Retrieval-Augmented Generation) 프롬프트를 생성합니다.
        
        Args:
            question: 사용자 질문
            context: 검색된 컨텍스트
            company_name: 회사명 (있는 경우)
            
        Returns:
            str: RAG 프롬프트
        """
        # 컨텍스트 길이 제한
        context_text = "\n\n".join(context[:5])  # 상위 5개만 사용
        if len(context_text) > self.config.max_context_length:
            context_text = context_text[:self.config.max_context_length] + "..."
        
        base_prompt = self.create_base_prompt("기업 정보 분석 및 답변")
        
        prompt = f"""
{base_prompt}

## 질문: {question}

## 검색된 정보:
{context_text}

## 답변 요구사항:
1. 위 검색된 정보만을 사용하여 답변
2. 정보가 없으면 "정보가 없습니다"라고 명시
3. 답변의 근거가 되는 구체적인 문장 인용
4. 확실하지 않은 정보는 "확실하지 않지만"으로 시작

답변:
"""
        return prompt
    
    def create_company_report_prompt(self, company_name: str, 
                                   field: str, context: str) -> str:
        """
        기업 리포트 생성을 위한 프롬프트를 생성합니다.
        
        Args:
            company_name: 회사명
            field: 요청 항목
            context: 검색된 컨텍스트
            
        Returns:
            str: 리포트 생성 프롬프트
        """
        format_rules = {
            "company_summary": "2~3문장 자유 서술",
            "industry_keywords": "상위 5개 키워드 리스트",
            "target_customers": "3~5개 키워드 리스트",
            "financial_info": "연도:금액 쌍의 객체 (금액은 단일 문자열로 표기)",
            "recent_trends": "3~5개 키워드 리스트",
            "competitors": "{경쟁사: 주요 경쟁 분야} 쌍의 **객체**",
            "strengths": "3~5개 리스트",
            "risk_factors": "3~5개 리스트",
            "key_executives": "이름만 포함한 **단일 문자열**"
        }
        
        format_description = format_rules.get(field, "단일 문자열 (또는 리스트)")
        
        prompt = f"""
당신은 회사 분석 전문가입니다. '{company_name}'의 '{field}' 항목을 다음 규칙에 따라 **한 가지** JSON 값으로 반환하세요.

## 핵심 원칙:
1. **확실한 정보만 응답**: 제공된 컨텍스트에서 명확히 확인된 정보만 사용
2. **추측 금지**: 확실하지 않은 정보는 절대 추측하지 않음
3. **정보 없음 표시**: 컨텍스트에 없는 정보는 null 반환

## 출력 양식: "{format_description}"

## 회사명: "{company_name}"
## 요청 항목: "{field}"

## 참고 컨텍스트:
{context}

## 출력은 오직 아래처럼 JSON만:
```json
{{
"{field}": ...  // 위 규칙에 맞춘 값 (정보 없으면 null)
}}
"""
        return prompt
    
    def create_validation_prompt(self, answer: str, context: str, 
                               question: str) -> str:
        """
        답변 검증을 위한 프롬프트를 생성합니다.
        
        Args:
            answer: 검증할 답변
            context: 원본 컨텍스트
            question: 원본 질문
            
        Returns:
            str: 검증 프롬프트
        """
        return f"""
당신은 답변의 정확성을 검증하는 전문가입니다.

## 원본 질문: {question}

## 제공된 답변: {answer}

## 원본 컨텍스트: {context}

## 검증 기준:
1. **정보 일치성**: 답변이 컨텍스트의 정보와 일치하는가?
2. **추측 여부**: 답변에 추측이나 가정이 포함되어 있는가?
3. **완전성**: 질문에 대한 답변이 완전한가?
4. **출처 명시**: 답변의 근거가 명확히 제시되었는가?

## 검증 결과를 JSON으로 반환:
```json
{{
"is_accurate": true/false,
"confidence_score": 0.0-1.0,
"issues": ["문제점1", "문제점2"],
"suggestions": ["개선제안1", "개선제안2"],
"answer_type": "confirmed/uncertain/not_found/error"
}}
```
"""

class OutputParser:
    """LLM 출력을 구조화된 형태로 파싱하는 클래스"""
    
    def __init__(self):
        self.json_pattern = r'```json\s*(.*?)\s*```'
        self.simple_json_pattern = r'\{.*?\}'
    
    def parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        JSON 응답을 파싱합니다.
        
        Args:
            response: LLM 응답
            
        Returns:
            Optional[Dict]: 파싱된 JSON 또는 None
        """
        try:
            # ```json ... ``` 패턴 찾기
            json_match = re.search(self.json_pattern, response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                return json.loads(json_str)
            
            # 단순 JSON 패턴 찾기
            json_match = re.search(self.simple_json_pattern, response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0).strip()
                return json.loads(json_str)
            
            return None
        except Exception as e:
            print(f"JSON 파싱 실패: {e}")
            return None
    
    def parse_confidence_score(self, response: str) -> float:
        """
        응답에서 신뢰도 점수를 추출합니다.
        
        Args:
            response: LLM 응답
            
        Returns:
            float: 신뢰도 점수 (0.0-1.0)
        """
        # 신뢰도 관련 키워드 패턴
        confidence_patterns = [
            r'신뢰도[:\s]*(\d+\.?\d*)',
            r'확신도[:\s]*(\d+\.?\d*)',
            r'confidence[:\s]*(\d+\.?\d*)',
            r'확실성[:\s]*(\d+\.?\d*)'
        ]
        
        for pattern in confidence_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                return min(max(score / 100.0, 0.0), 1.0)  # 0-1 범위로 정규화
        
        # 기본값
        return 0.5
    
    def parse_answer_type(self, response: str) -> AnswerType:
        """
        응답에서 답변 타입을 추출합니다.
        
        Args:
            response: LLM 응답
            
        Returns:
            AnswerType: 답변 타입
        """
        response_lower = response.lower()
        
        if any(keyword in response_lower for keyword in ["확실합니다", "확실히", "명확히"]):
            return AnswerType.CONFIRMED
        elif any(keyword in response_lower for keyword in ["확실하지 않지만", "추정", "아마도"]):
            return AnswerType.UNCERTAIN
        elif any(keyword in response_lower for keyword in ["정보가 없습니다", "찾을 수 없습니다", "알 수 없습니다"]):
            return AnswerType.NOT_FOUND
        else:
            return AnswerType.ERROR
    
    def extract_citations(self, response: str) -> List[str]:
        """
        응답에서 인용문을 추출합니다.
        
        Args:
            response: LLM 응답
            
        Returns:
            List[str]: 인용문 리스트
        """
        # 인용 패턴 찾기
        citation_patterns = [
            r'출처[:\s]*([^.\n]+)',
            r'근거[:\s]*([^.\n]+)',
            r'인용[:\s]*([^.\n]+)',
            r'\(([^)]+)\)'
        ]
        
        citations = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, response)
            citations.extend(matches)
        
        return list(set(citations))  # 중복 제거

class HallucinationDetector:
    """할루시네이션 감지 및 방지 클래스"""
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
    
    def detect_hallucination(self, answer: str, context: str, 
                           confidence_score: float) -> Dict[str, Any]:
        """
        할루시네이션을 감지합니다.
        
        Args:
            answer: 검사할 답변
            context: 원본 컨텍스트
            confidence_score: 신뢰도 점수
            
        Returns:
            Dict: 할루시네이션 감지 결과
        """
        # 1. 신뢰도 점수 기반 감지
        low_confidence = confidence_score < self.confidence_threshold
        
        # 2. 키워드 기반 감지
        hallucination_keywords = [
            "추정", "아마도", "일반적으로", "보통", "대부분",
            "probably", "maybe", "usually", "typically", "generally"
        ]
        
        has_uncertainty_keywords = any(
            keyword in answer.lower() for keyword in hallucination_keywords
        )
        
        # 3. 정보 일치성 검사 (간단한 키워드 매칭)
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())
        overlap_ratio = len(answer_words & context_words) / len(answer_words) if answer_words else 0
        
        low_overlap = overlap_ratio < 0.3
        
        # 종합 판단
        is_hallucination = low_confidence or has_uncertainty_keywords or low_overlap
        
        return {
            "is_hallucination": is_hallucination,
            "confidence_score": confidence_score,
            "low_confidence": low_confidence,
            "has_uncertainty_keywords": has_uncertainty_keywords,
            "low_overlap": low_overlap,
            "overlap_ratio": overlap_ratio,
            "risk_level": "high" if is_hallucination else "low"
        }
    
    def suggest_correction(self, answer: str, context: str, 
                          detection_result: Dict[str, Any]) -> str:
        """
        할루시네이션 감지 시 수정 제안을 생성합니다.
        
        Args:
            answer: 원본 답변
            context: 원본 컨텍스트
            detection_result: 감지 결과
            
        Returns:
            str: 수정 제안
        """
        if not detection_result["is_hallucination"]:
            return answer
        
        suggestions = []
        
        if detection_result["low_confidence"]:
            suggestions.append("신뢰도가 낮습니다. 더 확실한 정보만 답변하세요.")
        
        if detection_result["has_uncertainty_keywords"]:
            suggestions.append("추측성 표현을 제거하고 확실한 정보만 답변하세요.")
        
        if detection_result["low_overlap"]:
            suggestions.append("제공된 컨텍스트와 일치하지 않는 정보가 포함되어 있습니다.")
        
        if suggestions:
            return f"⚠️ 할루시네이션 감지됨\n" + "\n".join(suggestions) + f"\n\n수정된 답변: 정보가 부족하여 정확한 답변을 드릴 수 없습니다."
        
        return answer

# 사용 예시
if __name__ == "__main__":
    # 프롬프트 매니저 초기화
    prompt_manager = PromptManager()
    output_parser = OutputParser()
    hallucination_detector = HallucinationDetector()
    
    # 테스트
    question = "삼성전자의 2023년 매출은?"
    context = ["삼성전자는 2023년에 약 300조원의 매출을 기록했습니다."]
    
    # RAG 프롬프트 생성
    rag_prompt = prompt_manager.create_rag_prompt(question, context, "삼성전자")
    print("RAG 프롬프트:")
    print(rag_prompt[:200] + "...")
    
    # 가상의 LLM 응답
    mock_response = "확실합니다. 삼성전자의 2023년 매출은 약 300조원입니다. (출처: 삼성전자는 2023년에 약 300조원의 매출을 기록했습니다.)"
    
    # 응답 분석
    confidence = output_parser.parse_confidence_score(mock_response)
    answer_type = output_parser.parse_answer_type(mock_response)
    citations = output_parser.extract_citations(mock_response)
    
    print(f"\n응답 분석:")
    print(f"신뢰도: {confidence}")
    print(f"답변 타입: {answer_type.value}")
    print(f"인용문: {citations}")
    
    # 할루시네이션 감지
    detection = hallucination_detector.detect_hallucination(mock_response, context[0], confidence)
    print(f"할루시네이션 감지: {detection['is_hallucination']}") 