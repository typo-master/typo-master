module.exports = {
  apps: [
    {
      name: 'typomaster-backend',
      script: './app/backend/run_prod.py',
      cwd: '/Users/cc11001100/github/typo-master/typo-master',
      interpreter: '/Users/cc11001100/github/typo-master/typo-master/venv311/bin/python',
      env: {
        PYTHONUNBUFFERED: '1',
      },
      // 保活配置
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 1000,
      exp_backoff_restart_delay: 100,

      // 进程管理
      watch: false,
      ignore_watch: [],
      kill_timeout: 5000,
      wait_ready: false,
      listen_timeout: 10000,

      // 日志
      log_file: '/Users/cc11001100/github/typo-master/typo-master/.pm2/logs/typomaster-backend.log',
      error_file: '/Users/cc11001100/github/typo-master/typo-master/.pm2/logs/typomaster-backend-error.log',
      out_file: '/Users/cc11001100/github/typo-master/typo-master/.pm2/logs/typomaster-backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',

      // 其他
      instance_var: 'INSTANCE_ID',
    },
    {
      name: 'typomaster-frontend',
      script: 'npm',
      args: 'run dev -- --host 0.0.0.0 --port 50121 --strictPort',
      cwd: '/Users/cc11001100/github/typo-master/typo-master/app/frontend',
      interpreter: 'none',

      // 保活配置
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 1000,
      exp_backoff_restart_delay: 100,

      // 进程管理
      watch: false,
      kill_timeout: 5000,
      wait_ready: false,
      listen_timeout: 10000,

      // 日志
      log_file: '/Users/cc11001100/github/typo-master/typo-master/.pm2/logs/typomaster-frontend.log',
      error_file: '/Users/cc11001100/github/typo-master/typo-master/.pm2/logs/typomaster-frontend-error.log',
      out_file: '/Users/cc11001100/github/typo-master/typo-master/.pm2/logs/typomaster-frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',

      // 其他
      instance_var: 'INSTANCE_ID',
    },
  ],
};
