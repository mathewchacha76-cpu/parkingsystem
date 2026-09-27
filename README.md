# NetGen Parking System 

A modern, web-based parking management system built for a client automating
their parking operations in Kenya.

**Assignment:** Data Structures and Algorithms — Multimedia University of Kenya


## What it does

- Shows drivers live parking bay availability before they enter
- Records each vehicle's arrival time and assigns it a bay
- Calculates the parking fee automatically when a vehicle exits
- Accepts payment by **M-Pesa, Card, or Cash**, then opens the barrier
  only once payment is confirmed
- Lets management **change parking rates at any time**, with no code change
- Keeps a permanent, timestamped **transaction log** for reconciliation and VAT


**Scope (per section 1.3):** in scope — entry lane control, slot monitoring
and display, slot allocation, duration and fee computation, payment
collection, exit barrier control, exception handling, and administrative
reporting. **Out of scope for this phase:** online pre-booking of bays,
valet operations, third-party loyalty integrations, and automated number
plate blacklisting.

## Fee structure (default rates, editable by management)

| Duration        | Fee          |
|------------------|--------------|
| Up to 30 minutes | Free         |
| Up to 2 hours    | Kshs. 50     |
| Up to 4 hours    | Kshs. 100    |
| Up to 6 hours    | Kshs. 300    |
| Over 6 hours     | Kshs. 500    |

These are the *starting* values only — management can change them anytime
at `/admin/rates` without touching the code.

## Tech stack

- **Backend:** Python 3 + Flask
- **Frontend:** HTML + CSS (Jinja2 templates)
- **Data storage:** JSON file (`data/parking_data.json`), acting as a
  dynamic, self-updating database 

## Project structure

```
SmartParkKE/
    app.py                      # Flask app: all 7 modules and routes
    data/
       ── parking_data.json       # Dynamic "database": rates, slots, vehicles, transactions
    templates/
     ─ base.html
     ─ index.html              # Module 1: Slot Display
     ─ entry.html              # Module 2: Vehicle Entry
     ─ exit.html                # Modules 3, 4, 5: Fee, Payment, Barrier
     ─ admin_rates.html         # Module 6: Rate Management
     ─ reports.html             # Module 7: Audit & Reporting
     static/
      ── style.css
```

## Modules

1. **Slot Display Module** — shows free/occupied bays on the home page
2. **Vehicle Entry Module** — records arrival, assigns a bay (with exception handling for full parking / duplicate entry)
3. **Fee Calculation Module** — computes duration and fee on exit, using live rates
4. **Payment Module** — captures payment method (M-Pesa, Card, Cash) and confirms payment
5. **Barrier Control Module** — frees the bay once payment is confirmed
6. **Rate Management Module** — lets management update fee bands at any time, no code change
7. **Audit & Reporting Module** — permanent transaction log with totals, for reconciliation and VAT

## Exception handling

- Empty or duplicate plate on entry
- No available bay ("Parking Full")
- Unknown plate number on exit
- Missing or invalid payment method
- Non-numeric or negative values when updating rates


- Slot display: `/`
- Vehicle entry: `/entry`
- Vehicle exit & payment: `/exit`
- Rate management (admin): `/admin/rates`
- Reports (audit trail): `/reports`

## Data structures used

| Structure | Where | Why |
|---|---|---|
| Dictionary | Active vehicles, keyed by plate number | O(1) lookup on exit |
| List | Parking slots | Simple to iterate and display in order |
| List of dictionaries | Transaction log | Preserves order of events; easy to sum/filter for reports |
| datetime object | Entry/exit timestamps | Accurate duration calculation |
| Nested JSON | Whole system state (rates, slots, vehicles, transactions) | Updates dynamically as cars come and go, and as rates change |
