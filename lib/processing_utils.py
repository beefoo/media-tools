import multiprocessing
import sys

def getThreadCount(target=-1):
    cpuCount = multiprocessing.cpu_count()
    threads = min(target, cpuCount) if target > 0 else cpuCount
    return threads

def printProgress(step, total):
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*step/total*100,2))
    sys.stdout.flush()
