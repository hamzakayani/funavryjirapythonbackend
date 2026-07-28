module.exports = {
    apps: [
      {
        name: "ft_jira",
        cwd: "/home/azureuser/FT/funavryjirapythonbackend",
        script: "gunicorn",

        // Pinned to a single worker: the chat WebSocket connection manager
        // (app/core/chat_ws.py) is in-process/in-memory only, so a message
        // broadcast from one worker never reaches sockets connected to a
        // different worker. Do NOT raise this without first adding a Redis
        // pub/sub layer for chat broadcasts.
        args: "-w 1 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8005 --timeout 120 --max-requests 1000 --max-requests-jitter 100 --access-logfile - --access-logformat '%(h)s - - [%(t)s] \"%(m)s %(U)s %(H)s\" %(s)s %(b)s'",
  
        interpreter: "/home/azureuser/miniconda3/envs/ft-jira/bin/python",
  
        instances: 1,
        exec_mode: "fork",
  
        env: {
          PYTHONPATH: "."
        },
  
        /* Logging */
        error_file: "./app/logs/backend-error.log",
        out_file: "./app/logs/backend-out.log",
        log_date_format: "YYYY-MM-DD HH:mm:ss",
        merge_logs: true,
        time: true,
  
        /* Stability */
        autorestart: true,
        max_memory_restart: "1G",
        restart_delay: 5000,
        kill_timeout: 5000,
        exp_backoff_restart_delay: 100,
      }
    ]
  }