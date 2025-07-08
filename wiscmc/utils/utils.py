import subprocess
import os
import re


def get_campaign_os(campaign):
    if "Run3" in campaign:
        return "el9"
    elif "RunII" in campaign:
        return "el7" if "UL" in campaign else "el6"
    raise ValueError(f"Unknown MC campaign type: {campaign}.")


def get_os_container(required_os):
    # Use rhel containers, as x509 proxy doesn't work with unpacked.cern.ch el* containers
    return f"/cvmfs/singularity.opensciencegrid.org/cmssw/cms:rh{required_os}-x86_64"


def find_x509(x509_path: str):
    """Checks if a x509 proxy exists and returns the path"""
    default_x509_path = f"/tmp/x509up_u{os.getuid()}"
    if not x509_path:
        make_proxy(default_x509_path)
        return default_x509_path
    try:
        x509_abspath = os.path.abspath(x509_path)
        if x509_abspath[:4] == "/afs":
            raise OSError(f"HTCondor cannot use proxies stored on AFS.")
        if not os.path.isfile(x509_abspath):
            raise FileNotFoundError(f"Could not find voms proxy at {x509_abspath}")
        if get_proxy_lifetime(x509_abspath) < 24:
            raise OSError("x509 proxy expires in under 24 hours.")
        return x509_path
    except Exception:
        print("Could not find a suitable x509 proxy. Generating one now...")
        make_proxy(default_x509_path)
        return default_x509_path


def make_proxy(proxy_path):
    os.system(f"voms-proxy-init -voms cms -out {proxy_path} -valid 192:00")


def get_proxy_lifetime(proxy_path):
    lifetime = subprocess.check_output(
        f"voms-proxy-info -timeleft -file {proxy_path}", shell=True
    ).strip()
    return float(lifetime)
