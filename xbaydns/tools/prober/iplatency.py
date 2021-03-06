#!/usr/bin/env python
# encoding: utf-8
"""
iplatency.py

Created by Razor <bg1tpt AT gmail.com> on 2008-03-17.
Copyright (c) 2008 xBayDNS Team. All rights reserved.

"""

import os, re, struct, sys, time
import threading
from iplatency_conf import *

pingre_obj = re.compile(PING_RE)
digre_obj = re.compile(DIG_RE)
tracertre_obj = re.compile(TRACERT_RE)

pool_sema = threading.BoundedSemaphore(MAX_TESTING)
file_mutex = threading.Lock()

def getlatency_ping(ip):
    latencies = {}
    ping = os.popen(PING_CMD%ip, "r")
    while True:
        output = ping.readline()
        if output == '':
            break
        if pingre_obj.match(output) != None:
            latencies['min'], latencies['avg'], latencies['max'] = pingre_obj.match(output).groups()
            break
    ping.close()
    return latencies

def getlatency_queryns(ip):
    latencies = dict(query={}, run={})
    querytime_lst = []
    runtimes_lst = []
    count = 0
    while count < MAXQUERIES:
        time_start = time.time()
        dig = os.popen(DIG_CMD%ip, "r")
        output = dig.read()
        time_end = time.time()
        dig.close()
        querytime = digre_obj.findall(output)
        if len(querytime) != 0:
            querytime_lst.append(int(querytime[0]))
            runtimes_lst.append(round((time_end - time_start) * 1000, 3))
        time.sleep(QUERY_INTERVAL)
        count += 1
    if len(querytime_lst) > 0:
        latencies['query']['avg'] = float(sum(querytime_lst))/len(querytime_lst)
        latencies['query']['min'] = min(querytime_lst)
        latencies['query']['max'] = max(querytime_lst)
        latencies['run']['avg'] = sum(runtimes_lst)/len(runtimes_lst)
        latencies['run']['min'] = min(runtimes_lst)
        latencies['run']['max'] = max(runtimes_lst)
    return latencies

def getlatency_gateway(ip):
    tracert = os.popen(TRACERT_CMD%ip, "r")
    output = tracert.read()
    tracert.close()
    lines = output.rstrip('\n').split('\n')
    host_ip = tracertre_obj.findall(lines[-1])
    if host_ip != [] and host_ip[0] == ip:
        gateway_ip = tracertre_obj.findall(lines[-2])
        if gateway_ip != [] and gateway_ip[0] != '':
            return getlatency_ping(gateway_ip[0])
    return []

def getlatency(ip):
    latencies = getlatency_ping(ip)
    if len(latencies) == 0:
        latencies = getlatency_queryns(ip)
        if len(latencies['query']) == 0:
            latencies = getlatency_gateway(ip)
            if len(latencies) == 0:
                pingtype = "OUT_OF_REACH"
                latency = -1
            else:
                pingtype = "PING_GATEWAY"
                latency = latencies['avg']
        else:
            pingtype = "NS_QUERY"
            latency = latencies['query']['avg']
    else:
        pingtype = "PING_HOST"
        latency = latencies['avg']
    return (pingtype, latency)

def threadmain(ip, fileobj):
    pool_sema.acquire(True)
    pingtype, latency = getlatency(ip)
    pool_sema.release()
    file_mutex.acquire()
    fileobj.write("%s,%s,%s,%s\n"%(ip, pingtype, latency, time.strftime("%Y-%m-%d %H:%M:%S")))
    fileobj.flush()
    file_mutex.release()

def main():
    threads = []
    input = "/dev/stdin"
    output = "/dev/stdout"
    if len(sys.argv) == 1:
        pass
    elif len(sys.argv) == 2:
        input = sys.argv[1]
    elif len(sys.argv) == 3:
        input = sys.argv[1]
        output = sys.argv[2]
    else:
        print '''Usage:  %s
        %s iplistfile
        %s iplistfile outputfile'''%(__file__, __file__, __file__)
        return 1
    try:
        iplst = open(input, "r")
        latency_file = open(output, "a")
    except IOError, e:
        print e.strerror
        return 1
    while True:
        ip = iplst.readline().strip('\n')
        if ip == '':
            break
        threads.append(threading.Thread(target=threadmain, args=(ip, latency_file)))
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    latency_file.close()
    return 0

if __name__ == '__main__':
    try:
        pidfile = open("/tmp/iplatency.pid", "r")
        pid = int(pidfile.readline())
        pidfile.close()
        os.kill(pid, 0)
        sys.exit(1)
    except ValueError:
        sys.exit(1)
    except IOError:
        pass
    except OSError:
        pass
    pid = os.getpid()
    pidfile = open("/tmp/iplatency.pid", "w")
    pidfile.write(str(pid))
    pidfile.close()
    ret = main()
    if os.path.isfile("/tmp/iplatency.pid"):
        os.remove("/tmp/iplatency.pid")
    sys.exit(ret)
