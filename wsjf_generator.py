# -*- coding: utf-8 -*-
"""
Author: Jesper Johnsen - jsj@sky-watch.com
Created on Thu Mar 18 08:35:49 2021
Class to generate WATS JSON Format reports and publish the report
"""
import json
import os
import socket
import uuid
from datetime import datetime
from enum import Enum

import requests
from colorama import Fore, init
from pytz import timezone

init(autoreset=True)

class Group(str, Enum):
    STARTUP = "S"
    MAIN = "M"
    CLEANUP = "C"

class Operation(str, Enum):
    GREATER_THAN_EQUAL_LESS_THAN_EQUAL = "GELE"
    EQUALS = "EQ"
    NOT_EQUAL = "NQ"

class TestType(str, Enum):
    UUT = "T"
    UUR = "R"

class TestResult(str, Enum):
    PASSED = "P"
    FAILED = "F"
    DONE = "D"
    SKIPPED = "S"
    ERROR = "E"
    TERMINATED = "T"

class StepType(str, Enum):
    SEQUENCE_CALL = "SequenceCall"
    NUMERIC_LIMIT_TEST_SINGLE = "ET_NLT"
    STRING_VALUE_TEST_SINGLE = "ET_SVT"
    PASS_FAIL_TEST_SINGLE = "ET_PFT"

""" Returns [low limit, high limit, nominal value, tolerance] """
def MakePassRange(nominalValue, tolerance):
    _tolerance = float(nominalValue) * float(tolerance) / 100.0
    return (float(nominalValue) - _tolerance), (float(nominalValue) + _tolerance), float(nominalValue), float(
        tolerance)


def evaluateNumericLimitTest(operation: Operation, measuredValue, lowLimit, highLimit) -> TestResult:
    if operation == Operation.GREATER_THAN_EQUAL_LESS_THAN_EQUAL:
        return TestResult.PASSED if lowLimit <= measuredValue <= highLimit else TestResult.FAILED
    if operation == Operation.NOT_EQUAL:
        return TestResult.PASSED if measuredValue != lowLimit else TestResult.FAILED
    if operation == Operation.EQUALS:
        return TestResult.PASSED if measuredValue == lowLimit else TestResult.FAILED
    return TestResult.SKIPPED

