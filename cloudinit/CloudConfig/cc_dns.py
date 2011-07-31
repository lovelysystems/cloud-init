# vi: ts=4 expandtab
#
#    Copyright (C) 2009-2010 Canonical Ltd.
#
#    Author: Scott Moser <scott.moser@canonical.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 3, as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import pwd
import socket
import subprocess
import cloudinit.DistAction

def handle(name,cfg,cloud,log,args):
    # If there isn't a dns key in the configuration don't do anything
    if not cfg.has_key('dns'): return

    dns_cfg = cfg['dns']
    hostname = dns_cfg['hostname']
    host, domain = hostname.split('.', 1)
    subprocess.Popen(['hostname', hostname]).communicate()
    subprocess.check_call(['sed', '-i',
                           '-e', 's/^HOSTNAME=.*/HOSTNAME=%s/' %hostname,
                           '/etc/sysconfig/network'])
    log.debug("set HOSTNAME in /etc/sysconfig/network to %s on first boot", hostname)
    local_ipv4 = cloud.datasource.get_local_ipv4()
    hosts_fh = open('/etc/hosts', 'a')
    hosts_fh.write("\n%s    %s    %s" %(local_ipv4, hostname, host))
    log.debug("set entry for %s to %s in /etc/hosts", %(hostname, local_ipv4))

    if dns_cfg.has_key('route53'):
        env = {'AWS_ACCESS_KEY_ID': dns_cfg['route53']['aws_access_key_id'],
               'AWS_SECRET_ACCESS_KEY': dns_cfg['route53']['aws_secret_access_key']}
        ttl = '%s' %dns_cfg['route53']['ttl']
        hostname = cloud.datasource.get_public_hostname()
        subprocess.Popen(['/usr/bin/cli53', 'rrcreate', 
                          domain, host, 'CNAME', hostname, '--ttl', ttl, '--replace'], env=env).communicate()
        log.debug("updated Route53 hostname %s", hostname)

