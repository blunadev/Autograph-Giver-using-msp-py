import time
import hashlib
import binascii
import random
import base64
import msp_tls_client
from typing import List, Union
from datetime import date, datetime
from pyamf import remoting, ASObject, TypedObject, AMF3, amf3
from secrets import token_hex
from colorama import Fore, Style, init

# Initialize Colorama for colored output
init(autoreset=True)

COOLDOWN_SECONDS = 120  # 2 minutes cooldown

# ===== MSP Functions (merged from msp.py) =====
def get_marking_id() -> int:
    marking_id = random.randint(2**0, 2**32)
    return marking_id

def ticket_header(ticket: str) -> ASObject:
    marking_id = get_marking_id()
    marking_id_bytes = str(marking_id).encode('utf-8')
    marking_id_hash = hashlib.md5(marking_id_bytes).hexdigest()
    marking_id_hex = binascii.hexlify(marking_id_bytes).decode()
    return ASObject({"Ticket": ticket + marking_id_hash + marking_id_hex, "anyAttribute": None})

def calculate_checksum(arguments: Union[int, str, bool, bytes, List[Union[int, str, bool, bytes]],
                                       dict, date, datetime, ASObject, TypedObject]) -> str:
    checked_objects = {}
    no_ticket_value = "XSV7%!5!AX2L8@vn"
    salt = "2zKzokBI4^26#oiP"

    def from_object(obj):
        if obj is None:
            return ""
        if isinstance(obj, (int, str, bool)):
            return str(obj)
        if isinstance(obj, amf3.ByteArray):
            return from_byte_array(obj)
        if isinstance(obj, (date, datetime)):
            return str(obj.year) + str(obj.month - 1) + str(obj.day)
        if isinstance(obj, (list, dict)) and "Ticket" not in obj:
            return from_array(obj)
        return ""

    def from_byte_array(bytes):
        if len(bytes) <= 20:
            return bytes.getvalue().hex()
        num = len(bytes) // 20
        array = bytearray(20)
        for i in range(20):
            bytes.seek(num * i)
            array[i] = bytes.read(1)[0]
        return array.hex()

    def from_array(arr):
        result = ""
        for item in arr:
            if isinstance(item, (ASObject, TypedObject)):
                result += from_object(item)
            else:
                result += from_object_inner(item)
        return result

    def get_ticket_value(arr):
        for obj in arr:
            if isinstance(obj, ASObject) and "Ticket" in obj:
                ticket_str = obj["Ticket"]
                if ',' in ticket_str:
                    ticket_parts = ticket_str.split(',')
                    return ticket_parts[0] + ticket_parts[5][-5:]
        return no_ticket_value

    def from_object_inner(obj):
        result = ""
        if isinstance(obj, dict):
            for key in sorted(obj.keys()):
                result += from_object(obj[key])
                checked_objects[key] = True
        else:
            result += from_object(obj)
        return result

    result_str = from_object_inner(arguments) + salt + get_ticket_value(arguments)
    return hashlib.sha1(result_str.encode()).hexdigest()

def invoke_method(server: str, method: str, params: list, session_id: str) -> tuple[int, any]:
    if server.lower() == "uk":
        server = "gb"
    req = remoting.Request(target=method, body=params)
    event = remoting.Envelope(AMF3)
    event.headers = remoting.HeaderCollection({
        ("sessionID", False, session_id),
        ("needClassName", False, False),
        ("id", False, calculate_checksum(params))
    })
    event['/1'] = req
    encoded_req = remoting.encode(event).getvalue()
    full_endpoint = f"https://ws-{server}.mspapis.com/Gateway.aspx?method={method}"
    session = msp_tls_client.Session(client_identifier="xerus_ja3_spoof", force_http1=True)
    headers = {
        "Referer": "app:/cache/t1.bin/[[DYNAMIC]]/2",
        "Accept": ("text/xml, application/xml, application/xhtml+xml, "
                   "text/html;q=0.9, text/plain;q=0.8, text/css, image/png, "
                   "image/jpeg, image/gif;q=0.8, application/x-shockwave-flash, "
                   "video/mp4;q=0.9, flv-application/octet-stream;q=0.8, "
                   "video/x-flv;q=0.7, audio/mp4, application/futuresplash, "
                   "/;q=0.5, application/x-mpegURL"),
        "x-flash-version": "32,0,0,100",
        "Content-Type": "application/x-amf",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "Mozilla/5.0 (Windows; U; en) AppleWebKit/533.19.4 "
                      "(KHTML, like Gecko) AdobeAIR/32.0",
        "Connection": "Keep-Alive",
    }
    response = session.post(full_endpoint, data=encoded_req, headers=headers)
    resp_data = response.content if response.status_code == 200 else None
    if response.status_code != 200:
        return (response.status_code, resp_data)
    return (response.status_code, remoting.decode(resp_data)["/1"].body)

