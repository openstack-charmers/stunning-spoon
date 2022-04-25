#!/usr/bin/env python3
import functools
import yaml

from ansible.module_utils.basic import AnsibleModule
from apt_pkg import version_compare
from ubuntutools.lp.lpapicache import (Launchpad, Distribution,
                                       PackageNotFoundException)


DOCUMENTATION = r'''
---
module: identify_outdated_packages
short_description: Determine packages that need backporting for UCA release
'''

EXAMPLES = r'''
# Determine packages that need backporting for UCA release
- name: Identify Outdated Packages
  identify_outdated_packages:
    openstack_release: yoga
    source_series: jammy
    target_series: focal
    #target_ppa: ppa:chris.macnaughton/yoga-staging-test
    packages:
      - aodh
      - keystone
      - neutron
      - nova
'''

RETURN = r'''
# Example of possible return value
package_jobs:
  description: List of package jobs that need to be run
  returned: success
  type: list
  elements: str
  sample:
    - backport_yoga_keystone
    - backport_yoga_nova
'''


def outdated_packages(os_release, source_series, target_series,
                      packages, module):
    proposed = True

    ca_packages = {}
    for pkg in packages:
        ca_packages.update(query_ca_ppa(ppa='%s-staging' % os_release,
                           release=target_series, package=pkg))
    distro_packages = {}
    for pkg in ca_packages:
        distro_packages.update({pkg: query_distro(pkg, source_series,
                               proposed)})

    outdated = {}
    for ca_pkg, ca_vers in ca_packages.items():
        # strip the ~cloud suffix
        if 'cloud' in ca_vers:
            ca_vers = ca_vers.split('~cloud')[0]
        elif 'ctools' in ca_vers:
            ca_vers = ca_vers.split('~ctools')[0]
        else:
            raise Exception('Unable to determine cloud archive version')
        if distro_packages[ca_pkg]:
            if version_compare(ca_vers, distro_packages[ca_pkg]) < 0:
                outdated[ca_pkg] = {'ubuntu_version': distro_packages[ca_pkg],
                                    'ca_version': ca_vers}
        else:
            module.log(f"Unable to find package {ca_pkg} in Ubuntu archive")
    return outdated


def get_lp():
    if not Launchpad.logged_in:
        Launchpad.login_anonymously()


def query_ca_ppa(ppa, release, owner='ubuntu-cloud-archive',
                 package=None):
    ''' Query a PPA for source packages and versions '''
    get_lp()
    ppa = Launchpad.people[owner].getPPAByName(name=ppa)
    distro = ppa.distribution.getSeries(name_or_version=release)
    out = {}
    for pkg in ppa.getPublishedSources(exact_match=True,
                                       distro_series=distro,
                                       status='Published',
                                       source_name=package):
        out[pkg.source_package_name] = pkg.source_package_version
    return out


def query_distro(package, release, proposed=False):
    ''' Query the release for the version of package '''
    get_lp()
    archive = Distribution('ubuntu').getArchive()
    pkgs = []
    pockets = ['Release', 'Security', 'Updates']
    if proposed:
        pockets.append('Proposed')
    for pocket in pockets:
        try:
            pkg = archive.getSourcePackage(package, release, pocket=pocket)
            pkgs.append(pkg)
        except PackageNotFoundException:
            pass

    if not pkgs:
        return None
    pkgs = sorted(pkgs, key=functools.cmp_to_key(compare), reverse=True)
    return pkgs[0].getVersion()


def compare(x, y):
    return version_compare(x.getVersion(), y.getVersion())


def run_module():
    module_args = dict(
        openstack_release=dict(type='str', required=True),
        source_series=dict(type='str', required=True),
        target_series=dict(type='str', required=True),
        #target_ppa=dict(type='str', required=True),
        packages=dict(type='list', required=True),
    )

    result = dict(
        changed=False,
        package_jobs=[]
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if module.check_mode:
        module.exit_json(**result)

    module.log("Querying outdated packages: {} vs. {}-{}.".format(
               module.params['source_series'],
               module.params['target_series'],
               module.params['openstack_release']))

    outdated = outdated_packages(module.params['openstack_release'],
                                 module.params['source_series'],
                                 module.params['target_series'],
                                 module.params['packages'],
                                 module)
    module.log(f"Outdated packages: {outdated_packages}")

    for pkg, version in outdated.items():
        if pkg not in module.params['packages']:
            continue
        pkg_job = f"backport_{module.params['openstack_release']}_{pkg}"
        result['package_jobs'].append(pkg_job)
        result['changed'] = True
        module.log("{}: Ubuntu ({}): {} > CA ({}): {}".format(
                   pkg,
                   module.params['source_series'],
                   version['ubuntu_version'],
                   module.params['openstack_release'],
                   version['ca_version']))

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
