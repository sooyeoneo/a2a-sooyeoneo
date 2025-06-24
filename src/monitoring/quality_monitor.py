"""
quality_monitor.py
RAG 파이프라인 품질 모니터링 및 자동화 모듈
- 정확도 자동 측정(정답률, 신뢰도, 할루시네이션 비율 등)
- 리포트 자동 생성(정량/정성 지표)
- 실사용 피드백 수집 및 저장
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

class QualityMonitor:
    """RAG 품질 모니터링 및 자동화 클래스"""
    def __init__(self, log_dir: str = "./quality_logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.logs: List[Dict[str, Any]] = []

    def log_result(self, result: Dict[str, Any]):
        """
        RAG 실행 결과를 로그로 저장합니다.
        """
        self.logs.append(result)
        log_file = os.path.join(self.log_dir, f"rag_log_{datetime.now().date()}.jsonl")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    def compute_metrics(self, logs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        품질 지표(정확도, 신뢰도, 할루시네이션 비율 등) 자동 산출
        """
        logs = logs if logs is not None else self.logs
        if not logs:
            return {}
        total = len(logs)
        correct = sum(1 for log in logs if log.get("answer_type") == "confirmed")
        uncertain = sum(1 for log in logs if log.get("answer_type") == "uncertain")
        not_found = sum(1 for log in logs if log.get("answer_type") == "not_found")
        hallucinated = sum(1 for log in logs if log.get("hallucination_detected"))
        avg_confidence = sum(log.get("confidence_score", 0) for log in logs) / total
        
        return {
            "total": total,
            "정답률(confirmed)": correct / total if total else 0,
            "불확실률(uncertain)": uncertain / total if total else 0,
            "정보없음(not_found)": not_found / total if total else 0,
            "할루시네이션 비율": hallucinated / total if total else 0,
            "평균 신뢰도": avg_confidence
        }

    def generate_report(self, metrics: Dict[str, Any], logs: Optional[List[Dict[str, Any]]] = None, file_name: Optional[str] = None):
        """
        품질 리포트(정량/정성) 자동 생성 및 저장
        """
        logs = logs if logs is not None else self.logs
        file_name = file_name or f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = os.path.join(self.log_dir, file_name)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# RAG 품질 리포트\n\n")
            f.write(f"생성일: {datetime.now().isoformat()}\n\n")
            f.write(f"## 정량 지표\n")
            for k, v in metrics.items():
                f.write(f"- {k}: {v}\n")
            f.write(f"\n## 최근 5개 예시\n")
            for log in logs[-5:]:
                f.write(f"- 질문: {log.get('question')}\n  - 답변: {log.get('answer')}\n  - 신뢰도: {log.get('confidence_score')}\n  - 할루시네이션: {log.get('hallucination_detected')}\n\n")
        print(f"✅ 품질 리포트 저장: {report_path}")

    def collect_user_feedback(self, question: str, answer: str, feedback: str, user: str = "anonymous"):
        """
        실사용자 피드백 수집 및 저장
        """
        feedback_data = {
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "question": question,
            "answer": answer,
            "feedback": feedback
        }
        feedback_file = os.path.join(self.log_dir, f"user_feedback_{datetime.now().date()}.jsonl")
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_data, ensure_ascii=False) + "\n")
        print(f"✅ 피드백 저장: {feedback_file}")

# 사용 예시
if __name__ == "__main__":
    monitor = QualityMonitor()
    # 가상 로그 예시
    for i in range(10):
        monitor.log_result({
            "question": f"Q{i+1}",
            "answer": f"A{i+1}",
            "answer_type": "confirmed" if i % 2 == 0 else "uncertain",
            "confidence_score": 0.8 if i % 2 == 0 else 0.5,
            "hallucination_detected": i % 3 == 0
        })
    metrics = monitor.compute_metrics()
    monitor.generate_report(metrics)
    monitor.collect_user_feedback("삼성전자 매출?", "300조원", "정확한 답변 감사합니다.", user="user1") 