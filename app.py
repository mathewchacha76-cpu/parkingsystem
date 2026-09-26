"""
SmartPark KE - A Modern Parking Management System


MODULES IMPLEMENTED:
1. Slot Display Module        -> "/"
2. Vehicle Entry Module       -> "/entry"
3. Fee Calculation Module     -> part of "/exit"
4. Payment Module             -> part of "/exit" (confirm step)
5. Barrier Control Module     -> triggered after payment is confirmed
6. Rate Management Module     -> "/admin/rates"
7. Audit & Reporting Module   -> "/reports"
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = "smartpark_secret_key"  # for flash messages

# Path to JSON "database" file
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "parking_data.json")

VALID_PAYMENT_METHODS = ["M-Pesa", "Card", "Cash"]


# DATA HANDLING FUNCTIONS ("dynamic database" operations)


def load_data():
    """Read the current parking data from the JSON file."""
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    """Write updated parking data back to the JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# MODULE 1: SLOT DISPLAY MODULE


@app.route("/")
def index():
    """
    Algorithm:
    1. Load slots data from JSON file
    2. Count how many slots are Free vs Occupied
    3. Display the slot list to the driver before entry
    """
    data = load_data()
    slots = data["slots"]
    free_count = sum(1 for s in slots if s["status"] == "Free")
    return render_template(
        "index.html",
        slots=slots,
        free_count=free_count,
        total_slots=len(slots)
    )


# MODULE 2: VEHICLE ENTRY MODULE (with exception handling)


@app.route("/entry", methods=["GET", "POST"])
def entry():
    """
    Algorithm:
    1. Driver requests entry and types their plate number
    2. EXCEPTION: reject empty plate input
    3. EXCEPTION: reject a plate that is already parked inside
    4. Check slot list for a Free slot
    5. EXCEPTION: if no free slot -> show "Parking Full" message
    6. Otherwise -> assign the first available slot, record entry time,
       mark slot as Occupied, save to JSON, "open" the entry barrier
    """
    data = load_data()

    if request.method == "POST":
        plate = request.form.get("plate", "").strip().upper()

        # Exception: empty input
        if not plate:
            flash("Please enter a valid plate number.", "error")
            return redirect(url_for("entry"))

        # Exception: vehicle already inside
        if plate in data["vehicles"]:
            flash(f"Vehicle {plate} is already parked inside.", "error")
            return redirect(url_for("entry"))

        # Look for a free slot
        free_slot = next((s for s in data["slots"] if s["status"] == "Free"), None)

        # Exception: parking full
        if free_slot is None:
            flash("Sorry, the parking is FULL. No slots available.", "error")
            return redirect(url_for("entry"))

        # Assign the slot and record the vehicle
        free_slot["status"] = "Occupied"
        data["vehicles"][plate] = {
            "slot_id": free_slot["slot_id"],
            "entry_time": datetime.now().isoformat(timespec="seconds"),
            "exit_time": None,
            "fee": None,
            "paid": False
        }
        save_data(data)

        flash(
            f"Barrier open. Vehicle {plate} assigned to Slot {free_slot['slot_id']}.",
            "success"
        )
        return redirect(url_for("index"))

    return render_template("entry.html")


# MODULE 3: FEE CALCULATION MODULE (rates now configurable)


def calculate_fee(entry_time_str, rates):
    """
    Algorithm:
    1. Get entry_time from record; get exit_time (now)
    2. duration = exit_time - entry_time (in minutes)
    3. Compare duration against the CURRENT rate bands (read from data,
       so management can change them without a software change)
    4. Return duration (minutes) and fee owed
    """
    entry_time = datetime.fromisoformat(entry_time_str)
    exit_time = datetime.now()
    duration_minutes = (exit_time - entry_time).total_seconds() / 60

    if duration_minutes <= rates["free_minutes"]:
        fee = 0
    elif duration_minutes <= rates["band1_minutes"]:
        fee = rates["band1_fee"]
    elif duration_minutes <= rates["band2_minutes"]:
        fee = rates["band2_fee"]
    elif duration_minutes <= rates["band3_minutes"]:
        fee = rates["band3_fee"]
    else:
        fee = rates["over_limit_fee"]

    return duration_minutes, fee, exit_time


# MODULE 4 & 5: PAYMENT MODULE + BARRIER CONTROL MODULE


