rm -f twopi-colored-jobmaster.seamless

python3 simple-pi-database.py
export SEAMLESS_COMMUNION_OUTGOING_IP=0.0.0.0
export SEAMLESS_COMMUNION_OUTGOING_PORT=8602
python3 ~/seamless-scripts/jobslave.py --database --time 5 &
unset SEAMLESS_COMMUNION_OUTGOING_IP
unset SEAMLESS_COMMUNION_OUTGOING_PORT
sleep 2
python3 ~/seamless-scripts/color-graph-jobmaster.py twopi.seamless twopi-colored-jobmaster.seamless
wait
md5sum twopi-colored-jobmaster.seamless
