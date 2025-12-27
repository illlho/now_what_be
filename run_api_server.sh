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
    echo -e "${YELLOW}⚠ 가상 환경 '${ENV_NAME}'이(가) 이미 존재합니다.${NC}"
    echo -e "${GREEN}가상 환경을 활성화합니다...${NC}"
else
    echo -e "${YELLOW}가상 환경 '${ENV_NAME}'이(가) 존재하지 않습니다.${NC}"
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
echo -e "${GREEN}가상 환경 '${ENV_NAME}' 활성화 중...${NC}"
conda activate "${ENV_NAME}"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 가상 환경 활성화에 실패했습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 가상 환경이 활성화되었습니다.${NC}"

# Python 버전 확인
PYTHON_VER=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}현재 Python 버전: ${PYTHON_VER}${NC}"

# 프로젝트 디렉토리로 이동
cd "${PROJECT_DIR}" || exit 1

# .env 파일 존재 확인
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env 파일이 존재하지 않습니다.${NC}"
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}.env.example 파일을 참고하여 .env 파일을 생성하세요.${NC}"
    fi
fi

# pip 업그레이드
echo -e "${GREEN}pip를 최신 버전으로 업그레이드합니다...${NC}"
pip install --upgrade pip --quiet

# requirements.txt 설치
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}필요한 패키지를 설치합니다...${NC}"
    echo -e "${YELLOW}(LangGraph, LangChain 최신 버전 포함)${NC}"
    
    pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 패키지 설치에 실패했습니다.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ 패키지 설치가 완료되었습니다.${NC}"
else
    echo -e "${RED}❌ requirements.txt 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

# 설치된 주요 패키지 버전 확인
echo -e "${GREEN}설치된 주요 패키지 버전:${NC}"
python -c "import langgraph; print(f'  LangGraph: {langgraph.__version__}')" 2>/dev/null || echo "  LangGraph: 확인 불가"
python -c "import langchain; print(f'  LangChain: {langchain.__version__}')" 2>/dev/null || echo "  LangChain: 확인 불가"
python -c "import fastapi; print(f'  FastAPI: {fastapi.__version__}')" 2>/dev/null || echo "  FastAPI: 확인 불가"

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