@app.route("/exit", methods=["GET", "POST"])
def exit_vehicle():
    """
    Handles both:
    - Step 1: driver enters plate number -> system calculates fee (Module 3)
    - Step 2: driver picks a payment method and confirms -> Module 4 marks
      as paid and writes an audit record, then Module 5 (barrier) opens
      and frees the slot
    """
    data = load_data()

    if request.method == "POST":
        plate = request.form.get("plate", "").strip().upper()
        action = request.form.get("action")

        vehicle = data["vehicles"].get(plate)

        # Exception: unknown plate
        if not vehicle:
            flash(f"No record found for plate {plate}. Check and try again.", "error")
            return redirect(url_for("exit_vehicle"))

        if action == "calculate":
            # MODULE 3: Fee Calculation
            duration_minutes, fee, exit_time = calculate_fee(vehicle["entry_time"], data["rates"])
            vehicle["exit_time"] = exit_time.isoformat(timespec="seconds")
            vehicle["fee"] = fee
            save_data(data)

            return render_template(
                "exit.html",
                plate=plate,
                duration=round(duration_minutes, 1),
                fee=fee,
                payment_methods=VALID_PAYMENT_METHODS,
                show_payment=True
            )

        elif action == "pay":
            # Exception: reject an invalid/missing payment method
            payment_method = request.form.get("payment_method", "")
            if payment_method not in VALID_PAYMENT_METHODS:
                flash("Please select a valid payment method.", "error")
                return redirect(url_for("exit_vehicle"))

            # MODULE 4: Payment Module
            vehicle["paid"] = True
            vehicle["payment_method"] = payment_method

            # MODULE 5: Barrier Control Module
            slot_id = vehicle["slot_id"]
            for slot in data["slots"]:
                if slot["slot_id"] == slot_id:
                    slot["status"] = "Free"
                    break

            # MODULE 7: Audit & Reporting - write a permanent transaction
            # record BEFORE the vehicle entry is removed, for
            # reconciliation and VAT purposes
            data["transactions"].append({
                "plate": plate,
                "slot_id": slot_id,
                "entry_time": vehicle["entry_time"],
                "exit_time": vehicle["exit_time"],
                "duration_minutes": round(
                    (datetime.fromisoformat(vehicle["exit_time"]) -
                     datetime.fromisoformat(vehicle["entry_time"])).total_seconds() / 60, 1
                ),
                "fee": vehicle["fee"],
                "payment_method": payment_method,
                "paid_at": datetime.now().isoformat(timespec="seconds")
            })

            fee_paid = vehicle["fee"]
            del data["vehicles"][plate]
            save_data(data)

            flash(
                f"Payment of Kshs. {fee_paid} received via {payment_method}. "
                f"Barrier open. Slot {slot_id} is now free. Safe travels!",
                "success"
            )
            return redirect(url_for("index"))

    return render_template("exit.html", show_payment=False)


# MODULE 6: RATE MANAGEMENT MODULE


@app.route("/admin/rates", methods=["GET", "POST"])
def admin_rates():
    """
    Algorithm:
    1. Load current rates from the JSON data store
    2. Display them in an editable form to management
    3. On submit, validate each value is a non-negative number
    4. Save the updated rates back to the data store
    5. All future fee calculations immediately use the new rates -
       no code change or redeployment needed
    """
    data = load_data()

    if request.method == "POST":
        try:
            new_rates = {
                "free_minutes": int(request.form["free_minutes"]),
                "band1_minutes": int(request.form["band1_minutes"]),
                "band1_fee": int(request.form["band1_fee"]),
                "band2_minutes": int(request.form["band2_minutes"]),
                "band2_fee": int(request.form["band2_fee"]),
                "band3_minutes": int(request.form["band3_minutes"]),
                "band3_fee": int(request.form["band3_fee"]),
                "over_limit_fee": int(request.form["over_limit_fee"]),
            }
        except (ValueError, KeyError):
            # Exception: non-numeric or missing input
            flash("All rate fields must be whole numbers.", "error")
            return redirect(url_for("admin_rates"))

        # Exception: reject negative values
        if any(v < 0 for v in new_rates.values()):
            flash("Rates cannot be negative.", "error")
            return redirect(url_for("admin_rates"))

        data["rates"] = new_rates
        save_data(data)
        flash("Parking rates updated successfully.", "success")
        return redirect(url_for("admin_rates"))

    return render_template("admin_rates.html", rates=data["rates"])


# MODULE 7: AUDIT & REPORTING MODULE


@app.route("/reports")
def reports():
    """
    Algorithm:
    1. Load the transaction log from the JSON data store
    2. Sum all fees collected -> total revenue
    3. Group totals by payment method (M-Pesa / Card / Cash)
    4. Display an itemised, timestamped list for reconciliation and VAT
    """
    data = load_data()
    transactions = list(reversed(data["transactions"]))  # newest first

    total_revenue = sum(t["fee"] for t in transactions)

    by_method = {}
    for method in VALID_PAYMENT_METHODS:
        by_method[method] = sum(t["fee"] for t in transactions if t["payment_method"] == method)

    return render_template(
        "reports.html",
        transactions=transactions,
        total_revenue=total_revenue,
        by_method=by_method,
        transaction_count=len(transactions)
    )


if __name__ == "__main__":
    app.run(debug=True)
