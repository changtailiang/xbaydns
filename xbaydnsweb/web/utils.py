#!/opt/local/bin/python2.5
# encoding: utf-8
"""
utils.py

Created by QingFeng on 2007-12-02.
Copyright (c) 2007 yanxu. All rights reserved.
"""
from django.core.management import setup_environ
from xbaydnsweb import settings
setup_environ(settings)

import logging.config
from xbaydnsweb.web.models import *
from xbaydns.dnsapi.namedconf import *
from xbaydns.conf import sysconf
from xbaydns.dnsapi import nsupdate
from xbaydns.tools import algorithms
from django.db.models import Q

log = logging.getLogger('xbaydnsweb.web.utils')
#logging.basicConfig(level=logging.DEBUG)

def genRecordList(record):
    rtstr = record.record_type.record_type
    if rtstr == 'A':
        return [[str(record.name),record.ttl,'IN','A',[str(record.record_info),]],]
    elif rtstr == 'CNAME':
        return [[str(record.name),record.ttl,'IN','CNAME',[str(record.record_info),]],]
    elif rtstr == 'NS':
        return [[str(record.name),record.ttl,'IN','NS',[str(record.record_info),]],]


def record_nsupdate(record):
    """调用NSUpdate更新record"""
    try:
        nsupobj = nsupdate.NSUpdate('127.0.0.1',"%s."%record.domain,view=record.viewname)
        #['foo', 3600, 'IN', 'A', ['192.168.1.1', '172.16.1.1']]#record style
        add_data=genRecordList(record)
        print "add_data",add_data
        nsupobj.addRecord(add_data)
        nsupobj.commitChanges()
        print "NSUpdate OK"
    except:
        print traceback.print_exc()
        print "NSUpdate Error!"
    
def record_delete(record):
    try:
        nsupobj = nsupdate.NSUpdate('127.0.0.1',"%s."%record.domain,view=record.viewname)
        del_data=genRecordList(record)
        print "del_data",del_data
        nsupobj.removeRecord(del_data)
        nsupobj.commitChanges()
        print "NSUpdate OK"
    except:
        print traceback.print_exc()

def getRecords(iparea):
    """将Result的结果按照域名合并汇总并返回"""
    records=[]
    for domain_name,idc_alias in list(eval(iparea.service_route)):
        
        records.extend(Record.objects.filter(name=domain_name[:domain_name.index('.')],domain__name=domain_name[domain_name.index('.')+1:],idc__alias=idc_alias,record_type__record_type='A'))
    return records

def updateDomain():
    """发出nsupdate请求,更新所有record和更新默认机房的记录"""
    for iparea in IPArea.objects.all():
        """把A纪录分布到对应的VIEW中"""
        records=getRecords(iparea)
        for record in records:
            print "record ",record
            record.viewname=iparea.view
            print record.name,record.domain,record.viewname
            record_nsupdate(record)
        """把非A记录加入每一个VIEW"""
        for record in Record.objects.filter(Q(record_type__record_type='NS')|Q(record_type__record_type='CNAME')):
            print "record ",record
            record.viewname=iparea.view
            print record.name,record.domain,record.viewname
            record_nsupdate(record)
    """更新默认机房的记录"""
    for record in Record.objects.filter(is_defaultidc=True):
        record.viewname="view_default"
        print record.name,record.domain,record.viewname
        record_nsupdate(record)

def genNamedConf(path):
    """生成所有named配置文件"""
    nc = NamedConf()
    ipareas = IPArea.objects.all()
    for i,iparea in enumerate(ipareas):
        aclname='acl_acl%s'%i
        print "aclname",aclname
        iparea.acl = aclname
        nc.addAcl(aclname,list(eval(iparea.ip)))
        #每个View对应一种ACL
        viewname='view_view%s'%i
        nc.addView(viewname,[aclname,])
        iparea.view = viewname
        iparea.save()
    #增加any的ACL和View
    nc.addAcl('acl_default',['any',])
    nc.addView('view_default',['any',])
    #追加所有的Domain
    #domain_matchs = map(lambda x:'%s'%x.domain,Record.objects.all())
    domain_matchs = map(lambda x:'%s'%x.name,Domain.objects.all())
    nc.addDomain(domain_matchs)
    nc.save(path)
    nc.reload()
        
#保存所有配置,生成所有bind需要的配置文件
def saveAllConf(path=os.path.join(sysconf.chroot_path,sysconf.namedconf)):
    genNamedConf(path)
    updateDomain()

def getDetectedIDC():
    CONF_FILE='%s/idcview/idcview.current'%sysconf.xbaydnsdb
    try:
        f =open(CONF_FILE)
        r = f.readline()
        agents=r.split(',')
        agents=map(lambda x:x.strip(),agents)
        f.close()
    except:
        agents = []
    return agents

def update_allow_transfer(slaveip, path=os.path.join(sysconf.chroot_path,sysconf.namedconf)):

    named_conf_path = os.path.join(path, "named.conf")
    named_conf_string = open(named_conf_path, 'r').read()
    
    p = re.compile('allow-transfer\s*{ (?P<allows> [^}]* ) }', re.VERBOSE)
    l = p.findall(named_conf_string)
    if len(l) == 0:
        return False
 
    allows=[]
    for ip in l[0].split(';'):
        cip = ip.strip()
        if len(cip) == 0 or cip == 'none':
            pass
        else:
            allows.append(cip)

    if ip in allows:
        return True

    allows.append(slaveip)
    allows.append('')
    allow_list = 'allow-transfer{ %s }' % '; '.join(allows)

    s = p.sub(allow_list, named_conf_string)
    open(named_conf_path, 'w').write(s)

    nc = NamedConf()
    nc.reload()
    return True