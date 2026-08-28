# ============================================================
# ALPHAPILOT AI - RISK MANAGER
# ============================================================

ACCOUNT_SIZE = 100_000

# Maximum percentage of account we are willing
# to risk on a single trade.
MAX_RISK_PERCENT = 1.0

# Maximum total capital allocated to one trade.
MAX_POSITION_PERCENT = 5.0

# Stop loss on option premium.
STOP_LOSS_PERCENT = 30.0

# Take profit on option premium.
TAKE_PROFIT_PERCENT = 60.0


# ============================================================
# 1. CALCULATE MAXIMUM RISK
# ============================================================

def calculate_max_risk(account_size=ACCOUNT_SIZE):

    max_risk = (
        account_size
        * MAX_RISK_PERCENT
        / 100
    )

    return max_risk


# ============================================================
# 2. CALCULATE MAXIMUM POSITION VALUE
# ============================================================

def calculate_max_position_value(
    account_size=ACCOUNT_SIZE
):

    max_position = (
        account_size
        * MAX_POSITION_PERCENT
        / 100
    )

    return max_position


# ============================================================
# 3. CALCULATE CONTRACT COST
# ============================================================

def calculate_contract_cost(option_price):

    # One US options contract normally represents
    # 100 shares.

    return option_price * 100


# ============================================================
# 4. CALCULATE CONTRACT QUANTITY
# ============================================================

def calculate_contract_quantity(
    option_price,
    account_size=ACCOUNT_SIZE
):

    if option_price <= 0:
        return 0

    contract_cost = calculate_contract_cost(
        option_price
    )

    max_risk = calculate_max_risk(
        account_size
    )

    max_position = calculate_max_position_value(
        account_size
    )

    # Maximum number based on risk
    quantity_by_risk = int(
        max_risk / contract_cost
    )

    # Maximum number based on total position size
    quantity_by_position = int(
        max_position / contract_cost
    )

    # Use the more conservative limit
    quantity = min(
        quantity_by_risk,
        quantity_by_position
    )

    return max(quantity, 0)


# ============================================================
# 5. STOP LOSS
# ============================================================

def calculate_stop_loss(option_price):

    return option_price * (
        1 - STOP_LOSS_PERCENT / 100
    )


# ============================================================
# 6. TAKE PROFIT
# ============================================================

def calculate_take_profit(option_price):

    return option_price * (
        1 + TAKE_PROFIT_PERCENT / 100
    )


# ============================================================
# 7. RISK / REWARD
# ============================================================

def calculate_risk_reward(option_price):

    stop_loss = calculate_stop_loss(
        option_price
    )

    take_profit = calculate_take_profit(
        option_price
    )

    risk = option_price - stop_loss
    reward = take_profit - option_price

    if risk <= 0:
        return 0

    return reward / risk


# ============================================================
# 8. RISK GATE
# ============================================================

def risk_gate(
    option_price,
    quantity,
    account_size=ACCOUNT_SIZE
):

    if option_price <= 0:

        return {
            "approved": False,
            "reason": "Invalid option price"
        }

    if quantity <= 0:

        return {
            "approved": False,
            "reason": "Position size is zero"
        }

    contract_cost = calculate_contract_cost(
        option_price
    )

    total_cost = (
        contract_cost * quantity
    )

    max_position = calculate_max_position_value(
        account_size
    )

    max_risk = calculate_max_risk(
        account_size
    )

    stop_loss = calculate_stop_loss(
        option_price
    )

    # Approximate loss if premium falls
    # to stop-loss level.
    loss_per_contract = (
        option_price - stop_loss
    ) * 100

    total_risk = (
        loss_per_contract * quantity
    )

    # --------------------------------------------------------
    # Position size check
    # --------------------------------------------------------

    if total_cost > max_position:

        return {
            "approved": False,
            "reason": "Position size exceeds maximum allowed",
            "total_cost": total_cost,
            "max_position": max_position
        }

    # --------------------------------------------------------
    # Risk check
    # --------------------------------------------------------

    if total_risk > max_risk:

        return {
            "approved": False,
            "reason": "Maximum trade risk exceeded",
            "total_risk": total_risk,
            "max_risk": max_risk
        }

    # --------------------------------------------------------
    # Approved
    # --------------------------------------------------------

    return {

        "approved": True,

        "reason": "Risk checks passed",

        "quantity": quantity,

        "contract_cost": contract_cost,

        "total_cost": total_cost,

        "total_risk": total_risk,

        "max_risk": max_risk,

        "stop_loss": stop_loss,

        "take_profit": calculate_take_profit(
            option_price
        ),

        "risk_reward": calculate_risk_reward(
            option_price
        )
    }


# ============================================================
# 9. TEST RISK MANAGER
# ============================================================

if __name__ == "__main__":

    print("=" * 65)
    print("             ALPHAPILOT AI RISK MANAGER")
    print("=" * 65)

    account_size = 100_000

    # Example premium
    option_price = 2.53

    print(
        f"\nAccount Size       : ${account_size:,.2f}"
    )

    print(
        f"Option Premium     : ${option_price:.2f}"
    )

    max_risk = calculate_max_risk(
        account_size
    )

    max_position = calculate_max_position_value(
        account_size
    )

    quantity = calculate_contract_quantity(
        option_price,
        account_size
    )

    print(
        f"Maximum Trade Risk : ${max_risk:,.2f}"
    )

    print(
        f"Maximum Position   : ${max_position:,.2f}"
    )

    print(
        f"Suggested Quantity : {quantity} contract(s)"
    )

    if quantity > 0:

        result = risk_gate(
            option_price,
            quantity,
            account_size
        )

        print("\n---------------- RISK DECISION ----------------")

        print(
            "Approved           :",
            result["approved"]
        )

        print(
            "Reason             :",
            result["reason"]
        )

        if result["approved"]:

            print(
                f"Total Cost         : "
                f"${result['total_cost']:,.2f}"
            )

            print(
                f"Estimated Risk     : "
                f"${result['total_risk']:,.2f}"
            )

            print(
                f"Stop Loss          : "
                f"${result['stop_loss']:.2f}"
            )

            print(
                f"Take Profit        : "
                f"${result['take_profit']:.2f}"
            )

            print(
                f"Risk/Reward        : "
                f"{result['risk_reward']:.2f}"
            )

    else:

        print("\nNO TRADE")
        print(
            "Option premium is too expensive "
            "for the current risk limits."
        )

    print("\n" + "=" * 65)
    print("             RISK ANALYSIS COMPLETE")
    print("=" * 65)

    print("\nNO ORDER WAS PLACED.")