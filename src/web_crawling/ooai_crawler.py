import json
from pathlib import Path
import re
import sys
import urllib.parse
import requests
import time
from collections import Counter  # 빈도수 계산을 위해 추가
from .config import USER_AGENT
from web_crawling.ooai_extra_field import ooai_field

# from common.ooai_extra_field import ooai_field
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def ooai_crawler(query: str) -> dict:
    """
    oo.ai에 특정 쿼리 검색하여 검색 결과를 파싱하여 전환

    Args:
    query(str): 검색할 검색어 (예:  "삼성전자 주요 타겟 고객층")

    Returns:
    dict: 검색 결과와 관련된 정보 담은 딕셔너리
        {
            'json': {'search_id': ..., 'full_html_answer': ..., 'plain_text_answer': ...}}
        }
        검색 실패 시 빈 딕셔너리 반환.
    """
    encoded_query = urllib.parse.quote(query)

    # 1. CSRF 토큰 추출
    url = f"https://oo.ai/search?q={encoded_query}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[{query}] 초기 페이지 접근 오류: {e}")
        return {}

    html = response.text
    token = None
    # 정규표현식을 사용하여 token 값 추출
    token_match = re.search(r'token:\s*"([^"]+)"', html)
    if token_match:
        token = token_match.group(1)

    # 추출된 토큰이 없다면 에러 메시지 출력
    if not token:
        print(f"[{query}] CSRF 토큰을 찾을 수 없습니다.")
        return {}

    # 추출된 토큰을 출력
    print({"json": {"csrf_token": token}})

    # 2. 검색 API 호출
    search_url = f"https://oo.ai/api/search?q={encoded_query}&lang=ko&tz=Asia/Seoul"
    headers = {
        "accept": "*/*",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "cookie": "_variant=stable; lang=ko",
        "origin": "https://oo.ai",
        "referer": f"https://oo.ai/search?q={encoded_query}",
        "user-agent": USER_AGENT,
        "x-csrf-token": f"Bearer {token}",
    }

    try:
        response = requests.post(search_url, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[{query}] 검색 API 호출 오류: {e}")
        return {}

    parsed_data = parse_sse_response(response.text)
    print(json.dumps(parsed_data, ensure_ascii=False, indent=4))

    return parsed_data


def parse_sse_response(stream_data: str) -> dict:
    """
    SSE 형식의 응답을 파싱하여 최종 답변 추출

    Args:
        stream_data(str) : SEE 형식의 문자열 데이터

    Returns:
        dict: 파싱된 검색 결과(search_id, full_html_answer, plain_text_answer)
    """
    lines = stream_data.split("\n")
    final_answer_html = None
    sid = None
    for line in lines:
        if line.startswith("data:"):
            try:
                json_data_string = line[5:].strip()
                if json_data_string:
                    parsed_data = json.loads(json_data_string)
                    if parsed_data.get("type") == "save":
                        if "answer" in parsed_data:
                            final_answer_html = parsed_data["answer"]
                        if "id" in parsed_data:
                            sid = parsed_data["id"]
                        if final_answer_html and sid:
                            break
            except Exception:
                # JSON 파싱 오류는 무시하고 다음 라인으로 진행
                continue

    plain_text_answer = None
    if final_answer_html:
        # <webblock> 태그와 그 내용 제거
        temp_answer = re.sub(
            r"<webblock>.*?</webblock>", "", final_answer_html, flags=re.DOTALL
        ).strip()
        # 나머지 HTML 태그를 공백으로 변환 후, 여러 공백을 하나로 합치고 앞뒤 공백 제거
        plain_text_answer = re.sub(r"<[^>]+>", " ", temp_answer)
        plain_text_answer = re.sub(r"\s+", " ", plain_text_answer).strip()
    return {
        "json": {
            "search_id": sid,
            "full_html_answer": final_answer_html,
            "plain_text_answer": plain_text_answer,
        }
    }


def enrich_company_data(company_name: str, existing_data: dict) -> dict:
    """
    기존에 수집된 기업 데이터에서 비어있는 특정 필드들을 oo.ai 검색을 통해 보완.
    주요 목표 고객층, 경쟁사, 강점, 위험 요인, 최근 동향 등의 정보를 검색하여 `existing_data`를 업데이트.

    Args:
        company_name(str): 기업명. oo.ai 검색 쿼리를 구성하는 데 사용.
        existing_data(dict): 현재까지 수집된 기업 데이터가 담긴 딕셔너리.
                             이 딕셔너리의 비어있는 필드를 보완.(필드: 값)

    Returns:
        dict: oo.ai 검색을 통해 보완된 기업 데이터가 담긴 딕셔너리.
              새로운 정보가 발견되지 않으면 빈 문자열("")로 채워짐.
    """
    # oo.ai 보완할 필드 템플릿 적용
    fields_to_enrich = ooai_field(company_name)

    extra_prompt_guide = "에 대해 다음 가이드라인을 엄수하여 1문장으로 핵심만 요약해 주세요: 1. 불필요한 서론/결론 없이 바로 본론부터 시작. 2. 객관적인 정보만 포함. 3. 가능한 한 수치나 사실 기반으로 서술. 4. ~이다/입니다 체 종결 5. 관련 정보가 없을 경우 텍스트 대신 ''으로 출력."

    final_data = existing_data.copy()

    for field, query_template in fields_to_enrich.items():
        # 현재 필드 값이 비어있는지 확인
        if not final_data.get(field):
            print(
                f"🔍'{field}' 필드가 비어있습니다. OO.ai에서 검색을 시도합니다: '{query_template}'"
            )
            search_result = ooai_crawler(query_template + extra_prompt_guide)

            if search_result and search_result["json"].get("plain_text_answer"):
                answer = search_result["json"]["plain_text_answer"]
                final_data[field] = answer
                print(f"✅'{field}' 필드 채움")
            else:
                print(
                    f"❌ '{field}' 필드에 대한 OO.ai 검색 결과가 없거나 유효하지 않습니다."
                )
                final_data[field] = ""

    return final_data
