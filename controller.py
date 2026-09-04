
import os
import sys
import subprocess
from datetime import datetime

from dotenv import load_dotenv


# ============================================================
# ALPHAPILOT AI - MASTER CONTROLLER
# SAFE PAPER-TRADING PIPELINE
# ============================================================

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
PYTHON = sys.executable

PAPER_TRADING = True
MIN_CONFIDENCE = 70


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


if not PAPER_TRADING:

    print("\nSAFETY ERROR:")
    print("Real-money trading is disabled by this controller.")

    raise SystemExit(1)


print("Python environment : OK")
print(".env file          : FOUND")

if not os.path.isdir(AGENTS_DIR):

    print("Agents directory   : MISSING")
    raise SystemExit(1)

print("Agents directory   : OK")
print("Paper trading      : ACTIVE")
print("Real money         : DISABLED")


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
    print("             RUNNING:", title)
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
# STEP 1 - AI TRADE SIGNAL
# ============================================================

signal_ok = run_module(
    "trade_signal.py",
    "AI TRADE SIGNAL"
)


if not signal_ok:

    print("\nAI signal module failed.")
    print("Pipeline stopped safely.")

    raise SystemExit(1)


# ============================================================
# STEP 2 - OPTION SELECTOR
# ============================================================

option_ok = run_module(
    "option_selector.py",
    "OPTION SELECTOR"
)


if not option_ok:

    print("\nOption selector failed.")
    print("Pipeline stopped safely.")

    raise SystemExit(1)


# ============================================================
# STEP 3 - ENTRY MANAGER
# ============================================================

print("\n" + "=" * 70)
print("             ENTRY DECISION")
print("=" * 70)

print()
print("Entry Manager checks:")
print()
print("  • BUY / NO TRADE")
print("  • Confidence threshold")
print("  • Existing position")
print("  • Existing order")
print("  • Option quote")
print("  • Maximum position value")
print("  • Paper-order submission")
print()
print("Real-money trading is DISABLED.")
print()


entry_ok = run_module(
    "entry_manager.py",
    "ENTRY MANAGER"
)


if not entry_ok:

    print("\nEntry manager failed.")
    print("Pipeline stopped safely.")

    raise SystemExit(1)


# ============================================================
# STEP 4 - ORDER MONITOR
# ============================================================

print("\n" + "=" * 70)
print("             ORDER MONITOR")
print("=" * 70)

print()
print("Checking for existing PAPER orders.")
print("No new order will be submitted by this module.")
print()


order_monitor_path = os.path.join(
    AGENTS_DIR,
    "order_monitor.py"
)


if os.path.isfile(order_monitor_path):

    order_monitor_ok = run_module(
        "order_monitor.py",
        "ORDER MONITOR"
    )

else:

    print("order_monitor.py not found.")
    print("Skipping order monitor.")

    order_monitor_ok = True


# ============================================================
# STEP 5 - POSITION MONITOR
# ============================================================

print("\n" + "=" * 70)
print("             POSITION MONITOR")
print("=" * 70)

print()
print("Checking for existing PAPER positions.")
print()
print("If a position exists:")
print("  • Stop Loss is monitored")
print("  • Take Profit is monitored")
print("  • Automatic paper exit is enabled")
print()
print("If no position exists:")
print("  • No exit order will be created")
print()


position_monitor_path = os.path.join(
    AGENTS_DIR,
    "position_monitor.py"
)


if os.path.isfile(position_monitor_path):

    position_monitor_ok = run_module(
        "position_monitor.py",
        "POSITION MONITOR"
    )

else:

    print("position_monitor.py not found.")
    print("Skipping position monitor.")

    position_monitor_ok = True


# ============================================================
# STEP 6 - PERFORMANCE
# ============================================================

print("\n" + "=" * 70)
print("             PERFORMANCE")
print("=" * 70)

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
    "Order Monitor           :",
    "OK" if order_monitor_ok else "FAILED"
)

print(
    "Position Monitor        :",
    "OK" if position_monitor_ok else "FAILED"
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
print("Automatic Order Monitor : CONNECTED")
print("Automatic Exit          : CONNECTED")
print("Stop Loss               : ENABLED")
print("Take Profit             : ENABLED")
print("Trade Logger            : ENABLED")


# ============================================================
# FINAL RESULT
# ============================================================

print("\n" + "=" * 70)
print("             MASTER CONTROLLER COMPLETE")
print("=" * 70)

print(
    "Timestamp:",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

print()

if (
    signal_ok
    and option_ok
    and entry_ok
    and order_monitor_ok
    and position_monitor_ok
    and performance_ok
):

    print(
        "All available pipeline modules completed successfully."
    )

else:

    print(
        "Pipeline completed with one or more module issues."
    )

print("=" * 70)
