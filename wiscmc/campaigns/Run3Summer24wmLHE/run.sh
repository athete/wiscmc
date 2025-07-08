#!/bin/bash
# Run a private production using the Run3Summer2024 configuration. 
# Uses CMSSW_14_1_0 instead of CMSSW_14_0_X for a workaround to a bug with Scouting NanoAOD production
# Local example:
# source run.sh MCDatasetName /path/to/fragment.py NEVENTS JOBINDEX NTHREADS filelist:/path/to/pileup/list.txt is_scouting
echo $@

CMSSW_RELEASE=CMSSW_14_1_0
GT=140X_mcRun3_2024_realistic_v26

if [ -z "$1" ]; then
    echo "Argument 1 (name of dataset) is mandatory."
    return 1
fi
NAME=$1

if [ -z $2 ]; then
    echo "Argument 2 (path to fragment) is mandatory."
    return 1
fi
FRAGMENTPATH=$2
echo "Input arg 2 = $FRAGMENTPATH"
FRAGMENTPATH=$(readlink -e $FRAGMENTPATH)
echo "After readlink, this fragment path will be used = $FRAGMENTPATH"

if [ -z "$3" ]; then
    NEVENTS=100
else
    NEVENTS=$3
fi

if [ -z "$4" ]; then
    JOBINDEX=0
else
    JOBINDEX=$4
fi

if [ -z "$5" ]; then
    MAX_NTHREADS=8
else
    MAX_NTHREADS=$5
fi
# Space out seeds; Madgraph concurrent mode adds idx(thread) to random seed. The extra *4 is a paranoia factor.
RSEED=$((JOBINDEX * MAX_NTHREADS * 4 + 1001))

if [ -z "$6" ]; then
    PILEUP_FILELIST="dbs:/Neutrino_E-10_gun/RunIIISummer24PrePremix-Premixlib2024_$GT-v1/PREMIX"
else
    PILEUP_FILELIST="filelist:$6"
fi

if [ -z "$7" ]; then
    SCOUTING=false
else
    SCOUTING=true
fi

echo $@
echo "Fragment=$FRAGMENTPATH"
echo "Dataset Name=$NAME"
echo "NEvents=$NEVENTS"
echo "Random seed=$RSEED"
echo "Pileup filelist=$PILEUP_FILELIST"
echo "Enable Scouting=$SCOUTING"

# setup the environment
if [ -r $CMSSW_RELEASE/src ] ; then
    echo "Release $CMSSW_RELEASE already exists"
else 
    cmsrel $CMSSW_RELEASE
    cd $CMSSW_RELEASE/src
    eval `scram runtime -sh`
fi

mkdir -pv $CMSSW_BASE/src/Configuration/GenProduction/python
cp $FRAGMENTPATH $CMSSW_BASE/src/Configuration/GenProduction/python/fragment.py
if [ ! -f "$CMSSW_BASE/src/Configuration/GenProduction/python/fragment.py" ]; then
    echo "Fragment copy failed"
    return 1
fi 
cd $CMSSW_BASE/src
scram b
cd ../..

# Make directories to store intermediate datatier files
mkdir -p wmLHEGS
mkdir -p DIGIPremix
mkdir -p RECO
mkdir -p MiniAOD
mkdir -p NanoAOD
mkdir -p ScoutingNanoAOD

# Step 1: wmLHEGS
cmsDriver.py Configuration/GenProduction/python/fragment.py \
    --python_filename "Run3Summer24wmLHEGS_${NAME}_cfg.py" \
    --eventcontent RAWSIM,LHE \
    --datatier GEN-SIM,LHE \
    --fileout "file:wmLHEGS/Run3Summer24_wmLHEGS_${NAME}_${JOBINDEX}.root" \
    --conditions $GT \
    --beamspot Realistic25ns13p6TeVEarly2023Collision \
    --step LHE,GEN,SIM \
    --geometry DB:Extended \
    --era Run3_2024 \
    --mc \
    --nThreads $(( $MAX_NTHREADS < 8 ? $MAX_NTHREADS : 8)) \
    --customise_commands "process.source.numberEventsInLuminosityBlock=cms.untracked.uint32(1000)\\nprocess.RandomNumberGeneratorService.externalLHEProducer.initialSeed=${RSEED}" \
    --no_exec \
    -n $NEVENTS
cmsRun "Run3Summer24wmLHEGS_${NAME}_cfg.py"
if [ ! -f "wmLHEGS/Run3Summer24_wmLHEGS_${NAME}_${JOBINDEX}.root" ]; then
    echo "wmLHEGS/Run3Summer24_wmLHEGS_${NAME}_${JOBINDEX}.root not found. Exiting."
    return 1
fi

# Step 2: DIGIPremix
cd $TOPDIR
cmsDriver.py \
    --python_filename "Run3Summer24DRPremix0_${NAME}_cfg.py" \
    --eventcontent PREMIXRAW \
    --datatier GEN-SIM-RAW \
    --filein "file:wmLHEGS/Run3Summer24_wmLHEGS_${NAME}_${JOBINDEX}.root" \
    --fileout "file:DIGIPremix/Run3Summer24_DRPremix0_${NAME}_${JOBINDEX}.root" \
    --conditions $GT \
    --step DIGI,DATAMIX,L1,DIGI2RAW,HLT:2024v14 \
    --pileup_input "$PILEUP_FILELIST" \
    --geometry DB:Extended \
    --era Run3_2024 \
    --datamix PreMix \
    --procModifiers premix_stage2 \
    --mc \
    --nThreads $(( $MAX_NTHREADS < 8 ? $MAX_NTHREADS : 8)) \
    --no_exec \
    -n $NEVENTS
