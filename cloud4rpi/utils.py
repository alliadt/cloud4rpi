# -*- coding: utf-8 -*-

import sys
import re
import inspect
import logging
import numbers
from datetime import datetime, tzinfo, timedelta
from cloud4rpi import config
from cloud4rpi.errors import InvalidTokenError
from cloud4rpi.errors import UnexpectedVariableValueTypeError
from cloud4rpi.errors import TYPE_WARN_MSG

if sys.version_info[0] > 2:
    from cloud4rpi.utils_v3 import is_string
else:
    from cloud4rpi.utils_v2 import is_string


log = logging.getLogger(config.loggerName)


class UtcTzInfo(tzinfo):
    # pylint: disable=W0223
    def tzname(self, dt):
        return "UTC"

    def utcoffset(self, dt):
        return timedelta(0)


def guard_against_invalid_token(token):
    token_re = re.compile('[1-9a-km-zA-HJ-NP-Z]{23,}')
    if not token_re.match(token):
        raise InvalidTokenError(token)


def to_bool(value):
    if isinstance(value, bool):
        return value
    elif isinstance(value, numbers.Number):
        return bool(value)
    else:
        raise Exception()


def to_numeric(value):
    if isinstance(value, bool):
        return float(value)
    elif isinstance(value, numbers.Number):
        return value
    elif is_string(value):
        log.warning(TYPE_WARN_MSG, value)
        return float(value)
    else:
        raise Exception()


def to_string(value):
    if isinstance(value, str):
        return value
    elif isinstance(value, bool):
        return str(value).lower()
    else:
        return str(value)


def validate_variable_value(name, var_type, value):
    if value is None:
        return value

    convert = {
        'bool': to_bool,
        'numeric': to_numeric,
        'string': to_string,
    }
    c = convert.get(var_type, None)
    if c is None:
        return None
    try:
        return c(value)
    except Exception:
        raise UnexpectedVariableValueTypeError('"{0}"={1}'.format(name, value))


def variables_to_config(variables):
    return [{'name': name, 'type': value['type']}
            for name, value in variables.items()]


def utcnow():
    return datetime.utcnow().replace(tzinfo=UtcTzInfo()).isoformat()


def args_count(binding):
    # pylint: disable=E1101, W1505
    if inspect.getargspec is not None:
        args = inspect.getargspec(binding).args
    else:
        args = inspect.getfullargspec(binding).args

    return args.__len__()


def has_args(binding):
    if inspect.ismethod(binding):
        return args_count(binding) > 1
    else:
        return args_count(binding) > 0


def resolve_callable(binding, current=None):
    if has_args(binding):
        return binding(current)
    else:
        return binding()
