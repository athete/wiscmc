#!/bin/bash

if [ -d env ]; then
	rm -rf env
fi

mkdir env && cd env

source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_14_1_0
cd CMSSW_14_1_0/src
eval `scram runtime -sh`
scram b
cd ../../

tar -czf env.tar.gz ./CMSSW*
mv env.tar.gz ..
cd ..

eval `scram unsetenv -sh`