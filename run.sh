#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

case "${1:-start}" in
    start)
        if [ -f bot.pid ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
            echo "Bot is already running (PID: $(cat bot.pid))"
            exit 1
        fi
        nohup python -m src.main > bot.log 2>&1 &
        echo $! > bot.pid
        echo "Bot started (PID: $!)"
        echo "Log: $(pwd)/bot.log"
        ;;
    stop)
        if [ -f bot.pid ]; then
            kill "$(cat bot.pid)" 2>/dev/null && echo "Bot stopped" || echo "Bot is not running"
            rm -f bot.pid
        else
            echo "No PID file found"
        fi
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    log)
        tail -f bot.log
        ;;
    status)
        if [ -f bot.pid ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
            echo "Bot is running (PID: $(cat bot.pid))"
        else
            echo "Bot is not running"
            rm -f bot.pid 2>/dev/null
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|log|status}"
        ;;
esac
