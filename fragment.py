import FWCore.ParameterSet.Config as cms

externalLHEProducer = cms.EDProducer(
    "ExternalLHEProducer",
    args=cms.vstring(
        "/afs/hep.wisc.edu/home/athete/datasets/gridpacks/ttbarDM_inclusive_scalar_mchi_1_mphi_50_gSM_1_gDM_1_6800GeV_el9_amd64_gcc11_CMSSW_13_2_9_tarball.tar.xz"
    ),
    nEvents=cms.untracked.uint32(5000),
    numberOfParameters=cms.uint32(1),
    outputFile=cms.string("cmsgrid_final.lhe"),
    scriptName=cms.FileInPath(
        "GeneratorInterface/LHEInterface/data/run_generic_tarball_cvmfs.sh"
    ),
)

# Link to cards:
# https://github.com/cms-sw/genproductions/tree/02c6e5b080dc6e6a5d9ab8fb16b793505262e14d/bin/MadGraph5_aMCatNLO/cards/production/13TeV/DarkMatter/DMPseudo_ttbar_dilep/DMPseudoscalar_ttbar01j_mphi_100_mchi_10_gSM_1p0_gDM_1p0

import FWCore.ParameterSet.Config as cms

from Configuration.Generator.Pythia8CommonSettings_cfi import *
from Configuration.Generator.Pythia8CUEP8M1Settings_cfi import *

generator = cms.EDFilter(
    "Pythia8HadronizerFilter",
    maxEventsToPrint=cms.untracked.int32(1),
    pythiaPylistVerbosity=cms.untracked.int32(1),
    filterEfficiency=cms.untracked.double(1.0),
    pythiaHepMCVerbosity=cms.untracked.bool(False),
    comEnergy=cms.double(13600.0),
    PythiaParameters=cms.PSet(
        pythia8CommonSettingsBlock,
        pythia8CUEP8M1SettingsBlock,
        processParameters=cms.vstring(
            "JetMatching:setMad = off",
            "JetMatching:scheme = 1",
            "JetMatching:merge = on",
            "JetMatching:jetAlgorithm = 2",
            "JetMatching:etaJetMax = 5.",
            "JetMatching:coneRadius = 1.",
            "JetMatching:slowJetPower = 1",
            "JetMatching:qCut = 90.",  # this is the actual merging scale
            "JetMatching:nQmatch = 4",  # 4 corresponds to 4-flavour scheme (no matching of b-quarks), 5 for 5-flavour scheme
            "JetMatching:nJetMax = 1",  # number of partons in born matrix element for highest multiplicity
            "JetMatching:doShowerKt = off",  # off for MLM matching, turn on for shower-kT matching
            "Check:epTolErr = 0.0003",
            "9100000:new  = MED MED 3 0 0 X_MMed_X 0 0 0 99999",
            "9100022:new  = DM  DM  2 0 0 X_MFM_X  0 0 0 99999",
            "9100022:mayDecay = off",
        ),
        parameterSets=cms.vstring(
            "pythia8CommonSettings",
            "pythia8CUEP8M1Settings",
            "processParameters",
        ),
    ),
)


# Link to generator fragment:
# https://raw.githubusercontent.com/cms-sw/genproductions/eb45213db83babe397f28221eafef9c57d0fc785/python/ThirteenTeV/Hadronizer_TuneCUETP8M1_13TeV_MLM_4f_max1j_LHE_pythia8_cff.py
