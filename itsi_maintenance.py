# Created 01/16/2020
# Author: Mike McGrail
# Usage: Retrieve entity key and create ITSI maintenance window. This works for testing but is not production-ready.
# Example call: itsi_maintenance.py --action create --title "Test Maintenance Window" --type entity --include emilyserver01 --length 86400
# Note: In our environment, we found using one always-present maintenance window is easiest to add/remove devices (instead of creating a new maintenance window every time)

import sys
import json
import argparse
import datetime
import logging
from pathlib import Path

import requests


def itsi_env():    #Function to specify ITSI environment host and API port (default is 8089)
    itsi_host = '<Splunk_Search_Head_hostname_here>'
    itsi_port = '8089'
    return itsi_host + ':' + itsi_port


def itsi_creds():    #Function to handle credentials. [obviously] Do not use plain-text in production, use an API call to a password vault or something similar.
    itsi_n = '<username>'
    itsi_p = '<password>'
    return itsi_n, itsi_p


def set_logfile():
    logfile=Path(__file__).stem + '.log'
    return logfile


def get_key(itsi_type, itsi_title):    #Function to return ITSI key for a given entity 
    itsi_host = itsi_env()
    itsi_u, itsi_p = itsi_creds()
    if itsi_type == 'entity':    #future functionality; to do: add _key mapping for services
        try:
            logging.debug('Getting _key for entity %s', itsi_title)
            url = 'https://' + itsi_host + '/servicesNS/nobody/SA-ITOA/itoa_interface/entity/?fields=title,_key&filter={"title":"' + itsi_title + '"}'
            res = requests.get(url, auth=(itsi_u, itsi_p), verify=False)
            logging.debug(res.text)
            response = res.json()[0]
            return(response['_key'])
        except:
            logging.debug('No _key found for entity %s', itsi_title)
            return("-")
    elif itsi_type == 'maintenance':
        logging.debug('Getting _key for maintenance %s', itsi_title)
        url = 'https://' + itsi_host + '/servicesNS/nobody/SA-ITOA/maintenance_services_interface/maintenance_calendar/?fields=title,_key&filter={"title":"' + itsi_title + '"}'
        res = requests.get(url, auth=(itsi_u, itsi_p), verify=False)
        logging.debug(res.text)
        response = res.json()[0]
        return(response['_key'])


def maint_window(maint_action, maint_title, maint_type, maint_include, maint_length):
    itsi_host = itsi_env()
    itsi_u, itsi_p = itsi_creds()
    url = 'https://' + itsi_host + '/servicesNS/nobody/SA-ITOA/maintenance_services_interface/maintenance_calendar/'

    if maint_action=='create':
        logging.info('Creating maintenance window title=%s', maint_title)
        body = {
            "title":maint_title,
            "comment":"Created by " + itsi_u,
            "start_time":"0",
            "end_time":maint_length,
            "objects":[]
        }
        if ',' in maint_include:    #Handle comma-separated list of entities
            maint_list = maint_include.split(',')
            for i in maint_list:
                obj_key = get_key(maint_type, i)
                if obj_key != '-':
                    body["objects"].append({"object_type":"entity","_key":obj_key})
        else:
            obj_key = get_key(maint_type, maint_include)
            body["objects"].append({"object_type":"entity","_key":obj_key})

        res = requests.post(url, auth=(itsi_u, itsi_p), data=json.dumps(body), verify=False)
        logging.debug('POST response=%s', str(res.text))
        if res.status_code != 200:
            logging.warning('Unable to create maintenance window for %s', maint_title)

    elif maint_action=='remove':
        obj_key = get_key('maintenance', maint_title)
        url += obj_key + '/'
        res = requests.delete(url, auth=(itsi_u, itsi_p), verify=False)
        if res.status_code == 204:
            logging.info('Successfully removed maintenance window for %s', maint_title)
        else:
            logging.warning('Unable to remove maintenance window for %s', maint_title)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse arguments for ITSI Maintenance Windows')
    parser.add_argument("--action", choices=["create", "remove"], required=True, type=str, help="Action to take")
    parser.add_argument("--title", required=True, type=str, help="Title of maintenance window")
    parser.add_argument("--type", choices=["entity", "service"], type=str, help="Define entity or service")
    parser.add_argument("--include", type=str, help="Name of entity or service")
    parser.add_argument("--length", type=int, help="Length of maintenance window")

    args = parser.parse_args()

    maint_action = args.action
    maint_title = args.title
    #maint_type = args.include    #future functionality; to do: add _key mapping for services
    maint_type = 'entity'
    maint_include = args.include
    #maint_length = args.length    #future functionality; to do: parse length and add logic to add seconds to timestamp
    maint_length = '2147385600' # 2147385600 is indefinite

    try:
        logfile = set_logfile()
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', filename=logfile, level=logging.DEBUG)
    except:
        print('Error initializing logging')

    if maint_action == 'create':
        if maint_type == None:
            logging.critical('Must specify type (entity or service) when creating maintenance window')
            sys.exit(1)
        if maint_include == None:
            logging.critical('Must specify entities to include when creating maintenance window')
            sys.exit(1)

    try:
        maint_window(maint_action, maint_title, maint_type, maint_include, maint_length)
    except:
        print('Fatal exception')
        sys.exit(1)