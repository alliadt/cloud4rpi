import json
import os
import re
import requests
from c4r import errors
from c4r.logger import get_logger
import settings_vendor as config
from sensors import cpu as cpu_sensor

REQUEST_TIMEOUT_SECONDS = 3 * 60 + 0.05

log = get_logger()


def find_actuators(settings):
    return [x['address'] for x in settings.Actuators]


def find_variables(settings):
    return [x['name'] for x in settings.Variables]


def request_headers(token):
    return {'api_key': token}


def device_request_url(token):
    return '{0}/devices/{1}/'.format(config.baseApiUrl, token)


def device_variables_request_url(token):
    return '{0}/devices/{1}/variables'.format(config.baseApiUrl, token)


def stream_request_url(token):
    return '{0}/devices/{1}/streams/'.format(config.baseApiUrl, token)


def system_parameters_request_url(token):
    return '{0}/devices/{1}/params/'.format(config.baseApiUrl, token)


def get_system_parameters():
    cpu_temperature = cpu_sensor.read()
    return {
        'cpuTemperature': cpu_temperature
    }


def load_device_config():
    return load_file(config.config_file)


def load_device_state():
    return load_file(config.state_file)


def load_file(file_path):
    with open(file_path, 'r') as config_file:
        return json.load(config_file)


def write_device_config(device_config):
    write_file(config.config_file, device_config)


def write_device_state(device_state):
    write_file(config.state_file, device_state)


def write_file(file_path, file_content):
    try:
        with open(file_path, 'w') as config_file:
            json.dump(file_content, config_file)
    except Exception as e:
        log.exception('Error during write file {0}. Skipping... Error: {1}'.format(file_path, e.message))


def get_device(token):
    if os.path.isfile(config.config_file):
        try:
            device = load_device_config()
            return device
        except (TypeError, Exception) as e:
            log.exception('Error during load saved device config. Skipping... Error: {0}'.format(e.message))

    res = requests.get(device_request_url(token),
                       headers=request_headers(token),
                       timeout=REQUEST_TIMEOUT_SECONDS)
    check_response(res)
    return res.json()


def put_device_variables(token, variables_config):
    log.info('Sending device configuration...')
    res = requests.put(device_variables_request_url(token),
                       headers=request_headers(token),
                       json=variables_config,
                       timeout=REQUEST_TIMEOUT_SECONDS)
    check_response(res)
    if res.status_code != 200:
        log.error('Can\'t register variables. Status: {0}'.format(res.status_code))

    http_result = res.json()
    write_device_config(http_result)

    return http_result


def post_stream(token, stream):
    log.info('sending {0}'.format(stream))

    res = requests.post(stream_request_url(token),
                        headers=request_headers(token),
                        json=stream,
                        timeout=REQUEST_TIMEOUT_SECONDS)
    check_response(res)
    return res.json()


def post_system_parameters(token):
    params = get_system_parameters()
    log.info('sending {0}'.format(params))

    res = requests.post(system_parameters_request_url(token),
                        headers=request_headers(token),
                        json=params,
                        timeout=REQUEST_TIMEOUT_SECONDS)
    check_response(res)
    return res.json()


def check_response(res):
    log.info(res.status_code)
    if res.status_code == 401:
        raise errors.AuthenticationError
    if res.status_code >= 500:
        raise errors.ServerError


def is_token_valid(token):
    r = re.compile('[0-9a-f]{24}')
    return token and len(token) == 24 and r.match(token)


def verify_token(token):
    if not is_token_valid(token):
        raise errors.InvalidTokenError


def extract_variable_bind_prop(props, prop_name):
    bind = get_variable_bind(props)
    if bind is None:
        return False
    if hasattr(bind, '__call__'):
        return bind()

    return bind[prop_name]


def extract_variable_prop(props, prop_name):
    if props is None:
        return None
    if prop_name in props.keys():
        return props[prop_name]
    return None


def get_variable_address(variable):
    return extract_variable_bind_prop(variable, 'address')


def get_variable_type(props):
    return extract_variable_bind_prop(props, 'type')


def get_variable_value(props):
    return extract_variable_prop(props, 'value')


def get_variable_bind(props):
    return extract_variable_prop(props, 'bind')


def bind_is_handler(bind):
    if bind is None:
        return False
    return hasattr(bind, '__call__')
