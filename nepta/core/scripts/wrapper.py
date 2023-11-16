#!/usr/bin/env python
import subprocess
import os
import sys


def main():
    script_name = os.path.basename(sys.argv[0])  # Get the script name from the command
    dir_of_this_script = os.path.dirname(os.path.abspath(__file__))
    target_script = os.path.join(dir_of_this_script, f"{script_name}")

    if os.path.exists(target_script) and os.access(target_script, os.X_OK):
        subprocess.call(target_script)
    else:
        print(f"Error: Script {target_script} not found or is not executable.")


if __name__ == "__main__":
    main()
