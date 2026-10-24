#!/bin/bash
# run only once


echo 'run only once! press enter to continue, ctrl+c to cancel'
read
pip3 install -r requirements.txt --break-system-packages
cd builder
./docker_control.sh create


