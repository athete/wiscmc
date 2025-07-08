import sys
import os

def main():
    # Forwards command line arguments to condor_submit

    # Set MCDIRPATH to the working directory of this package
    package_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["MCDIRPATH"] = package_dir

    from wiscmc.condor_submit import main as condor_submit_main
    condor_submit_main(sys.argv[1:])