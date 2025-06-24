"""
test_web_report_agent.py
web_report_agent.py의 기능을 실제로 테스트하는 코드
"""
import os
from langchain_openai import ChatOpenAI
from web_report_agent import generate_company_report

if __name__ == "__main__":
    # 환경변수에서 API 키 불러오기
    SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
    if not SEARCH_API_KEY:
        print("[ERROR] SEARCH_API_KEY 환경변수가 설정되어 있지 않습니다.")
        exit(1)

    # LLM 인스턴스 생성
    llm = ChatOpenAI(model_name="gpt-4o")

    # 테스트용 기업명
    company_name = "삼성전자"

    try:
        html_report = generate_company_report(company_name, SEARCH_API_KEY, llm)
        with open("samsung_report.html", "w", encoding="utf-8") as f:
            f.write(html_report)
        print("[성공] 삼성전자 리포트가 samsung_report.html 파일로 저장되었습니다.")
    except Exception as e:
        print(f"[실패] 에러 발생: {e}") 