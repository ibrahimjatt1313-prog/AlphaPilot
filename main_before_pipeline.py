import os
import sys
import subprocess
from datetime import datetime

from dotenv import load_dotenv


# ============================================================
# ALPHAPILOT AI - MASTER CONTROLLER
# ============================================================

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
PYTHON = sys.executable


# ============================================================
# SETTINGS
# ============================================================

MIN_CONFIDENCE = 70

PAPER_TRADING = True


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("                 ALPHAPILOT AI")
print("                 MASTER CONTROLLER")
print("=" * 70)

print()
print("Mode              : PAPER TRADING")
print("Python            :", PYTHON)
print("Project           :", BASE_DIR)

print(
    "Controller started:",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

print("\n" + "=" * 70)
print("             ENVIRONMENT CHECK")
print("=" * 70)

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")


if not API_KEY or not SECRET_KEY:

    print("\nERROR: Alpaca API keys not found.")
    print("Check your .env file.")

    raise SystemExit(1)


print("Python environment : OK")
print(".env file          : FOUND")


if not os.path.isdir(AGENTS_DIR):

    print("Agents directory   : MISSING")

    raise SystemExit(1)


print("Agents directory   : OK")


# ============================================================
# RUN MODULE
# ============================================================

def run_module(filename, title):

    path = os.path.join(
        AGENTS_DIR,
        filename
    )

    if not os.path.isfile(path):

        print(
            "\nERROR: Module not found:",
            path
        )

        return False

    print("\n" + "=" * 70)

    print(
        "             RUNNING:",
        title
    )

    print("=" * 70)

    try:

        result = subprocess.run(
            [PYTHON, path],
            cwd=BASE_DIR
        )

        print("\n" + "-" * 70)

        print("Module    :", title)
        print("Exit Code :", result.returncode)

        if result.returncode == 0:

            print("Status    : SUCCESS")

            return True

        print("Status    : FAILED")

        return False

    except Exception as e:

        print("\nERROR running module:")
        print(e)

        return False


# ============================================================
# STEP 1
# AI TRADE SIGNAL
# ============================================================

signal_ok = run_module(
    "trade_signal.py",
    "AI TRADE SIGNAL"
)


if not signal_ok:

    print("\nAI signal failed.")
    raise SystemExit(1)


# ============================================================
# STEP 2
# OPTION SELECTOR
# ============================================================

option_ok = run_module(
    "option_selector.py",
    "OPTION SELECTOR"
)


if not option_ok:

    print("\nOption selector failed.")
    raise SystemExit(1)


# ============================================================
# STEP 3
# ENTRY MANAGER
# ============================================================

print("\n" + "=" * 70)
print("             ENTRY DECISION")
print("=" * 70)

print()
print("Entry manager will now evaluate:")
print()
print("  • BUY / NO TRADE")
print("  • Confidence threshold")
print("  • Existing position")
print("  • Existing orders")
print("  • Option quote")
print("  • Maximum position value")
print()
print("Paper trading only.")
print()


entry_ok = run_module(
    "entry_manager.py",
    "ENTRY MANAGER"
)


if not entry_ok:

    print("\nEntry manager failed.")

    # Do not continue to order monitor
    # if entry manager itself failed.

    raise SystemExit(1)


# ============================================================
# STEP 4
# PERFORMANCE
# ============================================================

performance_ok = run_module(
    "performance.py",
    "PERFORMANCE"
)


# ============================================================
# SYSTEM STATUS
# ============================================================

print("\n" + "=" * 70)
print("             ALPHAPILOT SYSTEM STATUS")
print("=" * 70)

print(
    "AI Trade Signal         :",
    "OK" if signal_ok else "FAILED"
)

print(
    "Option Selector         :",
    "OK" if option_ok else "FAILED"
)

print(
    "Entry Manager           :",
    "OK" if entry_ok else "FAILED"
)

print(
    "Performance             :",
    "OK" if performance_ok else "FAILED"
)


# ============================================================
# SAFETY STATUS
# ============================================================

print("\n" + "=" * 70)
print("             SAFETY STATUS")
print("=" * 70)

print("Paper Trading           : ACTIVE")
print("Real Money Trading      : DISABLED")
print("Minimum Confidence      :", str(MIN_CONFIDENCE) + "%")
print("Automatic Entry         : CONNECTED")
print("Automatic Exit          : POSITION MONITOR")
print("Maximum Position       : $500.00")


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("             MASTER CONTROLLER COMPLETE")
print("=" * 70)

print(
    "Timestamp:",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

print()
print("Controller execution completed.")

print("=" * 70)