#!/usr/bin/env python3
import pprint
import requests
from datetime import datetime

HOST_NAME = "dev.example.com"
SITE_NAME = "dev"


API_URL = f"https://{HOST_NAME}/{SITE_NAME}/check_mk/api/1.0"

USERNAME = "automation"
PASSWORD = 'PW'

host_dict = {}
ruleset_list = []
success_remove = ""
error_remove   = ""
success_update = ""
error_update   = ""

def log_writer(path, message):
    print(message)
    with open(path, 'a') as log_file:
         log_file.write(message)
         log_file.close()
    return ""


session = requests.session()
session.headers['Authorization'] = f"Bearer {USERNAME} {PASSWORD}"
session.headers['Accept'] = 'application/json'
session.verify = '/etc/ssl/certs/ca-bundle.trust.crt'

host_resp = session.get(
    f"{API_URL}/domain-types/host_config/collections/all",
    params={  # goes into query string
        "effective_attributes": False,  # Show all effective attributes on hosts, not just the attributes which were set on this host specifically.
    },
)
if host_resp.status_code == 200:
    for host in host_resp.json()['value']: host_dict[host['id']] = ""
else:
    exit("query all host failed")

ruleset_resp = session.get(
    f"{API_URL}/domain-types/ruleset/collections/all",
    params={  # goes into query string
    },
)

if ruleset_resp.status_code == 200:
    for ruleset in ruleset_resp.json()['value']: ruleset_list.append(ruleset['id'])
else:
    exit("query all host failed")

for ruleset in ruleset_list:
    #log_writer(f"./{SITE_NAME}_{ruleset}_cleanup.log",f"\033[91mworking on ruleset {ruleset}\033[0m")
    resp = session.get(
        f"{API_URL}/domain-types/rule/collections/all",
        params={  # goes into query string
            "ruleset_name": ruleset,  # (required) The name of the ruleset.
        },
    )
    
    if resp.status_code == 200:
        for rule in resp.json()['value']:
            #log_writer(f"./{SITE_NAME}_{ruleset}_cleanup.log",f"working on rule nr#{i}: {rule['id']}")
            if rule['extensions']['conditions'].get('host_name') is not None :
                removed_hosts = []
                extensions = rule['extensions']
                for item in rule['extensions']['conditions']['host_name']['match_on']:
                    #host match is not regex
                    if item[0] == "~": 
                        continue
                    # host does not exist in wato
                    if item not in host_dict:
                        # list of to remove hosts
                        removed_hosts.append(item)
                # remove hosts from conditions
                for item in removed_hosts:
                    extensions['conditions']['host_name']['match_on'].remove(item)
                # if no hosts are left as condistions => delete rule
                if len(extensions['conditions']['host_name']['match_on']) == 0:
                    del_resp = session.delete(rule['links'][0]['href'], timeout=180)
                    if del_resp.status_code  == 204:
                        success_remove += f"{rule['extensions']['ruleset']}; Folder and Index{rule['extensions']['folder']} {rule['extensions']['folder_index']}; Rule for host(s) {', '.join(removed_hosts)} has been removed\n" 
                    else:
                        error_remove   += f"{rule['extensions']['ruleset']}; Folder and Index{rule['extensions']['folder']} {rule['extensions']['folder_index']}; Error removing Rule for host(s) {', '.join(removed_hosts)}\n" 
                # else update the rule with the now cleand condistions
                else:
                    # add comment
                    extensions['properties']['comment'] = f"{datetime.today().strftime('%Y-%m-%d')} cleanup script removed these host(s) {', '.join(removed_hosts)}\n"+ extensions['properties'].get('comment', "") 
                    update_resp = session.put(
                        f"{API_URL}/objects/rule/{rule['id']}",
                        headers={
                            "If-Match": f'{resp.headers["ETag"]}',
                            "Content-Type": 'application/json',
                        },
                        json={
                            "properties": extensions['properties'],
                            "value_raw":  extensions['value_raw'],
                            "conditions": extensions['conditions'],
                        },
                    )
                    if update_resp.status_code  == 200:
                        success_update += f"{rule['extensions']['ruleset']}; Folder and Index{rule['extensions']['folder']} {rule['extensions']['folder_index']};{', '.join(removed_hosts)} have been removed from rule\n"
                    else:
                        error_update   += f"{rule['extensions']['ruleset']}; Folder and Index{rule['extensions']['folder']} {rule['extensions']['folder_index']};Error removing {', '.join(removed_hosts)}\n"
    
    elif resp.status_code == 204:
        print("Done")
    else:
        raise RuntimeError(pprint.pformat(resp.json()))

log_writer(f"./{SITE_NAME}_success_remove.log",f"sucessfuly removed:\n{success_remove}")
log_writer(f"./{SITE_NAME}_error_remove.log"  ,f"ERROR removed:\n{error_remove}")
log_writer(f"./{SITE_NAME}_success_update.log",f"sucessfuly update:\n{success_update}")
log_writer(f"./{SITE_NAME}_error_update.log"  ,f"ERROR update:\n{error_update}")


