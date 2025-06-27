"""
test_web_report_agent.py
report_generator.py의 기능을 실제로 테스트하는 코드
"""
import os
from langchain_openai import ChatOpenAI
from generator.web_report_agent import generate_company_report, generate_sample_report

if __name__ == "__main__":
    print("=== 웹 리포트 에이전트 테스트 ===\n")
    
    # 1. 예시 데이터로 테스트 (API 키 불필요)
    print("1. 예시 데이터로 HTML 리포트 생성 테스트...")
    try:
        generate_sample_report()
        print("✅ 예시 데이터 테스트 성공: company_report.html 파일이 생성되었습니다.\n")
    except Exception as e:
        print(f"❌ 예시 데이터 테스트 실패: {e}\n")
    
    # 2. DuckDuckGo API를 사용한 테스트 (API 키 불필요)
    print("2. DuckDuckGo API를 사용한 테스트...")
    try:
        llm = ChatOpenAI(model="gpt-4o")
        company_name = "삼성전자"
        html_report = generate_company_report(company_name, llm)
        with open("samsung_report.html", "w", encoding="utf-8") as f:
            f.write(html_report)
        print("✅ DuckDuckGo API 테스트 성공: samsung_report.html 파일이 생성되었습니다.")
    except Exception as e:
        print(f"❌ DuckDuckGo API 테스트 실패: {e}")
    
    print("\n=== 테스트 완료 ===") 