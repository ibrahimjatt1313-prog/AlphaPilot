
import os
import sys
import subprocess
from datetime import datetime


# ============================================================
# ALPHAPILOT AI - MASTER CONTROLLER
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PYTHON = os.path.join(
    BASE_DIR,
    "venv",
    "Scripts",
    "python.exe"
)

AGENTS_DIR = os.path.join(
    BASE_DIR,
    "agents"
)


# ============================================================
# SETTINGS
# ============================================================

PAPER_TRADING = True

# These modules are diagnostic / analysis modules.
MODULES = [
    ("AI Decision", "trade_signal.py"),
    ("Option Selector", "option_selector.py"),
    ("Performance", "performance.py"),
]


# ============================================================
# HEADER
# ============================================================

def print_header():

    print("=" * 70)
    print("                 ALPHAPILOT AI")
    print("                 MASTER CONTROLLER")
    print("=" * 70)

    print()
    print("Mode              : PAPER TRADING")
    print("Python            :", PYTHON)
    print("Project           :", BASE_DIR)

    print()
    print(
        "Controller started:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


# ============================================================
# CHECK ENVIRONMENT
# ============================================================

def check_environment():

    print("\n" + "=" * 70)
    print("             ENVIRONMENT CHECK")
    print("=" * 70)

    # --------------------------------------------------------
    # Python
    # --------------------------------------------------------

    if not os.path.exists(PYTHON):

        print("\nERROR: Virtual environment Python not found.")

        print(
            "Expected:",
            PYTHON
        )

        return False

    print("\nPython environment : OK")


    # --------------------------------------------------------
    # .env
    # --------------------------------------------------------

    env_file = os.path.join(
        BASE_DIR,
        ".env"
    )

    if os.path.exists(env_file):

        print(".env file         : FOUND")

    else:

        print(".env file         : NOT FOUND")

        print(
            "Warning: Alpaca API credentials may be unavailable."
        )


    # --------------------------------------------------------
    # Agents directory
    # --------------------------------------------------------

    if os.path.isdir(AGENTS_DIR):

        print("Agents directory   : OK")

    else:

        print("Agents directory   : MISSING")

        return False


    return True


# ============================================================
# CHECK MODULE
# ============================================================

def module_exists(filename):

    path = os.path.join(
        AGENTS_DIR,
        filename
    )

    return os.path.exists(path)


# ============================================================
# RUN MODULE
# ============================================================

def run_module(
    display_name,
    filename
):

    print("\n" + "=" * 70)

    print(
        "             RUNNING:",
        display_name.upper()
    )

    print("=" * 70)


    module_path = os.path.join(
        AGENTS_DIR,
        filename
    )


    if not os.path.exists(module_path):

        print(
            "\nMODULE NOT FOUND:",
            module_path
        )

        return False


    try:

        result = subprocess.run(

            [
                PYTHON,
                module_path
            ],

            cwd=BASE_DIR,

            check=False
        )


        print("\n" + "-" * 70)

        print(
            "Module:",
            display_name
        )

        print(
            "Exit Code:",
            result.returncode
        )


        if result.returncode == 0:

            print(
                "Status: SUCCESS"
            )

            return True


        print(
            "Status: FAILED"
        )

        return False


    except Exception as e:

        print(
            "\nERROR running module:"
        )

        print(e)

        return False


# ============================================================
# SYSTEM STATUS
# ============================================================

def print_system_status(results):

    print("\n" + "=" * 70)
    print("             ALPHAPILOT SYSTEM STATUS")
    print("=" * 70)


    for name, success in results:

        if success:

            status = "OK"

        else:

            status = "FAILED"


        print(
            "%-25s : %s"
            % (name, status)
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print_header()


    # --------------------------------------------------------
    # Environment
    # --------------------------------------------------------

    if not check_environment():

        print("\nEnvironment check FAILED.")

        return 1


    # --------------------------------------------------------
    # Run analysis modules
    # --------------------------------------------------------

    results = []


    for display_name, filename in MODULES:

        if not module_exists(filename):

            print(
                "\nSkipping missing module:",
                filename
            )

            results.append(
                (display_name, False)
            )

            continue


        success = run_module(
            display_name,
            filename
        )


        results.append(
            (display_name, success)
        )


    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    print_system_status(
        results
    )


    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("             MASTER CONTROLLER COMPLETE")
    print("=" * 70)

    print(
        "Timestamp:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    failed = [
        name
        for name, success in results
        if not success
    ]


    if failed:

        print("\nFailed modules:")

        for name in failed:

            print(
                " -",
                name
            )

        print(
            "\nSystem completed with warnings."
        )

        return 1


    print(
        "\nAll controller modules completed successfully."
    )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )

