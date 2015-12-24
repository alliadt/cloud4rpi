#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect
import types
import unittest
from teamcity import is_running_under_teamcity
from teamcity.unittestpy import TeamcityTestRunner
import os  # should be imported before fake_filesystem_unittest
import c4r
from c4r import lib
from c4r import ds18b20 as ds_sensors
from c4r.ds18b20 import W1_DEVICES
from c4r import helpers
from c4r import errors
from c4r import error_messages
import fake_filesystem_unittest
from mock import patch
from mock import MagicMock


device_token = '000000000000000000000001'

sensor_10 = \
    '2d 00 4d 46 ff ff 08 10 fe : crc=fe YES' '\n' \
    '2d 00 4d 46 ff ff 08 10 fe : t=22250'

sensor_28 = \
    '2d 00 4d 46 ff ff 08 10 fe : crc=fe YES' '\n' \
    '2d 00 4d 46 ff ff 08 10 fe : t=28250'


class TestApi(unittest.TestCase):
    def setUp(self):
        c4r.set_device_token(device_token)

    @patch('c4r.lib.read_persistent')
    def testReadPersistent(self, mock):
        input = {'A': 1}
        c4r.read_persistent(input)
        mock.assert_called_once_with(0)

    @patch('c4r.lib.read_cpu')
    def testReadSystem(self, mock):
        input = {'A': 1}
        c4r.read_system(input)
        mock.assert_called_once_with({'A': 1})

    @patch('c4r.lib.send_receive')
    def testReadPersistent(self, mock):
        input = {'A': 1}
        c4r.send_receive(input)
        mock.assert_called_once_with(input)

    @patch('c4r.ds18b20.find_all')
    def testFindDSSensors(self, mock):
        c4r.find_ds_sensors()
        self.assertTrue(mock.called)

    def call_without_token(self, methods):
        lib.device_token = None
        for fn, args in methods.items():
            with self.assertRaises(errors.InvalidTokenError):
                if args is None:
                    fn()
                else:
                    fn(*args)

    def testVerifyToken(self):
        methods = {
            c4r.find_ds_sensors: None,
            c4r.register: ({},),
            c4r.read_persistent: ({},),
            c4r.read_system: ({},),
            c4r.process_variables: ({}, {}),
            c4r.send_receive: ({},)
        }
        self.call_without_token(methods)


class TestLibrary(unittest.TestCase):
    sensorReadingMock = None

    def setUp(self):
        pass

    def tearDown(self):
        self.restoreSensorReadingMock()

    def setUpSensorReading(self, expected_val):
        self.restoreSensorReadingMock()
        self.sensorReadingMock = MagicMock(return_value=expected_val)
        ds_sensors.read = self.sensorReadingMock

    def restoreSensorReadingMock(self):
        if not self.sensorReadingMock is None:
            self.sensorReadingMock.reset_mock()

    def methods_exists(self, methods):
        for m in methods:
            self.assertTrue(inspect.ismethod(m))

    def static_methods_exists(self, methods):
        for m in methods:
            is_instance = isinstance(m, types.FunctionType)
            self.assertTrue(is_instance)

    def testDefauls(self):
        self.assertIsNone(lib.device_token)

    # def testMethodsExists(self):
    # methods = [
    # ]
    # self.methods_exists(methods)

    def testStaticMethodsExists(self):
        self.static_methods_exists([
            lib.set_device_token,
            lib.run_handler,
            lib.find_ds_sensors,
            lib.create_ds18b20_sensor,
            lib.read_persistent,
            lib.send_receive
        ])

    def testSetDeviceToken(self):
        self.assertIsNone(lib.device_token)
        lib.set_device_token(device_token)
        self.assertEqual(lib.device_token, device_token)

    def testHandlerExists(self):
        var1 = {
            'title': 'valid',
            'bind': MockHandler.empty
        }
        var2 = {
            'title': 'invalid',
            'bind': {'address': 'abc'}
        }
        self.assertFalse(lib.bind_handler_exists(None))
        self.assertFalse(lib.bind_handler_exists(var2))
        self.assertTrue(lib.bind_handler_exists(var1))


    @patch('c4r.ds18b20.read')
    def testReadPersistent(self, mock):
        addr = '10-000802824e58'
        var = {
            'title': 'temp',
            'bind': {
                'type': 'ds18b20',
                'address': addr
            }
        }
        input = {"Var1": var}

        lib.read_persistent(input)
        mock.assert_called_with(addr)

    def testUpdateVariableValueOnRead(self):
        addr = '10-000802824e58'
        var = {
            'title': 'temp',
            'bind': {'type': 'ds18b20', 'address': addr}
        }
        input = {'Test': var}

        self.setUpSensorReading(22.4)

        lib.read_persistent(input)
        self.assertEqual(var['value'], 22.4)

    def testCollectReadings(self):
        variables = {
            'temp1': {'title': '123', 'value': 22.4, 'bind': {'type': 'ds18b20'}},
            'some': {'title': '456', 'bind': {'type': 'unknown'}},
            'temp2': {'title': '456', 'bind': {'type': 'ds18b20'}}
        }
        readings = lib.collect_readings(variables)
        expected = {'temp2': None, 'temp1': 22.4}
        self.assertEqual(readings, expected)


        # @patch('c4r.daemon.Daemon.run_handler')
        # def testProcessVariables(self, mock):
        # addr = '10-000802824e58'
        # temp = {
        # 'address': addr,
        #         'value': 22
        #     }
        #     self.daemon.register_variable_handler(addr, self._mockHandler)
        #
        #     self.daemon.process_variables([temp])
        #     mock.assert_called_with(addr)


