# vi: ts=4 expandtab
#
#    Copyright (C) 2009-2010 Canonical Ltd.
#
#    Author: Scott Moser <scott.moser@canonical.com>
#
#    Modifications Copyright (C) 2010 Amazon.com, Inc. or its affiliates.
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
#

#    Modifications:  New file based on apt/sources.list actions in
#                    cc_apt_update_upgrade.py.  These changes implement
#                    equivalent actions in yum for the sake of portability
#                    (apt and other package management products should
#                    have a similar file)

import cloudinit
import cloudinit.util as util
import os
import sys
import subprocess
import platform
import socket
import glob

YUMBIN = "/usr/bin/yum"
YUMREPOS = "/etc/yum.repos.d"

def update():
    cloudinit.log.debug(" -- repo_yum handler/update() --")
    subprocess.Popen([YUMBIN, 'makecache']).communicate()

def upgrade(upgrade = util.UPGRADE_SECURITY):
    cloudinit.log.debug(" -- repo_yum handler/upgrade() --")
    args = []
    if upgrade == util.UPGRADE_SECURITY:
        args.append("--security")
    # we treat bugfixes like "all" since it is hard to explain what is a
    # non-bugfix update
    subprocess.Popen([YUMBIN, 'upgrade', '-y'] + args).communicate()

def install(pkglist):
    cloudinit.log.debug(" -- repo_yum handler/install() --")

    cmd = [YUMBIN, 'install', '-y']
    cmd.extend(pkglist)
    subprocess.Popen(cmd).communicate()

def generate(repo_cfg):
    cloudinit.log.debug(" -- repo_yum handler/generate() --")

    if 'name' not in repo_cfg:
        # Pull name from python
        dist_full = platform.linux_distribution()
        name = dist_full[0]
        repo_cfg['name'] = name
    else:
        name = repo_cfg['name']

    if 'version' not in repo_cfg:
        repo_cfg['version'] = 'latest'

    # Most configs should use mirror in URL specifications
    repo_cfg['mirror'] = get_mirror(repo_cfg)

    if repo_cfg['mirror'] == None:
        cloudinit.log.error("No mirror for yum repo- bailing!")
        raise Exception("No mirror defined for yum-repo!")
    else:
        # render all the templates that match the glob $name*.repo.tmpl
        tmpl_glob = '%s*.repo.tmpl' % name
        for tmpl in glob.glob(os.path.join(util.templatesdir, tmpl_glob)):
            # remove the .tmpl from the glob filename
            reponame = os.path.basename(tmpl)[:-5]
            filename = os.path.join(YUMREPOS, reponame)
            util.render_to_file(reponame, filename, repo_cfg)

def get_mirror(repo_cfg):
    if 'mirror' in repo_cfg:
        # mirror hard coded in config
        return repo_cfg['mirror']

    # regional_mirror and default_mirror can specify named variables.
    # This is the mechanism to fill out the mirror based on:
    #  - distribution config
    #  - cloud config
    #  - datasource availability zone
    # example:  %(dist_name)s.%(ec2_az)s.%(domain)s.com
    #           - each of these variables need to be defined
    mirror = None

    if 'regional_mirror' in repo_cfg:
        regional_mirror = repo_cfg['regional_mirror']
        mirror = regional_mirror % repo_cfg
        try:
            cloudinit.log.debug("Checking integrity of regional hostname: %s" % mirror)
            socket.getaddrinfo(mirror, None, 0, socket.SOCK_STREAM)
            return mirror
        except:
            cloudinit.log.warn("Unable to resolve regional mirror: %s" % mirror)

    # If you do not specify default_mirror in config, will return the regional_mirror
    if 'default_mirror' in repo_cfg:
        default_mirror = repo_cfg['default_mirror']
        mirror = default_mirror % repo_cfg
        try:
            cloudinit.log.debug("Checking integrity of default mirror: %s" % mirror)
            socket.getaddrinfo(mirror, None, 0, socket.SOCK_STREAM)
            return mirror
        except:
            cloudinit.log.warn("Unable to resolve default mirror: %s" % mirror)

    return mirror

def add(repolist):
    cloudinit.log.debug(" -- repo_yum handler/add() --")
    elst = []

    for ent in repolist:
        if not ent.has_key('source'):
            elst.append([ "", "missing source" ])
            continue

        source=ent['source']

        if not ent.has_key('filename'):
            ent['filename']='cloud_config.repo'

        if not ent['filename'].startswith("/"):
            ent['filename'] = os.path.join(YUMREPOS, ent['filename'])

        if ( ent.has_key('keyid') and not ent.has_key('key') ):
            elst.append([source,"no key server defind"])

        if not ent.has_key('enabled'):
            ent['enabled']=0

        ent['enabled'] = str(ent['enabled'])

        if not ent.has_key('key'):
            elst.append([source,"key not defined"])
            continue

        if not ( ent.has_key('baseurl') or ent.has_key('mirrorlist') ):
                elst.append([source,"baseurl or mirrorlist not defined"])
                continue

        if not ent.has_key('mirror_expire'):
            ent['mirror_expire']="5m"

        ent['mirror_expire'] = str(ent['mirror_expire'])

        repo_entry = "[" + source + "]\n" \
                     + "name="    + ent['name']    + "\n"
        if ent.has_key('baseurl'):
            repo_entry += "baseurl=" + ent['baseurl'] + "\n"
        if ent.has_key('mirrorlist'):
            repo_entry += "mirrorlist=" + ent['mirrorlist'] + "\n" \
                     + "mirror_expire=" + ent['mirror_expire'] + "\n"
        repo_entry += "enabled=" + ent['enabled'] + "\n" \
                     + "gpgkey="  + ent['key']     + "\n"

        try: util.write_file(ent['filename'], repo_entry + "\n")
        except:
            elst.append([source, "failed write to file %s" % ent['filename']])

        return(elst)
