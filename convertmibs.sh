#!/bin/bash
CHEF_REPO=~/code/cloudant/chef
INPUT_DIR=$CHEF_REPO/cookbooks/snmp/files/default
OUTPUT_DIR=conf/mibs/
for FILE in $(ls $INPUT_DIR/CLOUDANT-*-MIB.txt); do
    INPUT=$FILE
    OUTPUT=$(echo $OUTPUT_DIR/$(basename $FILE) | sed -e 's/.txt$/.py/')
    echo "Converting: $INPUT"
    build-pysnmp-mib -o $OUTPUT $INPUT
done
