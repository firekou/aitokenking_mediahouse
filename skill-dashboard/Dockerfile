# ★ 必須從 repo 根建置。
#   本服務讀的是 registry/、skills/、drafts/、cases/ —— 它們都在根目錄下。
#   把 build context 設成 skill-dashboard/ 會得到一個「找不到清單」的服務，
#   而那個畫面跟「還沒有 skill」長得一模一樣。
FROM python:3.11-slim

WORKDIR /app

# 只複製服務真正會讀到的東西。不複製 .git、不複製任何逐字稿原始檔。
COPY skill-dashboard/server.py  /app/skill-dashboard/server.py
COPY registry/                  /app/registry/
COPY skills/                    /app/skills/
COPY drafts/                    /app/drafts/
COPY providers/                 /app/providers/

# cases/ 只取目錄與分流結果，逐字稿本體（raw-transcripts.json / transcripts.sql）
# 本來就被 .gitignore 擋在版本庫外，不會進到映像檔。
COPY cases/                     /app/cases/

ENV MEDIAHOUSE_ROOT=/app
ENV PORT=8080
EXPOSE 8080

# 純標準庫，無 pip install。
CMD ["python3", "skill-dashboard/server.py"]
