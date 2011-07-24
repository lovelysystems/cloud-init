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

#    Modifications:  New file based on cc_apt_update_upgrade.py
#                    to support generic package setup actions
#                    instead of apt specific ones.  To support
#                    repo actions, package installs, etc, you need
#                    to make sure there is a DistAction handler for
#                    these actions.
import cloudinit.util as util
import cloudinit.DistAction
import subprocess
import traceback
import os

def handle(name,cfg,cloud,log,args):
    update = util.get_cfg_option_bool(cfg, 'repo_update', False)
    # map the various possible upgrade level choices to well known ones
    upgrade_val = util.get_cfg_option_str(cfg, 'repo_upgrade')
    upgrade = util.UPGRADE_NONE
    if upgrade_val:
        if upgrade_val.lower() in [ 'security', 'critical' ]:
            upgrade = util.UPGRADE_SECURITY
        elif upgrade_val.lower() in [ 'fixes', 'bugs', 'bugfix', 'bugfixes' ]:
            upgrade = util.UPGRADE_BUGFIX
        elif upgrade_val.lower() in [ 'true', '1', 'on', 'yes', 'all' ]:
            upgrade = util.UPGRADE_ALL

    dist = cloudinit.DistAction.DistAction("/etc/cloud/dist-defs.cfg")
    
    if not util.get_cfg_option_bool(cfg, 'repo_preserve', True):
        repo_cfg = dist.get_config_section('repo')

        if cfg.has_key("repo_mirror"):
            repo_cfg['mirror'] = cfg["repo_mirror"]
        else:
            # May build mirror from availabity zone information:
            availability_zone = cloud.datasource.get_availability_zone()
            repo_cfg['ec2_az'] = availability_zone[:-1] 
        log.debug("Generating default repo files");
        dist.repo_generate(repo_cfg)

        # Make this part of repo_generate??  (TODO)
        #old_mir = util.get_cfg_option_str(cfg,'repo_old_mirror', \
        #                                  mirror)
        #rename_repo(old_mir, mirror)

    # Equivalent to 'apt_sources': add a new package repository
    if cfg.has_key('repo_additions'):
        log.debug("Adding repo files from config");
        errors = dist.repo_add(cfg['repo_additions'])
        for e in errors:
            log.warn("Source Error: %s\n" % ':'.join(e))

    pkglist = []
    if 'packages' in cfg:
        if isinstance(cfg['packages'],list):
            pkglist = cfg['packages']
        else: pkglist.append(cfg['packages'])

    if update or upgrade or pkglist:
        log.debug("Running update on repo");
        dist.repo_update()

    if upgrade:
        log.debug("Running upgrade on repo");
        dist.repo_upgrade(upgrade)

    if pkglist:
        log.debug("Installing packages from repo");
        dist.repo_install(pkglist)

    return(True)
