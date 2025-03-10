if [ -z "$SEAMLESS_TOOLS_DIR" ]; then
  export SEAMLESS_TOOLS_DIR=~/seamless-tools
fi

export SEAMLESS_DATABASE_IP=localhost
rm -rf /tmp/PIN-FILESYSTEM-FOLDER1
rm -rf /tmp/PIN-FILESYSTEM-FOLDER2
db=/tmp/PIN-FILESYSTEM-TEST-DB
rm -rf $db
mkdir $db
echo 'Run 1'
python3 -u pin-filesystem.py > pin-filesystem.log 2>&1
checksum=`tail -1 pin-filesystem.log`
cat pin-filesystem.log
rm -f pin-filesystem.log
echo 'Start database'
dbconfig='''
host: "0.0.0.0" 
port:  5522
stores: 
    -
      path: "'''$db'''"
      readonly: false
      serve_filenames: true
'''
dbconfigro='''
host: "0.0.0.0"
port:  5522
stores: 
    -
      path: "'''$db'''"
      readonly: true
      serve_filenames: true
'''
echo "$dbconfig" | python3 $SEAMLESS_TOOLS_DIR/database.py /dev/stdin > $db.log 2>&1 &
sleep 2
echo
echo 'Run 2'
python3 -u pin-filesystem.py
echo
echo 'Share folder 2 and restart database'
kill `ps -ef | grep database | awk '{print $2}' | tac | awk 'NR > 1'`
$SEAMLESS_TOOLS_DIR/database-run-actions $db pin-filesystem-2.cson
$SEAMLESS_TOOLS_DIR/database-share-deepfolder-directory $db --collection testfolder2
echo "$dbconfigro" | python3 $SEAMLESS_TOOLS_DIR/database.py /dev/stdin > $db.log 2>&1 &
sleep 2
echo
echo 'Run 3'
python3 -u pin-filesystem.py
echo
echo 'Share folder 1 and restart database'
kill `ps -ef | grep database | awk '{print $2}' | tac | awk 'NR > 1'`
$SEAMLESS_TOOLS_DIR/database-run-actions $db pin-filesystem-1.cson
$SEAMLESS_TOOLS_DIR/database-share-deepfolder-directory  $db --collection testfolder1
echo "$dbconfigro" | python3 $SEAMLESS_TOOLS_DIR/database.py /dev/stdin > $db.log 2>&1 &
sleep 2
echo
echo 'Run 4'
python3 -u pin-filesystem.py
kill `ps -ef | grep database | awk '{print $2}' | tac | awk 'NR > 1'`
echo
echo 'Server log'
cat $db.log
echo ''
rm -rf $db
rm -rf /tmp/PIN-FILESYSTEM-FOLDER1
rm -rf /tmp/PIN-FILESYSTEM-FOLDER2
rm -f $db.log