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
    # If there isn't a puppet key in the configuration don't do anything
    if not cfg.has_key('puppet'): return
    
    puppet_cfg = cfg['puppet']
    # Start by installing the puppet package ...
    e=os.environ.copy()
    dist = cloudinit.DistAction.DistAction("/etc/cloud/dist-defs.cfg")
    dist.repo_install(['puppet'])
    servername = puppet_cfg['conf']['agent']['server']
    hostname = socket.getfqdn()
    ssldir = '/var/lib/puppet/ssl'
    # Puppet ssl sub-directory isn't created yet
    # Create it with the proper permissions and ownership
    puid = pwd.getpwnam('puppet').pw_uid
    if not os.path.exists(ssldir):
        os.makedirs(ssldir)
        os.chmod(ssldir, 0771)
        os.chown(ssldir, puid, 0)
        os.makedirs('%s/certs' %ssldir)
        os.chown('%s/certs' %ssldir, puid, 0)
        os.makedirs('%s/private_keys' %ssldir)
        os.chmod('%s/private_keys' %ssldir, 0750)
        os.chown('%s/private_keys' %ssldir, puid, 0)
        os.makedirs('%s/public_keys' %ssldir)
        os.chown('%s/public_keys' %ssldir, puid, 0)
    # Add all sections from the conf object to puppet.conf
    puppet_conf_fh = open('/etc/puppet/puppet.conf', 'a')
    for cfg_name, cfg in puppet_cfg.iteritems():
        fn = None
        if cfg_name == 'conf':
            for conf_name, conf in puppet_cfg['conf'].iteritems():
                puppet_conf_fh.write("\n[%s]\n" % (conf_name))
                for o, v in conf.iteritems():
                    if o == 'certname':
                        # Expand %f as the fqdn
                        v = v.replace("%f", hostname)
                        # Expand %i as the instance id
                        v = v.replace("%i", cloud.datasource.get_instance_id())
                        # certname needs to be downcase
                        v = v.lower()
                    puppet_conf_fh.write("    %s = %s\n" % (o, v))
                    if o == 'listen':
                        puppet_namespaceauth_fh = open('/etc/puppet/namespaceauth.conf', 'a')
                        puppet_namespaceauth_fh.write("[puppetrunner]\n")
                        puppet_namespaceauth_fh.write("    allow %s\n" %servername)
                        puppet_namespaceauth_fh.close()
        # ca_cert configuration is a special case
        # ca_cert configuration is a special case
        # Dump the puppetmaster ca certificate in the correct place
        elif cfg_name == 'ca_cert':
            fn = '%s/certs/ca.pem' %ssldir
        elif cfg_name == 'cert':
            fn = '%s/certs/%s.pem' %(ssldir, hostname)
        elif cfg_name == 'private_key':
            fn = '%s/private_keys/%s.pem' %(ssldir, hostname)
        elif cfg_name == 'public_key':
            fn = '%s/public_keys/%s.pem' %(ssldir, hostname)

        if fn is not None:
            fh = open(fn, 'w')
            fh.write(cfg)
            fh.close()
            os.chown(fn, puid, 0)
            
    puppet_conf_fh.close()
    # Set puppet default file to automatically start
    subprocess.check_call(['chkconfig', 'puppet', 'on'])
    # Start puppet
    subprocess.check_call(['service', 'puppet', 'start'])

