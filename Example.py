from wsjf_generator import *

filename = 'Example Report'
snr = '12345'
rev = "A"
productName = "Example product"
partNumber = "12-34-567"

# Initialize WSJF generator
# Process code and process name need to exist in WATS
watsDriver = wsjf_generator(f"{filename}.json", TestType.UUT, snr, rev, productName, partNumber, 1,
                            processName="Example test", location="Test location")
# Set optional comment
watsDriver.setComment(
    'This is an example test report')

# Add main test step to report
watsDriver.addMain()

# Create test groups
# Command returns ID of created group which is used to assign a test step to a group
preTest = watsDriver.addTestGroup(Group.MAIN, "Pretest")
fTest = watsDriver.addTestGroup(Group.MAIN, "Functional test")
dTest = watsDriver.addTestGroup(Group.MAIN, "Destructive test")

# Example GELE test
# First argument is the ID of the test group that the test should be added to
# Limits can be specified individually or alternatively a tolerance can be provided
watsDriver.addNumericTest(preTest, "On/Off test", Operation.GREATER_THAN_EQUAL_LESS_THAN_EQUAL, 'V',
                                              5, 4.9, 5.2, 4.8)

# Add additional UUT info to report.
# This can be text, numeric or both
watsDriver.addMiscInfo("Info", "This text is displayed in WATS under Misc. UUT info")
# Add information about sub unit inside UUT
# Name of part (part type), serial number, part number are required parameters. Revision is optional
watsDriver.addSubUnitInfo("Sub part", "0199", "99-99", "B")
# Decides if test report and test groups are pass/fail and saves report to disk
watsDriver.saveReport()