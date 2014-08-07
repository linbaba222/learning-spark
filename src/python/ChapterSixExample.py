"""Contains the Chapter 6 Example illustrating accumulators, broadcast variables, numeric operations, and pipe."""
import sys
import re
import bisect

from pyspark import SparkContext

inputFile = sys.argv[1]
outputDir = sys.argv[2]

sc = SparkContext(appName="ChapterSixExample")
file = sc.textFile(inputFile)

# Create Accumulator[Int] initialized to 0
blankLines = sc.accumulator(0)
dataLines = sc.accumulator(0)

def extractCallSigns(line):
    global blankLines, dataLines # Access the counters
    if (line == ""):
        blankLines += 1
    return line.split(" ")

callSigns = file.flatMap(extractCallSigns)
callSigns.saveAsTextFile(outputDir + "/callsigns")
print "Blank lines %d" % blankLines.value

# Create Accumulators for validating call signs
validSignCount = sc.accumulator(0)
invalidSignCount = sc.accumulator(0)

def validateSign(sign):
    global validSignCount, invalidSignCount
    if re.match(r"\A\d?[a-zA-Z]{1,2}\d{1,4}[a-zA-Z]{1,3}\Z", sign):
        validSignCount += 1
        return True
    else:
        invalidSignCount += 1
        return False

validSigns = callSigns.filter(validateSign)
contactCount = validSigns.map(lambda sign: (sign, 1)).reduceByKey((lambda x, y: x + y))
# Force evaluation so the counters are populated
contactCount.count()
if invalidSignCount.value < 0.1 * validSignCount.value:
    contactCount.saveAsTextFile(outputDir + "/contactCount")
else:
    print "Too many errors %d in %d" % (invalidSignCount.value, validSignCount.value)

# Lookup the locations of the call signs
f = open("./files/callsign_tbl_sorted", "r")
callSignMap = map((lambda x: x.split(",")), f.readlines())
(callSignKeys, callSignLocations) = zip(*callSignMap)
callSignKeysBroadcast = sc.broadcast(callSignKeys)
callSignLocationsBroadcast = sc.broadcast(callSignLocations)

def lookupCountry(sign_count):
    sign = sign_count[0]
    count = sign_count[1]
    pos = bisect.bisect_left(callSignKeysBroadcast.value, sign)
    return (callSignLocationsBroadcast.value[pos], count)

countryContactCount = contactCount.map(lookupCountry).reduceByKey((lambda x, y: x+ y))
countryContactCount.saveAsTextFile(outputDir + "/countries")
