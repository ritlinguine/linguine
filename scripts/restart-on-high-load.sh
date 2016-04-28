CPU_USAGE=$(uptime | cut -d"," -f5 | cut -d":" -f2 | cut -d" " -f2 | sed -e "s/\.//g")
CPU_USAGE_THRESHOLD=200

if [ $CPU_USAGE -gt $CPU_USAGE_THRESHOLD ] ; then
  systemctl restart linguine-node
  systemctl restart linguine-python
fi
