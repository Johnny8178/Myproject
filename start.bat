@echo off
start cmd /k "python api_server.py"
start cmd /k "cd vue3 && npm run dev"
echo 正在启动前端和后端，请稍后访问 http://localhost:5173
