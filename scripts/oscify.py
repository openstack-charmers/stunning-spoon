#!/use/bin/env python3

import logging
import yaml
from os import listdir
from os.path import isfile, join

GERRIT_JOB = """
- name: {name}
  parent: {parent}
  vars:
    package_name: {package_name}
"""

ABSTRACT_JOB = """---
- name: {name}
  abstract: true
  vars:
    uca: {uca}
"""


def main():
    config_files = [f for f in listdir('cloud-archive-config') if
                    isfile(join('cloud-archive-config', f))]
    logging.info("Reading UCA config files")
    pockets = {}
    for config_file in config_files:
        with open(join('cloud-archive-config', config_file), 'r') as file:
            try:
                pockets[config_file.split('.')[0]] = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print(exc)
                raise
    print(pockets)
    for pocket, config in pockets.items():
        zuul_config = ABSTRACT_JOB.format(name=pocket, uca=pocket)
        for package in config.get('packages', []):
            zuul_config += \
                GERRIT_JOB.format(name=f"backport-{pocket}-{package}",
                                  parent=pocket, package_name=package)
        print(f"{pocket} config:\n\n{zuul_config}")
        with open(join('osci.d', f'{pocket}.yaml'), 'w+') as f:
            f.write(zuul_config)


if __name__ == '__main__':
    main()

