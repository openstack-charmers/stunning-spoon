import unittest
from unittest.mock import patch, mock_open

import identify_outdated_packages


TEMPLATE_YAML = """---
source: test-release
destination: ppa:user/test-ppa-name
packages:
  - package1
  - package2
"""


class TestOutdatedPackages(unittest.TestCase):

    def test_lists_correct_packages(self):
        with patch(
                "builtins.open",
                mock_open(read_data=TEMPLATE_YAML)) as mock_file:
            packages = identify_outdated_packages.list_packages('test.yaml')
        mock_file.assert_called_with('test.yaml', 'r')
        self.assertEqual(['package1', 'package2'], packages)

    # def test_identifies_outdated_package(self):
        # self.assertTrue(identify_outdated_packages.is_outdated('package1'))
        # self.assertFalse(identify_outdated_packages.is_outdated('package2'))