def get_session_id() -> str:
    return base64.b64encode(token_hex(23).encode()).decode()

# ===== ASCII Banner =====
def print_banner():
    banner = (
        Fore.RED +
        "      ██╗██╗███╗   ███╗███████╗\n"
        "      ██║██║████╗ ████║██╔════╝\n"
        "      ██║██║██╔████╔██║███████╗\n"
        " ██   ██║██║██║╚██╔╝██║╚════██║\n"
        " ╚█████╔╝██║██║ ╚═╝ ██║███████║\n"
        "  ╚════╝ ╚═╝╚═╝     ╚═╝╚══════╝\n"
        + Style.RESET_ALL
    )
    print(banner)
    print(Fore.LIGHTWHITE_EX + "  MSP Multi-Target Autograph Tool by JIMS\n")

# ===== Core Login / Autograph Functions =====
def login(username, password, server):
    code, resp = invoke_method(
        server,
        "MovieStarPlanet.WebService.User.AMFUserServiceWeb.Login", 
        [
            username,
            password,
            [],
            None,
            None,
            "MSP1-Standalone:XXXXXX"
        ],
        get_session_id()
    )
    if code != 200:
        raise Exception(Fore.RED + f"Login request failed with HTTP code {code}")
    status = resp.get('loginStatus', {}).get('status')
    if status != "Success":
        raise Exception(Fore.RED + f"Login failed, status: {status}")
    ticket = resp['loginStatus']['ticket']
    actor_id = resp['loginStatus']['actor']['ActorId']
    return ticket, actor_id

def get_actor_id_by_name(server, name, session_id):
    code, resp = invoke_method(
        server,
        "MovieStarPlanet.WebService.AMFActorService.GetActorIdByName",
        [name],
        session_id
    )
    if code != 200:
        raise Exception(Fore.RED + f"GetActorIdByName failed with HTTP code {code}")
    return resp

def give_autograph(server, ticket, giver_actor_id, receiver_actor_id, session_id):
    code, resp = invoke_method(
        server,
        "MovieStarPlanet.WebService.UserSession.AMFUserSessionService.GiveAutographAndCalculateTimestamp",
        [
            ticket_header(ticket),
            giver_actor_id,
            receiver_actor_id,
        ],
        session_id
    )
    if code != 200:
        raise Exception(Fore.RED + f"GiveAutograph failed with HTTP code {code}")
    return resp

# ===== Main Script =====
def main():
    print_banner()
    USERNAME = input(Fore.YELLOW + "Enter your MSP username: " + Style.RESET_ALL).strip()
    PASSWORD = input(Fore.YELLOW + "Enter your MSP password: " + Style.RESET_ALL).strip()
    SERVER = input(Fore.YELLOW + "Enter MSP server (e.g. US, GB, DE): " + Style.RESET_ALL).strip().upper()
    targets = []
    print(Fore.CYAN + "Enter up to 10 target usernames (press Enter to finish):" + Style.RESET_ALL)
    for i in range(10):
        name = input(Fore.GREEN + f"Target {i+1}: " + Style.RESET_ALL).strip()
        if not name:
            break
        targets.append(name)
    if not targets:
        print(Fore.RED + "No targets provided. Exiting.")
        return
    try:
        print(Fore.MAGENTA + "\nLogging in..." + Style.RESET_ALL)
        ticket, my_actor_id = login(USERNAME, PASSWORD, SERVER)
        print(Fore.GREEN + f"Logged in successfully! Your Actor ID: {my_actor_id}" + Style.RESET_ALL)
        session_id = get_session_id()
        target_actor_ids = []
        for name in targets:
            print(Fore.CYAN + f"Fetching actor ID for '{name}'..." + Style.RESET_ALL)
            actor_id = get_actor_id_by_name(SERVER, name, session_id)
            target_actor_ids.append((name, actor_id))
        print(Fore.GREEN + "All target IDs fetched successfully!\n" + Style.RESET_ALL)
        while True:
            for name, actor_id in target_actor_ids:
                print(Fore.YELLOW + f"Sending autograph to {name} (Actor ID: {actor_id})..." + Style.RESET_ALL)
                response = give_autograph(SERVER, ticket, my_actor_id, actor_id, session_id)
                print(Fore.GREEN + f"Autograph sent to {name}!" + Style.RESET_ALL)
                print(Fore.LIGHTBLACK_EX + str(response) + Style.RESET_ALL)
                print(Fore.MAGENTA + f"Waiting {COOLDOWN_SECONDS} seconds before the next target...\n" + Style.RESET_ALL)
                time.sleep(COOLDOWN_SECONDS)
    except KeyboardInterrupt:
        print(Fore.RED + "\nScript stopped by user." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + "Error: " + str(e) + Style.RESET_ALL)

if __name__ == "__main__":
    main()
