from __future__ import print_function
from crhelper import CfnResource
import logging
import requests
import urllib3
import json
import copy

logger = logging.getLogger(__name__)
# Initialise the helper, all inputs are optional, this example shows the defaults
helper = CfnResource()

try:
    pass
except Exception as e:
    helper.init_failure(e)

def _create_auth_headers(username, password, account):
    headers = {'Content-Type':'application/json', 'Accept':'application/json'}
    headers.update(urllib3.util.make_headers(basic_auth = f"{username}:{password}"))
    return headers

def _verify_boomi_licensing(username, password, account):
    _headers = _create_auth_headers(username, password, account)
    API_URL = f"https://api.boomi.com/api/rest/v1/{account}/Account/{account}"
    resp = requests.get(API_URL, headers=_headers)
    resp.raise_for_status()
    json_resp = resp.json()

    account_status = json_resp['status']
    enterprise_licenses_purchased = json_resp['licensing']['enterprise']['purchased']
    enterprise_licenses_used = json_resp['licensing']['enterprise']['used']

    # Is the account active?
    if account_status == 'active':
        logger.info(f"Account is active")
    else:
        logger.error('Exception: Boomi account is inactive')
        raise Exception(f"Boomi account {account} is inactive.")

    # Do we have license entitelements at all?
    if enterprise_licenses_purchased > enterprise_licenses_used:
        logger.info(f"Licenses are available - Purchased: {enterprise_licenses_purchased} / Used: {enterprise_licenses_used}")
    else:
        logger.error('Exception: No enterprise license available')
        raise Exception(f"No enterprise licenses for account {account} are available. Purchased: {enterprise_licenses_purchased}, Used: {enterprise_licenses_used}")

def _verify_required_parameters(parameters):
    REQUIRED = ['BoomiUsername','BoomiPassword','BoomiAccountID', 'TokenType', 'TokenTimeout']
    REQ_TOKEN_TYPES = ['MOLECULE']
    for req_param in REQUIRED:
        if req_param not in parameters.keys():
            raise Exception(f"Not all required parameters have been passed. Need: {str(REQUIRED)}")
    if parameters['TokenType'].upper() not in REQ_TOKEN_TYPES:
        raise Exception(f"Parameter TokenType must be one of: {str(REQ_TOKEN_TYPES)}")
    _r = (
        parameters['BoomiUsername'],
        parameters['BoomiPassword'],
        parameters['BoomiAccountID'],
        parameters['TokenType'],
        parameters['TokenTimeout']
    )
    return _r

def _generate_install_token(username, password, account_id, token_type, timeout):
    _headers = _create_auth_headers(username, password, account_id)
    API_URL = f"https://api.boomi.com/api/rest/v1/{account_id}/InstallerToken/"
    payload = {
        "installType": token_type,
        "durationMinutes": int(timeout)
    }
    resp = requests.post(API_URL, json=payload)
    resp.raise_for_status()

    return resp['token']

@helper.create
@helper.update
def auth_and_licensing_logic(event, context):
      sanitized_event = copy.deepcopy(event)
      sanitized_event['ResourceProperties']['BoomiPassword'] = "<Redacted>"
      logger.info('Received event: %s' % json.dumps(sanitized_event))

      # Sanity Checking
      parameters = event['ResourceProperties']
      username, password, account_id, token_type, token_timeout = _verify_required_parameters(parameters)

      # Verify licensing
      _verify_boomi_licensing(username, password, account_id)

      # Generate install token
      token = _generate_install_token(username, password, account_id, token_type, token_timeout)

      helper.Data['InstallToken'] = token

def lambda_handler(event, context):
  # make sure we send a failure to CloudFormation if the function
  # is going to timeout
  helper(event, context)
