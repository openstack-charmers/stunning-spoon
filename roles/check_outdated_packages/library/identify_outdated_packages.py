import functools
import logging
import yaml

from apt_pkg import version_compare
# from ubuntutools.logger import Logger
from ubuntutools.lp.lpapicache import (Launchpad, Distribution,
                                       PackageNotFoundException)


def list_packages(config_file):
    with open(config_file, "r") as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            raise
    print(config)
    return config.get('packages', [])


def outdated_packages(
        os_release, source_series, target_series, proposed=False):
    # ca_packages = query_ca_ppa(ppa='%s-staging' % os_release,
    #                            release=target_series)
    ca_packages = [query_ca_ppa(ppa='%s-staging' % os_release,
                                release=target_series, package=p)
                   for p in list_packages()]
    distro_packages = {}
    [distro_packages.update({p: query_distro(p, source_series, proposed)})
     for p in ca_packages.keys()]

    outdated = {}
    for ca_pkg, ca_vers in ca_packages.iteritems():
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
            logging.info(
                'Unable to find package %s in Ubuntu archive' % ca_pkg)
    return outdated


def get_lp():
    if not Launchpad.logged_in:
        Launchpad.login_anonymously()


def query_ca_ppa(ppa, release, owner='ubuntu-cloud-archive',
                 package=None):
    ''' Query a PPA for source packages and versions '''
    get_lp()
    logging.debug("query_ca_ppa: checking ppa=%s, release=%s, owner=%s",
                  ppa, release, owner)
    ppa = Launchpad.people[owner].getPPAByName(name=ppa)
    distro = ppa.distribution.getSeries(name_or_version=release)
    out = {}
    for pkg in ppa.getPublishedSources(distro_series=distro,
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
    print("pkgs: {}".format(pkgs))
    pkgs = sorted(pkgs, key=functools.cmp_to_key(compare), reverse=True)
    return pkgs[0].getVersion()


def compare(x, y):
    return version_compare(x.getVersion(), y.getVersion())
