#!/bin/bash
pid=$(ps aux | grep web_server | grep -v grep | awk '{print $2}' | head -1)
echo "Backend PID: $pid"
if [ -z "$pid" ]; then
  echo "ERROR: web_server not found"
  exit 1
fi
token=$(cat /proc/$pid/environ | tr '\0' '\n' | grep OMEGA_AUTH_TOKEN | cut -d= -f2-)
echo "Token: ${token:0:20}..."
echo "$token"
