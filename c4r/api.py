#!/usr/bin/env python
# -*- coding: utf-8 -*-

from c4r import ds18b20
from c4r import cpu
from c4r import lib
from c4r import error_messages
from c4r.helpers import verify_token
from axel import Event


def api_wrapper(method, *args):
    try:
        return method(*args)
    except Exception as e:
        print 'API error: {0}'.format(get_error_message(e))
        return None


def get_error_message(e):
    return error_messages.get_error_message(e)


def set_device_token(token):
    api_wrapper(lib.set_device_token, token)


def register(variables):
    verify_token(lib.device_token)
    api_wrapper(lib.register, variables)


def find_ds_sensors():
    return api_wrapper(ds18b20.find_all)


def find_cpu():
    return api_wrapper(cpu.Cpu)


def read_persistent(variables):
    api_wrapper(lib.read_persistent, variables)


def read_system(variables):
    api_wrapper(lib.read_system, variables)


def process_variables(variables, server_msg):
    api_wrapper(lib.process_variables, variables, server_msg)


def send_receive(variables):
    verify_token(lib.device_token)
    return api_wrapper(lib.send_receive, variables)


on_broker_message = Event()
