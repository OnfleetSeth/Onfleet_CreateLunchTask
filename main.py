import requests
import json
import base64
import datetime

api_key = "b4523670d4ba81be1c6a2084776093eb"


def encode_b64(to_encode):
    encoded_ascii = to_encode.encode('ascii')
    base64_bytes = base64.b64encode(encoded_ascii)
    encoded_b64 = base64_bytes.decode('ascii')

    return encoded_b64


# Assumption: The second set of scheduled hours for a driver represents their break time
def get_break_schedule(worker_id=None, date=None):

    if not worker_id:
        print("Please provide worker id.")
        return

    # If no date is provided, fetch today's date
    if not date:
        date = datetime.date.today()

    url = f"https://onfleet.com/api/v2/workers/{worker_id}/schedule"

    payload = {}
    headers = {
        'Authorization': 'Basic ' + encode_b64(api_key)
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    j_response = json.loads(response.text)
    entries = j_response['entries']

    i = 0
    while i < len(entries):

        schedule_date = entries[i]['date']

        if schedule_date == str(date):
            shifts = entries[i]['shifts']
            break_start = shifts[1][0]
            break_end = shifts[1][1]
            break_time = (break_start, break_end)

            return break_time
        else:
            i += 1


# Break duration will map to the Service Time on break task
def break_duration(worker_id=None, date=None):
    break_time = get_break_schedule(worker_id=worker_id, date=date)
    duration_min = (break_time[1] - break_time[0]) / 1000 / 60  # Convert from epoch in milliseconds to minutes

    return duration_min


# Get the hub for this worker's team
# If a worker is on multiple teams, we're just picking the first
def get_hub(worker):

    if not worker:
        print("Provide a worker to find the hub.")

    team_id = worker.team

    url = f"https://onfleet.com/api/v2/teams/{team_id}"

    payload = {}
    headers = {
        'Authorization': 'Basic ' + encode_b64(api_key)
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    hub = (json.loads(response.text))['hub']

    return get_hub_address(hub)


# Get the address for the hub
# This will become the destination on the break task
def get_hub_address(hub):

    url = "https://onfleet.com/api/v2/hubs"

    payload = {}
    headers = {
        'Authorization': 'Basic ' + encode_b64(api_key)
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    json_response = json.loads(response.text)

    i = 0
    while i < len(json_response):
        if json_response[i]['id'] == hub:
            addy = json_response[i]['address']
            return addy
        else:
            i += 1


# Evaluate whether driver already has a lunch task based on boolean flag to be set in metadata
# Flag set to True after creating lunch task, set to False when driver goes Off-Duty
def check_for_lunch_task():
    url = "https://onfleet.com/api/v2/workers/metadata"

    payload = json.dumps([
        {
            "name": "Has Lunch Task?",
            "type": "boolean",
            "value": False
        }
    ])

    headers = {
        'Authorization': 'Basic ' + encode_b64(api_key),
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    needs_lunch = []

    for worker in json.loads(response.text):
        needs_lunch.append(worker['id'])

    print(needs_lunch)
    return needs_lunch


# Set boolean flag in task metadata indicating that a lunch task has been created to True
# When driver goes Off Duty - set boolean flag back to False
# Allows querying of metadata
def set_lunch_flag(status, worker_id=None):

    if not worker_id:
        print("No worker id.")
        return

    url = f"https://onfleet.com/api/v2/workers/{worker_id}"

    if status == "on_duty":
        payload = json.dumps({
            "metadata": {"$set": [
                {"name": "Has Lunch Task?", "type": "boolean", "value": True, "visibility": ["api", "dashboard"]}],
            }})

    elif status == "off_duty":
        print("off-duty")
        payload = json.dumps({
            "metadata": {"$set": [
                {"name": "Has Lunch Task?", "type": "boolean", "value": False, "visibility": ["api", "dashboard"]}],
            }})

    headers = {
        'Authorization': 'Basic ' + encode_b64(api_key),
        'Content-Type': 'text/plain'
    }

    response = requests.request("PUT", url, headers=headers, data=payload)

    return response


# Adjust the driver's route to insert break at the correct position in the route
def run_auto_dispatch(team_id):
    url = f"https://onfleet.com/api/v2/teams/{team_id}/dispatch"

    payload = {}
    headers = {
        'Authorization': 'Basic ' + encode_b64(api_key),
        'Content-Type': 'text/plain'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.text)
    return


# Check if driver needs a break task, create the task, set the metadata flag to True, execute Auto-Dispatch
def create_break_task(worker, date=None, location="hub"):

    check = check_for_lunch_task()

    if worker.id in check:

        if location == "hub":
            address = get_hub(worker)
            address["name"] = "THIS IS YOUR LUNCH TASK"
        else:
            address = location
            address["name"] = "THIS IS YOUR LUNCH TASK"

        break_time = get_break_schedule(worker_id=worker.id, date=date)
        break_start = break_time[0]

        latest_break_end = break_start + (2*60*60*1000)  # Add two hours

        url = "https://onfleet.com/api/v2/tasks"

        payload = json.dumps({
            "destination": {
                "address":
                    address,
            },
            "recipients": [
            ],
            "recipientName": worker.name,
            "completeAfter": break_start,
            "completeBefore": latest_break_end,
            "serviceTime": 60,
            "appearance": {"triangleColor": 2},
            "container": {"type": "WORKER", "worker": worker.id},
            "notes": "THIS IS YOUR LUNCH TASK"
        })
        headers = {
            'Authorization': 'Basic ' + encode_b64(api_key),
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        print(response.text)

    set_lunch_flag("on_duty", worker_id=worker.id)

    run_auto_dispatch(worker.team)

    return
