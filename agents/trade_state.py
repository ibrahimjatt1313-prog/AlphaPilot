import json
from pathlib import Path
from datetime import datetime

STATE_FILE = Path(__file__).resolve().parent / "trade_state.json"


def load_state():
    if not STATE_FILE.exists():
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    temp_file = STATE_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    temp_file.replace(STATE_FILE)


def clear_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def is_open():
    state = load_state()
    return state.get("status") in ("OPEN", "EXIT_PENDING")


def create_open_trade(
    symbol,
    quantity,
    entry_price,
    entry_order_id,
):
    state = {
        "symbol": symbol,
        "quantity": quantity,
        "entry_price": float(entry_price),
        "entry_value": float(entry_price) * int(quantity) * 100,
        "entry_time": datetime.now().isoformat(timespec="seconds"),
        "entry_order_id": str(entry_order_id),
        "exit_order_id": None,
        "status": "OPEN",
    }

    save_state(state)
    return state


def mark_exit_pending(exit_order_id):
    state = load_state()

    if not state:
        return

    state["exit_order_id"] = str(exit_order_id)
    state["status"] = "EXIT_PENDING"

    save_state(state)


def mark_exit_open():
    state = load_state()

    if not state:
        return

    state["exit_order_id"] = None
    state["status"] = "OPEN"

    save_state(state)