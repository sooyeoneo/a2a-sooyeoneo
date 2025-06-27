import os
from jinja2 import Template

REPORT_PATH = os.path.join(os.path.dirname(__file__), '../generated_reports/test_company_report.html')
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), '../generator/report_generator.py')

def test_html_report_generation():
    # 기존 리포트 파일 삭제(있다면)
    if os.path.exists(REPORT_PATH):
        os.remove(REPORT_PATH)
    # report_generator.py 실행 (경로에 공백이 있을 수 있으므로 쌍따옴표로 감싸서 전달)
    exit_code = os.system(f'python "{SCRIPT_PATH}" "{REPORT_PATH}"')
    assert exit_code == 0, 'report_generator.py 실행 실패'
    assert os.path.exists(REPORT_PATH), 'HTML 리포트 파일이 생성되지 않음'
    # 파일 내용 일부 확인
    with open(REPORT_PATH, 'r', encoding='utf-8') as f:
        html = f.read()
    assert '<html' in html and '</html>' in html, 'HTML 태그가 없음'
    assert '회사' in html or '기업' in html, '회사/기업 정보가 없음'

if __name__ == "__main__":
    test_html_report_generation()
    print("✅ HTML 리포트 생성 테스트 통과") 