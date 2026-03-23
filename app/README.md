# TypeMaster Product Layout

This `app/` directory is the product-oriented layout:

- `app/agent`: LangGraph Agent runtime and orchestration bridge.
- `app/backend`: Python API server (conversation + workflow control).
- `app/frontend`: React + TypeScript + Ant Design UI shell.

## Run Backend

```bash
pip install -r app/backend/requirements.txt -r requirements.txt
python3 app/backend/run.py
```

Backend default URL: `http://127.0.0.1:50120`

## Run Frontend

```bash
cd app/frontend
npm install
npm run dev
```

Frontend default URL: `http://127.0.0.1:50121`

## PM2 托管启动（推荐）

在仓库根目录执行：
./start.sh

管理命令：
./scripts/pm2_status.sh
./scripts/pm2_logs.sh
./scripts/pm2_stop_all.sh

默认地址：
- Frontend: http://127.0.0.1:50121
- Backend: http://127.0.0.1:50120
- Health: http://127.0.0.1:50120/api/v1/health
