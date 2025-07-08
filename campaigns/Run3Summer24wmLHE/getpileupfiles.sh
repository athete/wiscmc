#!/bin/bash
# source getfileupfiles [(optional) NUM_FILES_TO_USE]
dasgoclient -query="file dataset=/Neutrino_E-10_gun/RunIIISummer24PrePremix-Premixlib2024_140X_mcRun3_2024_realistic_v26-v1/PREMIX" > pileupinput.dat
if [ -z "$1" ]; then
    echo "The entire premix dataset will be used."
    return 0
else
    echo "Using only the top $1 files in the premix dataset."
    head -n $1 pileupinput.dat | tee pileupinput.dat
fi