cmsRun "Run3Summer24DRPremix0_${NAME}_cfg.py"
if [ ! -f "DIGIPremix/Run3Summer24_DRPremix0_${NAME}_${JOBINDEX}.root" ]; then
    echo "DIGIPremix/Run3Summer24_DRPremix0_${NAME}_${JOBINDEX}.root not found. Exiting."
    return 1
fi

# Step 3: RECO
cmsDriver.py \
    --python_filename "Run3Summer24RECO_${NAME}_cfg.py" \
    --eventcontent AODSIM \
    --datatier AODSIM \
    --filein "file:DIGIPremix/Run3Summer24_DRPremix0_${NAME}_${JOBINDEX}.root" \
    --fileout "file:RECO/Run3Summer24_RECO_${NAME}_${JOBINDEX}.root" \
    --conditions $GT \
    --step RAW2DIGI,L1Reco,RECO,RECOSIM \
    --geometry DB:Extended \
    --era Run3_2024 \
    --mc \
    --nThreads $(( $MAX_NTHREADS < 8 ? $MAX_NTHREADS : 8)) \
    --no_exec \
    -n $NEVENTS
cmsRun "Run3Summer24RECO_${NAME}_cfg.py"
if [ ! -f "RECO/Run3Summer24_RECO_${NAME}_${JOBINDEX}.root" ]; then
    echo "RECO/Run3Summer24_RECO_${NAME}_${JOBINDEX}.root not found. Exiting."
    return 1
fi

# Step 4: MiniAOD
cmsDriver.py \
    --python_filename "Run3Summer24MiniAOD_${NAME}_cfg.py" \
    --eventcontent MINIAODSIM \
    --datatier MINIAODSIM \
    --filein "file:RECO/Run3Summer24_RECO_${NAME}_${JOBINDEX}.root" \
    --fileout "file:MiniAOD/Run3Summer24_MiniAOD_${NAME}_${JOBINDEX}.root" \
    --conditions $GT \
    --step PAT \
    --geometry DB:Extended \
    --era Run3_2024 \
    --mc \
    --nThreads $(( $MAX_NTHREADS < 8 ? $MAX_NTHREADS : 8)) \
    --no_exec \
    -n $NEVENTS
cmsRun "Run3Summer24MiniAOD_${NAME}_cfg.py"
if [ ! -f "MiniAOD/Run3Summer24_MiniAOD_${NAME}_${JOBINDEX}.root" ]; then
    echo "MiniAOD/Run3Summer24_MiniAOD_${NAME}_${JOBINDEX}.root not found. Exiting."
    return 1
fi

if [ "$SCOUTING" = true ]; then 
    # Step 5: Scouting NanoAOD
    cmsDriver.py \
        --python_filename "Run3Summer24ScoutingNanoAOD_${NAME}_cfg.py" \
        --eventcontent NANOAODSIM \
        --datatier NANOAODSIM \
        --filein "file:MiniAOD/Run3Summer24_MiniAOD_${NAME}_${JOBINDEX}.root" \
        --fileout "file:ScoutingNanoAOD/Run3Summer24_ScoutingNanoAOD_${NAME}_${JOBINDEX}.root" \
        --conditions $GT \
        --step NANO:@Scout \
        --scenario pp \
        --geometry DB:Extended \
        --era Run3_2024 \
        --mc \
        --nThreads $(( $MAX_NTHREADS < 8 ? $MAX_NTHREADS : 8)) \
        --no_exec \
        -n $NEVENTS
    cmsRun "Run3Summer24ScoutingNanoAOD_${NAME}_cfg.py"
    if [ ! -f "ScoutingNanoAOD/Run3Summer24_ScoutingNanoAOD_${NAME}_${JOBINDEX}.root" ]; then
        echo "ScoutingNanoAOD/Run3Summer24_ScoutingNanoAOD_${NAME}_${JOBINDEX}.root not found. Exiting."
        return 1
    fi

else
    # Step 5: NanoAOD
    cmsDriver.py \
        --python_filename "Run3Summer24NanoAOD_${NAME}_cfg.py" \
        --eventcontent NANOAODSIM \
        --datatier NANOAODSIM \
        --filein "file:MiniAOD/Run3Summer24_MiniAOD_${NAME}_${JOBINDEX}.root" \
        --fileout "file:NanoAOD/Run3Summer24_NanoAOD_${NAME}_${JOBINDEX}.root" \
        --conditions $GT \
        --step NANO \
        --scenario pp \
        --geometry DB:Extended \
        --era Run3_2024 \
        --mc \
        --nThreads $(( $MAX_NTHREADS < 8 ? $MAX_NTHREADS : 8)) \
        --no_exec \
        -n $NEVENTS
    cmsRun "Run3Summer24NanoAOD_${NAME}_cfg.py"
    if [ ! -f "NanoAOD/Run3Summer24_NanoAOD_${NAME}_${JOBINDEX}.root" ]; then
        echo "NanoAOD/Run3Summer24_NanoAOD_${NAME}_${JOBINDEX}.root not found. Exiting."
        return 1
    fi
fi