class wsjf_generator:
    def __init__(self, filename, testType: TestType, serialNumber: str, revision: str, productName: str, partNumber: str, processCode: int, user: str = "", purpose: str = None, location:str = None, machineName: str = '', processName: str = '', executionTime: int = 0):
        self.fileHandler = open(filename, 'w')
        self.uuid = str(uuid.uuid4())
        self.result = TestResult.FAILED
        self.testType = testType
        self.serialNumber = serialNumber
        self.revision = revision
        self.productName = productName
        self.partNumber = partNumber
        self.processCode = processCode
        self.purpose = purpose
        self.location = location
        self.machineName = socket.gethostname() if machineName == '' else machineName
        self.processName = processName
        now = datetime.now(timezone('UTC'))
        self.start = now.astimezone(timezone("Europe/Amsterdam")).isoformat(timespec='seconds')
        self.startUTC = now.isoformat(timespec='seconds')[:-6] + ".Z"
        self.stepCounter = 2
        self.rootSteps = []
        self.wsjfReport = {}
        self.counterID = 0
        self.executionTime = executionTime
        self.user = os.getlogin() if user == "" else user
        self.TestSequencerName = "WSJF generator for Python"
        self.TestSequencerVersion = "0.1"
        self.__TestGroups = {}
        self.__writeHeader()
        self.resultsTable = {}

    def __writeHeader(self):
        dictHeader =   {
            "type": self.testType,
            "id": self.uuid,
            "pn": self.partNumber,
            "sn": self.serialNumber,
            "rev": self.revision,
            "productName": self.productName,
            "processCode": self.processCode,
            "processName": self.processName,
            "result": "F",
            "machineName": self.machineName,
            "location": self.location,
            "purpose": self.purpose,
            "start": self.start,
            "startUTC": self.startUTC,
            "root": "",
            "uut":{
                "user": self.user,
                "comment": "No Comments added",
                "execTime": self.executionTime
                },
            "miscInfos": [],
            "subUnits": []
            }
        self.wsjfReport = dictHeader
            
    def addMain(self, totalExecutionTime: int = 0):
        dictMain = {
            "id": 0,
            "group": "M",
            "stepType": "SequenceCall",
            "name": "MainSequence Callback",
            "status": "F",
            "totTime": totalExecutionTime,
            "steps": [
              ],
              "seqCall": {
                  "path": self.TestSequencerName,
                  "name": "Test sequence",
                  "version": self.TestSequencerVersion
                  }
        }
        self.counterID += 1
        self.Dict_setValue(self.wsjfReport, ["root"], dictMain)
        return ["root", "steps"]

    def addTestGroup(self, group: Group, name: str, totalTime: float = 0.0):
            _id = self.counterID
            _this = {
            "id": _id,
            "group": group,
            "stepType": "SequenceCall",
            "name": name,
            "status": "S",
            "totTime": totalTime,
            "causedUUTFailure": False,
            "steps": [
            ],
            "seqCall": {
                "path": self.TestSequencerName,
                "name": "Test sequence",
                "version": self.TestSequencerVersion
            }
            }
            self.__TestGroups[_id] = _this
            self.counterID += 1
            return _id

    def addNumericTest(self, testGroupID, testName: str, operation: Operation, unit: str, referenceValue: float, measuredValue: float, highLimit: float = 0.0, lowLimit: float = None, tolerance: float = None, steptime: float = 0.0, result: TestResult = None):
        # [highLimit, lowLimit, compOp, status, causedUUTFailure] = self.getSimpleLimits(path, value, highLimit, lowLimit)
        lowLimit = referenceValue if lowLimit is None else lowLimit
        if tolerance is not None:
            lowLimit, highLimit,_,_ = MakePassRange(referenceValue, tolerance)
        if result is None:
            status = evaluateNumericLimitTest(operation, measuredValue, lowLimit, highLimit)
        else:
            status = result
        dictSingleTest = {
                "id": self.counterID,
                "group": "M",
                "stepType": "ET_NLT",
                "name": testName,
                "status": status,
                "totTime": steptime,
                # "causedUUTFailure": causedUUTFailure,
                "numericMeas": [
                  {
                    "compOp": operation,
                    "name": None,
                    "status": status,
                    "unit": unit,
                    "value": measuredValue,
                    "highLimit": highLimit,
                    "lowLimit": lowLimit
                  }
                ]
              }
        
        if status == TestResult.PASSED:
            print(f"Testing {testName} -> " + Fore.GREEN + "Passed")
        else:
            print(f"Testing {testName} -> " + Fore.RED + "Failed")
        self.counterID += 1
        self.__TestGroups[testGroupID]['steps'].append(dictSingleTest)
        self.resultsTable[testName] = status

    """ Evaluates if measuredValue is True which means the test is a Pass. Passing TestResult as an argument skips the evaluation. """
    def addBooleanTest(self, testGroupID, testName: str, measuredValue: bool, steptime: float = 0.0, result: TestResult = None):
        if result is None:
            status = TestResult.PASSED if measuredValue else TestResult.FAILED
        else:
            status = result
        dictSingleTest = {
                "id": self.counterID,
                "group": "M",
                "stepType": "ET_PFT",
                "name": testName,
                "status": status,
                "totTime": steptime,
                "booleanMeas": [
                    {
                        "name": None,
                        "status": status
                    }
                ]
            }
        if status == TestResult.PASSED:
            print(f"Testing {testName} -> " + Fore.GREEN + "Passed")
        else:
            print(f"Testing {testName} -> " + Fore.RED + "Failed")
        self.counterID += 1
        self.__TestGroups[testGroupID]['steps'].append(dictSingleTest)
        self.resultsTable[testName] = status

    def addMiscInfo(self, description: str, text: str, numeric: float = 0.0):
        _dict = {
            "description": description,
            "numeric": numeric,
            "text": text
        }
        self.wsjfReport['miscInfos'].append(_dict)

    def addSubUnitInfo(self, partType: str, serialNumber: str, partNumber: str, revision: str):
        _dict = {
            "partType": partType,
            "sn": serialNumber,
            "pn": partNumber,
            "rev": revision
        }
        self.wsjfReport['subUnits'].append(_dict)

    def saveReport(self):
        for i in self.__TestGroups:
            self.updateStatusGroup(i)
            self.wsjfReport['root']['steps'].append(self.__TestGroups[i])
        self.updateStatusReport()
        self.fileHandler.write(json.dumps(self.wsjfReport, indent=2))
        print(Fore.GREEN + 'Test summary:')
        c=0
        for key in self.resultsTable.keys():
            if self.resultsTable[key] == TestResult.FAILED:
                print(Fore.RED + key)
                c+=1
        print( (Fore.RED if c>0 else Fore.GREEN) + f'{c} test(s) failed')
        return c

    def uploadReport(self, serverURL, token):
        r = requests.post(f"https://{serverURL}/api/report/wsjf", json=self.wsjfReport,
                          headers={
                              "Content-Type": "application/json",
                              "Authorization": token
                          })
        print(f'Server response: {r.status_code}')

    def ReportContainsFailedTests(self) -> bool:
        for key in self.resultsTable.keys():
            if self.resultsTable[key] == TestResult.FAILED:
                return True
        return False
    # WSJF support functions
    def updateStatusGroup(self, testGroupID):
        results = []
        for i in self.__TestGroups[testGroupID]['steps']:
            results.append(i['status'])
        if all((x == TestResult.PASSED or x==TestResult.SKIPPED) for x in results):
            self.__TestGroups[testGroupID]['status'] = TestResult.PASSED
        if all(x == TestResult.SKIPPED for x in results):
            self.__TestGroups[testGroupID]['status'] = TestResult.SKIPPED
        if any(x == TestResult.FAILED for x in results):
            self.__TestGroups[testGroupID]['status'] = TestResult.FAILED

    def updateStatusReport(self):
        results = []
        for i in self.__TestGroups:
            results.append(self.__TestGroups[i]['status'])
        if all(x == TestResult.PASSED for x in results):
            self.wsjfReport['result'] = TestResult.PASSED
            self.wsjfReport['root']['status'] = TestResult.PASSED
        if any(x == TestResult.FAILED for x in results):
            self.wsjfReport['result'] = TestResult.FAILED
            self.wsjfReport['root']['status'] = TestResult.FAILED

    def updateStatus(self, Dict, DictPath, status: TestResult):
        Dict["result"] = status
        for key in DictPath[:]:
            try:
                Dict["status"] = status
            except:
                None
                
            if type(Dict)==list:
                #Dict is a list of dicts
                #find the right dict in the list
                for dict_ in filter(lambda x: x[key[0]] == key[1], Dict):
                    self.updateStatus(dict_, DictPath[DictPath.index(key)+1:], status)
                    return
            else:
                Dict = Dict.setdefault(key, {})
    def setComment(self, text):
        self.Dict_setValue(self.wsjfReport, ["uut", "comment"], text)
                

    # Dict Support functions.
    # WSJF report is generated from a Dict object
    # and a Dict Object can be created from a JSON file
    def Dict_lookup(self, Dict, DictPath):
        tempDict = Dict
        for key in DictPath:
            if type(Dict)==list:
                for dict_ in filter(lambda x: x[key[0]] == key[1], tempDict):
                    return self.Dict_lookup(dict_, DictPath[DictPath.index(key)+1:])
            else:        
                tempDict = tempDict[key]
        return tempDict
    def Dict_setValue(self, Dict, DictPath, value):
        for key in DictPath[:-1]:
            if type(Dict)==list:
                #Dict is a list of dicts
                #find the right dict in the list
                for dict_ in filter(lambda x: x[key[0]] == key[1], Dict):
                    self.Dict_setValue(dict_, DictPath[DictPath.index(key)+1:], value)
                    return
            else:
                Dict = Dict.setdefault(key, {})    
        Dict[DictPath[-1]] = value
    def Dict_addList(self, Dict, DictPath, value):
        for key in DictPath:
            if type(Dict)==list:
                #Dict is a list of dicts
                #find the right dict in the list
                for dict_ in filter(lambda x: x[key[0]] == key[1], Dict):
                    self.Dict_addList(dict_, DictPath[DictPath.index(key)+1:], value)
                    return
            else:
                Dict = Dict.setdefault(key, {})    
        Dict.append( value )
        
    def Dict_addKey(self, Dict, DictPath, newkey, value=""):
        for key in DictPath:
            if type(Dict)==list:
                #Dict is a list of dicts
                #find the right dict in the list
                for dict_ in filter(lambda x: x[key[0]] == key[1], Dict):
                    self.Dict_addKey(dict_, DictPath[DictPath.index(key)+1:], newkey, value)
                    return
            else:
                Dict = Dict.setdefault(key, {})
        Dict[newkey] = value
    def Dict_delKey(self, Dict, DictPath):
        for key in DictPath[:-1]:
            if type(Dict)==list:
                #Dict is a list of dicts
                #find the right dict in the list
                for dict_ in filter(lambda x: x[key[0]] == key[1], Dict):
                    self.Dict_delKey(dict_, DictPath[DictPath.index(key)+1:])
                    return
            else:
                Dict = Dict.setdefault(key, {})
        del Dict[DictPath[-1]]


