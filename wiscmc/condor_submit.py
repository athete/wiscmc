import os
import argparse
from getpass import getuser
from datetime import datetime
from pprint import pprint

from .utils import find_x509

# Constants and Environment Variables

MCDIRPATH = os.environ.get("MCDIRPATH")
if not MCDIRPATH:
    raise EnvironmentError("MCDIRPATH is not set")
CONDOR_BASE = "$_CONDOR_SCRATCH_DIR"
USER = getuser()
XROOTD_REDIRECTOR = "root://cmsxrootd.hep.wisc.edu/"
OUTPATH_PREFIX = f"{XROOTD_REDIRECTOR}/store/user/{USER}/"
X509_PROXY_PATH = None

CAMPAIGNS = [c for c in os.listdir(f"{MCDIRPATH}/campaigns") if c.startswith("Run")]

JOBFLAVORS = [
    "espresso",
    "microcentury",
    "longlunch",
    "workday",
    "tomorrow",
    "testmatch",
    "nextweek",
]


def build_executable(filename, fragmentpath, args):
    with open(filename, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("mkdir jobs && cd jobs\n")
        f.write("source /cvmfs/cms.cern.ch/cmsset_default.sh\n")
        f.write("echo 'The OS on HTCondor is:'\ncat /etc/os-release\n")
        f.write("echo 'Validating x509 proxy...'\nvoms-proxy-info -all\n")
        if args.ship_env:
            f.write(
                """
mv ../env.tar.gz .
tar -xzf env.tar.gz
echo \"After extracting the environment\"
ls -lrth
for cdir in ./CMSSW*; do
    cd $cdir/src
    echo $cdir
    scramv1 b ProjectRename
    eval `scram runtime -sh`
    cd ../..
done                           
"""
            )
        command = f"source {CONDOR_BASE}/run.sh {args.name} {CONDOR_BASE}/{os.path.basename(fragmentpath)} {args.nevents_per_job} $1 {args.n_threads} "
        if args.use_pileup_file:
            command += f"{CONDOR_BASE}/pileupinput.dat"
        if args.scouting:
            command += f" true"
        command += " 2>&1"
        f.write(command + "\n")
        # Transfer output files
        if args.output_dir:
            SAVEPATH = OUTPATH_PREFIX + args.output_dir
        else:
            SAVEPATH = OUTPATH_PREFIX + f"{args.name}/{args.campaign}/"
        print(f"Produced files will be saved to {SAVEPATH}")
        if args.scouting:
            f.write(f"xrdcp -f -r -p ./ScoutingNanoAOD/ {SAVEPATH}\n")
        else:
            f.write(f"xrdcp -f -r -p ./NanoAOD/ {SAVEPATH}\n")
        if args.keep_mini:
            f.write(f"xrdcp -f -r -p ./MiniAOD/ {SAVEPATH}\n")


def main(args=None) -> None:
    parser = argparse.ArgumentParser(
        description="""
        Submit Monte Carlo production jobs to an HTCondor instance. \n\n
        Runs the entire MC generation chain from GEN to NanoAOD/Scouting NanoAOD.
        """
    )
    parser.add_argument("--name", type=str, required=True, help="Dataset name")
    parser.add_argument("--fragment", type=str, required=True, help="Path to fragment")
    parser.add_argument(
        "--campaign",
        type=str,
        required=True,
        help="MC campaign to run. Allowed options are: " + ", ".join(CAMPAIGNS),
        choices=CAMPAIGNS,
        metavar=" ",
    )
    parser.add_argument(
        "-e",
        "--ship_env",
        action="store_true",
        help="Use a prepackaged CMSSW environment",
    )
    parser.add_argument(
        "--use_pileup_file",
        action="store_true",
        help="Use a premade pileup input file instead of a runtime DAS query. Saves time during production, Run `source campaigns/campaign/getpileupfiles.sh",
    )
    parser.add_argument(
        "--nevents_per_job", type=int, default=100, help="Number of events per job"
    )
    parser.add_argument(
        "--n_jobs", type=int, default=1, help="Number of total jobs to run"
    )
    parser.add_argument(
        "--n_threads",
        type=int,
        default=8,
        help="Number of threads (reduced if condor priority is a problem)",
    )
    parser.add_argument(
        "--x509",
        type=str,
        default=None,
        help="Path to an x509 proxy",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=None,
        help="Where to output the generated NanoAOD (and MiniAOD, if requested) files.",
    )
    parser.add_argument(
        "--keep_mini", action="store_true", help="Save produced MiniAOD files to disk"
    )
    parser.add_argument(
        "--scouting",
        action="store_true",
        default=False,
        help="Produce Scouting NanoAOD files. If this option is chosen, regular NanoAOD files are not saved.",
    )
    parser.add_argument(
        "-t",
        "--job_flavor",
        type=str,
        default="longlunch",
        help="JobFlavour ClassAd choice. Allowed options are: " + ", ".join(JOBFLAVORS),
        choices=JOBFLAVORS,
        metavar="",
    )
    parser.add_argument(
        "-m",
        "--memory",
        type=int,
        default=3000,
        help="Memory requested on a worker (MB)",
    )
    parser.add_argument(
        "-s",
        "--submit_filename",
        type=str,
        help="Custom name for the HTCondor configuration (jdl) file",
    )
    parser.add_argument(
        "-l", "--log", type=str, help="Custom name for HTCondor log files"
    )
    parser.add_argument(
        "--no_submit", action="store_true", help="Prepare jobs but do not submit them"
    )
    args = parser.parse_args(args)

    # Validate fragment path
    fragment_abspath = os.path.abspath(args.fragment)
    if not os.path.isfile(fragment_abspath):
        raise FileNotFoundError(f"Invalid fragment path: {fragment_abspath}")

    print("Creating a submission job with the following parameters...")
    print(f"Dataset name: {args.name}")
    print(f"Using fragment at: {fragment_abspath}")
    print(f"Dataset campaign: {args.campaign}")
    print(f"Total number of events requested: {args.n_jobs * args.nevents_per_job}")
    if args.scouting:
        print(
            f"Scouting NanoAOD production is enabled. Regular NanoAODs will NOT be produced."
        )

    # Check x509 proxy, and make a new one if necessary
    X509_PROXY_PATH = find_x509(args.x509)
    os.system("voms-proxy-info")

    # Create submission directory in /nfs_scratch/username/
    dt_str = datetime.now().strftime("%Y-%m-%d-%H%M")
    condor_submit_path = f"/nfs_scratch/{USER}/condor-jobs/{args.name}/{dt_str}"
    os.makedirs(condor_submit_path, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(condor_submit_path)

    executable_name = f"run_mc.sh"
    build_executable(executable_name, fragment_abspath, args)

    # Create list of files to transfer
    campaign_dir = f"{MCDIRPATH}/campaigns/{args.campaign}"
    files_to_transfer = [
        fragment_abspath,
        f"{campaign_dir}/run.sh",
    ]

    os.chdir(campaign_dir)
    if args.use_pileup_file:
        pileup_file = os.path.join(campaign_dir, "pileupinput.dat")
        if not os.path.isfile(pileup_file):
            print("Generating pileup input file...")
            os.system("source ./getpileupfiles.sh")
        files_to_transfer.append(pileup_file)
    if args.ship_env:
        env_file = os.path.join(campaign_dir, "env.tar.gz")
        if not os.path.isfile(env_file):
            print("Creating environment tarball...")
            os.system("source ./build_env.sh")
        files_to_transfer.append(env_file)
    pprint(f"Files to transder to condor nodes: {files_to_transfer}")

    os.chdir(condor_submit_path)

    # Build the Condor JDL file
    condor_jdl_name = (
        args.submit_filename + "_cfg.jdl" if args.submit_filename else "condor_cfg.jdl"
    )
    with open(condor_jdl_name, "w") as jdl:
        jdl.write(
            f"""universe                = vanilla
executable              = {executable_name}
use_x509userproxy       = true
X509userproxy           = {X509_PROXY_PATH}
transfer_executable     = true
notification            = never
request_memory          = {args.memory}
request_cpus            = {args.n_threads}
+JobFlavour             = {args.job_flavor}         

should_transfer_files   = yes
transfer_input_files    = {','.join(files_to_transfer)}
transfer_output_files   = ""
when_to_transfer_output = on_exit
"""
        )
        condor_out = f"{args.log or dt_str}.$(ClusterId).$(ProcId)"
        jdl.write(
            f"""
output                 = {condor_out}.out
error                  = {condor_out}.err
log                    = {condor_out}.log
arguments              = $(ProcId)
queue {args.n_jobs}
"""
        )
        print("Successfully built submission script and executable.")
        print(f"Condor submission directory: {condor_submit_path}")
        if not args.no_submit:
            print("Submitting Condor jobs...")
            os.system(f"condor_submit {condor_jdl_name}")

    os.chdir(cwd)


if __name__ == "__main__":
    main()
