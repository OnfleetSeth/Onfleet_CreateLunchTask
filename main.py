import requests
import json
import base64
import datetime
import pprint as p

api_key = "b4523670d4ba81be1c6a2084776093eb"


def encode_b64(to_encode):
    bytes = to_encode.encode('ascii')
    base64_bytes = base64.b64encode(bytes)
    encoded_b64 = base64_bytes.decode('ascii')

    return encoded_b64


def get_break_schedule(worker_id=None, date=None):

    if not worker_id:
        print("Please provide worker id.")
        return

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


def break_duration(worker_id=None, date=None):
    break_time = get_break_schedule(worker_id=worker_id, date=date)
    duration_min = (break_time[1] - break_time[0]) / 1000 / 60

    return duration_min


def get_hub_address():
    url = "https://onfleet.com/api/v2/hubs"

    payload = {}
    headers = {
        'Authorization': 'Basic ' + encode_b64(api_key)
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    # print(response.text)
    addy = (json.loads(response.text))[0]['address']
    # print(addy)
    print(addy)
    return addy


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


def update_worker_metadata(worker_id=None):

    if not worker_id:
        print("No worker id.")
        return

    url = f"https://onfleet.com/api/v2/workers/{worker_id}"

    payload = json.dumps({
        "metadata": [
            {"name": "Has Lunch Task?", "type": "boolean", "value": True, "visibility": ["api", "dashboard"]}
            ],
    })

    headers = {
        'Authorization': 'Basic ' + encode_b64(api_key),
        'Content-Type': 'text/plain'
    }

    response = requests.request("PUT", url, headers=headers, data=payload)

    return response


def create_break_task(worker_id, date=None, location="hub"):

    check = check_for_lunch_task()

    if worker_id in check:

        if location == "hub":
            address = get_hub_address()
            address["name"] = "THIS IS YOUR LUNCH TASK"
        else:
            address = location
            address["name"] = "THIS IS YOUR LUNCH TASK"

        break_time = get_break_schedule(worker_id=worker_id, date=date)
        break_start = break_time[0]

        url = "https://onfleet.com/api/v2/tasks"

        payload = json.dumps({
            "destination": {
                "address":
                    address
                ,
            },
            "recipients": [
            ],
            "recipientName": "Driver (You): Seth",
            "completeAfter": break_start,
            "serviceTime": 60,
            "appearance": {"triangleColor": 2},
            "container": {"type": "WORKER", "worker": worker_id},
            "notes": "THIS IS YOUR LUNCH TASK"
        })
        headers = {
            'Authorization': 'Basic ' + encode_b64(api_key),
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        print(response.text)

    update_worker_metadata(worker_id=worker_id)


create_break_task(worker_id="KBH7vaqrLlx78it3162omPDE", date="2022-01-01", location="hub")

# update_worker_metadata(worker_id="KBH7vaqrLlx78it3162omPDE")

# check_for_lunch_task()