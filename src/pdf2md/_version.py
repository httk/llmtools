# Note: this file gets replaced during installation with a fixed version number.

import subprocess, shutil, os

if shutil.which("git") is not None:

    __version__ = subprocess.check_output(["git", "describe", "--always", "--dirty=-devel"], cwd=os.path.dirname(os.path.realpath(__file__))).strip().decode('utf8')

else:

    __version__ = "unknown-devel"