class TestFileSystemAndRequests(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.patchRequests()
        self.fs.CreateFile('/dev/null')

    def setUpResponse(self, verb, response, status_code=200):
        r_mock = MagicMock(['json', 'status_code'])
        r_mock.json.return_value = response
        verb.return_value = r_mock
        self.setUpStatusCode(verb, status_code)

    @staticmethod
    def setUpStatusCode(verb, code):
        verb.return_value.status_code = code

    def patchRequests(self):
        self.get = self.startPatching('requests.get')
        self.put = self.startPatching('requests.put')
        self.post = self.startPatching('requests.post')

    def setUpDefaultResponses(self):
        self.setUpPOSTStatus(201)

    def setUpResponse(self, verb, response, status_code=200):
        r_mock = MagicMock(['json', 'status_code'])
        r_mock.json.return_value = response
        verb.return_value = r_mock
        self.setUpStatusCode(verb, status_code)

    @staticmethod
    def startPatching(target):
        return patch(target).start()

    def setUpGET(self, res_body):
        self.setUpResponse(self.get, res_body)

    def setUpPUT(self, res_body):
        self.setUpResponse(self.put, res_body)

    def setUpGETStatus(self, code):
        self.setUpStatusCode(self.get, code)

    def setUpPUTStatus(self, code):
        self.setUpStatusCode(self.put, code)

    def setUpPOSTStatus(self, code):
        self.setUpStatusCode(self.post, code)


class TestDataExchange(TestFileSystemAndRequests):
    def setUp(self):
        super(TestDataExchange, self).setUp()
        self.setUpDefaultResponses()
        lib.set_device_token(device_token)

    def tearDown(self):
        lib.set_device_token(None)

    def testSendReceive(self):
        variables = {
            'temp1': {'title': '123', 'value': 22.4, 'bind': {'type': 'ds18b20', 'address': '10-000802824e58'}}
        }
        self.setUpResponse(self.post, variables, 201)
        json = lib.send_receive(variables)
        self.assertEqual(json, variables)

    def testRaiseExceptionOnUnAuthStreamPostRequest(self):
        self.setUpPOSTStatus(401)
        with self.assertRaises(errors.AuthenticationError):
            lib.send_receive({})

    @patch('c4r.helpers.put_device_variables')
    def test_register_variables(self, mock):
        variables = {
            'var1': {
                'title': 'temp',
                'type': 'number',
                'bind': 'ds18b20'
            }
        }
        c4r.register(variables)
        mock.assert_called_with(device_token, [{'type': 'number', 'name': 'var1', 'title': 'temp'}])


class TestHelpers(unittest.TestCase):
    def testExtractVariableBindAttr(self):
        addr = '10-000802824e58'
        bind = {
            'address': addr,
            'value': 22
        }
        var = {
            'title': 'temp',
            'bind': bind
        }
        actual = helpers.extract_variable_bind_prop(var, 'address')
        self.assertEqual(actual, addr)


class TestDs18b20Sensors(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()

    def setUpSensor(self, address, content):
        self.fs.CreateFile(os.path.join(W1_DEVICES, address, 'w1_slave'), contents=content)

    def setUpSensors(self):
        self.setUpSensor('10-000802824e58', sensor_10)
        self.setUpSensor('28-000802824e58', sensor_28)

    def testCreate_ds18b20_sensor(self):
        sensor = lib.create_ds18b20_sensor('abc')
        self.assertEqual(sensor, {'address': 'abc', 'type': 'ds18b20'})

    def testFindDSSensors(self):
        self.setUpSensors()
        sensors = lib.find_ds_sensors()
        self.assertTrue(len(sensors) > 0)
        expected = [
            {'address': '10-000802824e58', 'type': 'ds18b20'},
            {'address': '28-000802824e58', 'type': 'ds18b20'}
        ]
        self.assertEqual(sensors, expected)


class MockHandler(object):
    @staticmethod
    def variable_inc_val(var):
        var['value'] += 1

    @staticmethod
    def empty(var):
        pass


class ErrorMessages(unittest.TestCase):
    def testGetErrorMessage(self):
        m = c4r.get_error_message(KeyboardInterrupt('test_key_err'))
        self.assertEqual(m, 'Interrupted')
        m = c4r.get_error_message(c4r.errors.ServerError('crash'))
        self.assertEqual(m, 'Unexpected error: crash')
        m = c4r.get_error_message(c4r.errors.AuthenticationError())
        self.assertEqual(m, 'Authentication failed. Check your device token.')
        m = c4r.get_error_message(c4r.errors.AuthenticationError())


def main():
    if is_running_under_teamcity():
        runner = TeamcityTestRunner()
    else:
        runner = unittest.TextTestRunner()
    unittest.main(testRunner=runner)


if __name__ == '__main__':
    main()
