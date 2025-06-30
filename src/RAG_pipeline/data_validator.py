"""
data_validator.py
데이터 검증 모듈
- 추출된 데이터의 정확성 검증
- Ground truth와 비교
- 검증 실패 시 재호출 로직
"""
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

class DataValidator:
    """데이터 검증을 담당하는 클래스"""
    
    def __init__(self):
        # Ground truth 데이터 (실제로는 DB나 API에서 가져와야 함)
        self.ground_truth = {
            "무신사": {
                "대표자": "박준모",
                "매출액": "1조 1,005억원",
                "직원수": "510명",
                "설립년도": "2012",
                "업종": "쇼핑몰·오픈마켓·소셜커머스"
            }
        }
        
        # 검증 규칙
        self.validation_rules = {
            "대표자": self._validate_executive,
            "매출액": self._validate_revenue,
            "직원수": self._validate_employee_count,
            "설립년도": self._validate_year,
            "업종": self._validate_industry
        }
    
    def validate_field(self, company_name: str, field_name: str, 
                      extracted_value: str) -> Dict[str, Any]:
        """
        특정 필드의 데이터를 검증합니다.
        
        Args:
            company_name: 회사명
            field_name: 필드명
            extracted_value: 추출된 값
            
        Returns:
            Dict: 검증 결과
        """
        if not extracted_value:
            return {
                "valid": False,
                "reason": "데이터가 없음",
                "confidence": 0.0,
                "needs_retry": True
            }
        
        # Ground truth 확인
        ground_truth_data = self.ground_truth.get(company_name, {})
        expected_value = ground_truth_data.get(field_name)
        
        # 검증 규칙 적용
        validation_func = self.validation_rules.get(field_name, self._validate_generic)
        validation_result = validation_func(extracted_value, expected_value)
        
        # 결과 구성
        result = {
            "valid": validation_result["valid"],
            "extracted_value": extracted_value,
            "expected_value": expected_value,
            "confidence": validation_result["confidence"],
            "reason": validation_result["reason"],
            "needs_retry": validation_result["needs_retry"],
            "validated_at": datetime.now().isoformat()
        }
        
        return result
    
    def _validate_executive(self, extracted: str, expected: Optional[str]) -> Dict[str, Any]:
        """대표자 정보 검증"""
        if not expected:
            return {"valid": True, "confidence": 0.8, "reason": "Ground truth 없음", "needs_retry": False}
        
        # 정확히 일치하는지 확인
        if extracted.strip() == expected.strip():
            return {"valid": True, "confidence": 1.0, "reason": "정확히 일치", "needs_retry": False}
        
        # 부분 일치 확인 (성만 일치하는 경우 등)
        extracted_clean = re.sub(r'[^\w가-힣]', '', extracted)
        expected_clean = re.sub(r'[^\w가-힣]', '', expected)
        
        if extracted_clean in expected_clean or expected_clean in extracted_clean:
            return {"valid": True, "confidence": 0.9, "reason": "부분 일치", "needs_retry": False}
        
        return {"valid": False, "confidence": 0.0, "reason": "불일치", "needs_retry": True}
    
    def _validate_revenue(self, extracted: str, expected: Optional[str]) -> Dict[str, Any]:
        """매출액 정보 검증"""
        if not expected:
            return {"valid": True, "confidence": 0.8, "reason": "Ground truth 없음", "needs_retry": False}
        
        # 숫자 추출
        extracted_num = self._extract_number(extracted)
        expected_num = self._extract_number(expected)
        
        if extracted_num is None or expected_num is None:
            return {"valid": False, "confidence": 0.0, "reason": "숫자 추출 실패", "needs_retry": True}
        
        # 10% 오차 허용
        tolerance = expected_num * 0.1
        if abs(extracted_num - expected_num) <= tolerance:
            return {"valid": True, "confidence": 0.95, "reason": "오차 범위 내", "needs_retry": False}
        
        return {"valid": False, "confidence": 0.0, "reason": "매출액 불일치", "needs_retry": True}
    
    def _validate_employee_count(self, extracted: str, expected: Optional[str]) -> Dict[str, Any]:
        """직원수 정보 검증"""
        if not expected:
            return {"valid": True, "confidence": 0.8, "reason": "Ground truth 없음", "needs_retry": False}
        
        # 숫자 추출
        extracted_num = self._extract_number(extracted)
        expected_num = self._extract_number(expected)
        
        if extracted_num is None or expected_num is None:
            return {"valid": False, "confidence": 0.0, "reason": "숫자 추출 실패", "needs_retry": True}
        
        # 20% 오차 허용 (직원수는 변동이 있을 수 있음)
        tolerance = expected_num * 0.2
        if abs(extracted_num - expected_num) <= tolerance:
            return {"valid": True, "confidence": 0.9, "reason": "오차 범위 내", "needs_retry": False}
        
        return {"valid": False, "confidence": 0.0, "reason": "직원수 불일치", "needs_retry": True}
    
    def _validate_year(self, extracted: str, expected: Optional[str]) -> Dict[str, Any]:
        """연도 정보 검증"""
        if not expected:
            return {"valid": True, "confidence": 0.8, "reason": "Ground truth 없음", "needs_retry": False}
        
        # 연도 추출
        extracted_year = self._extract_year(extracted)
        expected_year = self._extract_year(expected)
        
        if extracted_year is None or expected_year is None:
            return {"valid": False, "confidence": 0.0, "reason": "연도 추출 실패", "needs_retry": True}
        
        if extracted_year == expected_year:
            return {"valid": True, "confidence": 1.0, "reason": "정확히 일치", "needs_retry": False}
        
        return {"valid": False, "confidence": 0.0, "reason": "연도 불일치", "needs_retry": True}
    
    def _validate_industry(self, extracted: str, expected: Optional[str]) -> Dict[str, Any]:
        """업종 정보 검증"""
        if not expected:
            return {"valid": True, "confidence": 0.8, "reason": "Ground truth 없음", "needs_retry": False}
        
        # 키워드 기반 유사도 검증
        extracted_keywords = set(re.findall(r'[\w가-힣]+', extracted.lower()))
        expected_keywords = set(re.findall(r'[\w가-힣]+', expected.lower()))
        
        if extracted_keywords & expected_keywords:  # 교집합이 있으면
            return {"valid": True, "confidence": 0.85, "reason": "키워드 일치", "needs_retry": False}
        
        return {"valid": False, "confidence": 0.0, "reason": "업종 불일치", "needs_retry": True}
    
    def _validate_generic(self, extracted: str, expected: Optional[str]) -> Dict[str, Any]:
        """일반적인 검증"""
        if not expected:
            return {"valid": True, "confidence": 0.7, "reason": "Ground truth 없음", "needs_retry": False}
        
        if extracted.strip() == expected.strip():
            return {"valid": True, "confidence": 1.0, "reason": "정확히 일치", "needs_retry": False}
        
        return {"valid": False, "confidence": 0.0, "reason": "불일치", "needs_retry": True}
    
    def _extract_number(self, text: str) -> Optional[float]:
        """텍스트에서 숫자 추출"""
        # 한국어 숫자 패턴 (조, 억, 만 등)
        patterns = [
            r'(\d+(?:\.\d+)?)\s*조',
            r'(\d+(?:\.\d+)?)\s*억',
            r'(\d+(?:\.\d+)?)\s*만',
            r'(\d+(?:,\d+)*)',  # 일반 숫자
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                num_str = match.group(1).replace(',', '')
                try:
                    num = float(num_str)
                    # 단위에 따른 변환
                    if '조' in text:
                        num *= 1000000000000
                    elif '억' in text:
                        num *= 100000000
                    elif '만' in text:
                        num *= 10000
                    return num
                except ValueError:
                    continue
        
        return None
    
    def _extract_year(self, text: str) -> Optional[int]:
        """텍스트에서 연도 추출"""
        match = re.search(r'(\d{4})', text)
        if match:
            try:
                year = int(match.group(1))
                if 1900 <= year <= 2100:
                    return year
            except ValueError:
                pass
        return None
    
    def validate_multiple_fields(self, company_name: str, 
                               field_data: Dict[str, str]) -> Dict[str, Any]:
        """
        여러 필드를 한번에 검증합니다.
        
        Args:
            company_name: 회사명
            field_data: 필드별 데이터 {field_name: value}
            
        Returns:
            Dict: 검증 결과
        """
        validation_results = {}
        overall_valid = True
        needs_retry_fields = []
        
        for field_name, value in field_data.items():
            result = self.validate_field(company_name, field_name, value)
            validation_results[field_name] = result
            
            if not result["valid"]:
                overall_valid = False
                if result["needs_retry"]:
                    needs_retry_fields.append(field_name)
        
        return {
            "overall_valid": overall_valid,
            "field_results": validation_results,
            "needs_retry_fields": needs_retry_fields,
            "validated_at": datetime.now().isoformat()
        }
    
    def get_validation_summary(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        검증 결과 요약을 반환합니다.
        
        Args:
            validation_results: 검증 결과
            
        Returns:
            Dict: 검증 요약
        """
        field_results = validation_results.get("field_results", {})
        
        total_fields = len(field_results)
        valid_fields = sum(1 for r in field_results.values() if r["valid"])
        retry_fields = len(validation_results.get("needs_retry_fields", []))
        
        avg_confidence = sum(r["confidence"] for r in field_results.values()) / total_fields if total_fields > 0 else 0
        
        return {
            "total_fields": total_fields,
            "valid_fields": valid_fields,
            "invalid_fields": total_fields - valid_fields,
            "retry_fields": retry_fields,
            "accuracy": valid_fields / total_fields if total_fields > 0 else 0,
            "avg_confidence": avg_confidence,
            "overall_valid": validation_results.get("overall_valid", False)
        } 