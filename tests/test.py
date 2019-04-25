import makepkg
import pathlib
import unittest
from unittest.mock import MagicMock, patch
from unittest import mock
from ansible.module_utils.basic import AnsibleModule
import tempfile
import os
import sys


class TestPkgName(unittest.TestCase):
    def setUp(self):
        self.module = MagicMock(spec=AnsibleModule)

    def test_check_package_installed_return_true(self):
        self.module.run_command.return_value = [0, "", ""]
        result = makepkg.check_package_installed(self.module, "pkgname")
        self.assertTrue(result)
        self.module.run_command.assert_called_once_with(
            ['pacman', '-Q', 'pkgname'], check_rc=False)

    def test_check_package_installed_return_false(self):
        self.module.run_command.return_value = [1, "", ""]
        result = makepkg.check_package_installed(self.module, "pkgname")
        self.assertFalse(result)
        self.module.run_command.assert_called_once_with(
            ['pacman', '-Q', 'pkgname'], check_rc=False)

    def test_makepkg_when_gitcommand_failed(self):
        with patch("makepkg.tempfile.TemporaryDirectory") as mocktempfile:
            mocktempfile.return_value.__enter__.return_value = "/tmp/workdir"
            self.module.run_command.return_value = [1, "stdout", "stderr"]
            result = makepkg.makepkg(self.module, "user/repo")
            self.assertEqual(result, (1, "stdout", "stderr"))
            self.module.run_command.assert_called_once_with(
                ['git', 'clone', 'git@github.com:user/repo.git', '/tmp/workdir'], check_rc=True)

    def test_makepkg_when_makepkgcommand_failed(self):
        def run_command_returns(command, check_rc):
            if "git" in command:
                return (0, "", "")
            if "makepkg" in command:
                return (1, "stdout", "stderr")
        run_command_calls = [
            unittest.mock.call(['git', 'clone', 'git@github.com:user/repo.git',
                                '/tmp/workdir'], check_rc=True),
            unittest.mock.call(['env', 'LC_ALL=C', 'makepkg', '--syncdeps',
                                '--install', '--noconfirm', '--needed'], check_rc=True),

        ]
        with patch("makepkg.tempfile.TemporaryDirectory") as mocktempfile:
            with patch("os.chdir"):
                mocktempfile.return_value.__enter__.return_value = "/tmp/workdir"
                self.module.run_command.side_effect = run_command_returns
                result = makepkg.makepkg(self.module, "user/repo")
                self.assertEqual(result, (1, "stdout", "stderr"))
                self.module.run_command.assert_has_calls(run_command_calls)

    def test_makepkg_all_commands_succeed(self):
        def run_command_returns(command, check_rc):
            if "git" in command:
                return (0, "", "")
            if "makepkg" in command:
                return (0, "stdout", "stderr")
        run_command_calls = [
            unittest.mock.call(['git', 'clone', 'git@github.com:user/repo.git',
                                '/tmp/workdir'], check_rc=True),
            unittest.mock.call(['env', 'LC_ALL=C', 'makepkg', '--syncdeps',
                                '--install', '--noconfirm', '--needed'], check_rc=True),
        ]

        with patch("makepkg.tempfile.TemporaryDirectory") as mocktempfile:
            with patch("os.chdir"):
                mocktempfile.return_value.__enter__.return_value = "/tmp/workdir"
                self.module.run_command.side_effect = run_command_returns
                result = makepkg.makepkg(self.module, "user/repo")
                self.assertEqual(result, (0, "stdout", "stderr"))
                self.module.run_command.assert_has_calls(run_command_calls)

    @patch('makepkg.check_package_installed', MagicMock(return_value=False))
    @patch('makepkg.makepkg', MagicMock(return_value=(0, "stdout", "stderr")))
    def test_install_packages_contain_invalid_package(self):
        def fail_json(msg):
            raise ValueError(msg)

        self.module.fail_json.side_effect = fail_json
        with self.assertRaises(Exception) as er:
            makepkg.install_packages(
                self.module, ["foo/bar", "invalid", "bar/baz"])
        self.assertEqual(er.exception.args[0],
                         'invalid name invalid')

    @patch('makepkg.check_package_installed', MagicMock(return_value=False))
    @patch('makepkg.makepkg', MagicMock(return_value=(1, "stdout", "stderr")))
    def test_install_packages_when_makepkg_failure(self):
        def fail_json(msg):
            raise ValueError(msg)

        self.module.fail_json.side_effect = fail_json
        with self.assertRaises(Exception) as er:
            makepkg.install_packages(
                self.module, ["foo/bar",  "bar/baz"])
        self.assertEqual(er.exception.args[0], 'stderr')

    @patch('makepkg.check_package_installed', MagicMock(return_value=False))
    @patch('makepkg.makepkg', MagicMock(return_value=(0, "stdout", "stderr")))
    def test_install_packages_succeed(self):

        makepkg.install_packages(
            self.module, ["foo/bar",  "bar/baz"])

        self.module.exit_json.assert_called_once_with(
            changed=True,
            msg="installed package(s)",
            rc=0
        )


if __name__ == '__main__':
    unittest.main()
