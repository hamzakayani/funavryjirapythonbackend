module.exports = {
    apps: [
      {
        name: "ft_jira",
        cwd: "/home/azureuser/FT/funavryjirapythonbackend",
        script: "gunicorn",
  
        args: "-w 8 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8005 --timeout 120 --max-requests 1000 --max-requests-jitter 100 --access-logfile -",
  
        interpreter: "/home/azureuser/miniconda3/envs/ft/bin/python",
  
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