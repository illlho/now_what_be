#!/bin/bash

# 프로젝트 설정
ENV_NAME="now_what_be_env"
PYTHON_VERSION="3.10"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 색상 출력을 위한 설정
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Now What Backend API 서버 실행 스크립트${NC}"
echo -e "${GREEN}========================================${NC}"

# Conda 설치 확인
if ! command -v conda &> /dev/null; then
    echo -e "${RED}❌ Conda가 설치되어 있지 않습니다.${NC}"
    echo -e "${YELLOW}Conda를 설치한 후 다시 시도하세요.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Conda가 설치되어 있습니다.${NC}"

# Conda 초기화 (필요한 경우)
eval "$(conda shell.bash hook)"

# 가상 환경 존재 여부 확인
if conda env list | grep -q "^${ENV_NAME}\s"; then
    echo -e "${GREEN}✓ 가상 환경 '${ENV_NAME}'을(를) 활성화합니다.${NC}"
else
    echo -e "${GREEN}Python ${PYTHON_VERSION}로 가상 환경을 생성합니다...${NC}"
    
    # Python 3.10 이상으로 가상 환경 생성
    conda create -n "${ENV_NAME}" python="${PYTHON_VERSION}" -y
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 가상 환경 생성에 실패했습니다.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ 가상 환경이 생성되었습니다.${NC}"
fi

# 가상 환경 활성화
conda activate "${ENV_NAME}"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 가상 환경 활성화에 실패했습니다.${NC}"
    exit 1
fi

# 프로젝트 디렉토리로 이동
cd "${PROJECT_DIR}" || exit 1

# .env 파일 존재 확인 (경고만 표시, 서버는 실행 가능)
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env 파일이 존재하지 않습니다. (선택사항)${NC}"
fi

# requirements.txt 확인
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

# 패키지 설치 필요 여부 확인
# 핵심 패키지가 설치되어 있는지 확인
NEED_INSTALL=false
if ! pip show fastapi &>/dev/null || ! pip show uvicorn &>/dev/null || ! pip show langgraph &>/dev/null || ! pip show langchain &>/dev/null; then
    NEED_INSTALL=true
else
    # requirements.txt의 패키지와 설치된 패키지 비교
    # pip freeze와 requirements.txt를 비교하여 누락된 패키지 확인
    INSTALLED=$(pip freeze 2>/dev/null | cut -d'=' -f1 | tr '[:upper:]' '[:lower:]')
    while IFS= read -r line; do
        # 주석과 빈 줄 제외
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # 패키지 이름 추출 (버전 정보 제거)
        package_name=$(echo "$line" | sed 's/[<>=!].*//' | sed 's/\[.*\]//' | xargs | tr '[:upper:]' '[:lower:]')
        
        if [ -n "$package_name" ]; then
            # 설치된 패키지 목록에 없으면 설치 필요
            if ! echo "$INSTALLED" | grep -q "^${package_name}$"; then
                NEED_INSTALL=true
                break
            fi
        fi
    done < requirements.txt
fi

# 패키지 설치 (필요한 경우에만)
if [ "$NEED_INSTALL" = true ]; then
    echo -e "${GREEN}필요한 패키지를 설치합니다...${NC}"
    pip install -r requirements.txt --quiet
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 패키지 설치에 실패했습니다.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ 패키지 설치가 완료되었습니다.${NC}"
else
    echo -e "${GREEN}✓ 필요한 패키지가 모두 설치되어 있습니다.${NC}"
fi

# API 서버 실행
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚀 API 서버를 시작합니다...${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}서버 주소: http://0.0.0.0:8000${NC}"
echo -e "${YELLOW}API 문서: http://localhost:8000/docs${NC}"
echo -e "${YELLOW}종료하려면 Ctrl+C를 누르세요.${NC}"
echo -e "${GREEN}========================================${NC}"

# main.py 실행 (uvicorn 사용)
python main.py

