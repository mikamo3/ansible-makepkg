#!/usr/bin/python

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible.module_utils.basic import AnsibleModule
import os
import re
import tempfile

DOCUMENTATION = """
"""

RETURN = """
"""

EXAMPLES = """
"""

REGEX_PACKAGENAME = r".*/(.*)$"
DEF_LANG = ["env", "LC_ALL=C"]
COMMANDS = {
    "git": ["git", "clone"],
    "makepkg": ["makepkg", "--syncdeps", "--install", "--noconfirm", "--needed"],
}


def check_package_installed(module, package):
    rc, _, _ = module.run_command(["pacman", "-Q", package], check_rc=False)
    return rc == 0


def makepkg(module, package):
    current_path = os.getcwd()
    git_path = "git@github.com:{}.git".format(package)
    with tempfile.TemporaryDirectory() as tmpdir:
        rc, out, err = module.run_command(
            COMMANDS["git"] + [git_path] + [tmpdir], check_rc=True
        )
        os.chdir(tmpdir)
        rc, out, err = module.run_command(DEF_LANG + COMMANDS["makepkg"], check_rc=True)
        os.chdir(current_path)
    return (rc, out, err)


def check_packages(module, packages):
    would_be_changed = []

    for package in packages:
        installed = check_package_installed(module, package)
        if not installed:
            would_be_changed.append(package)

    if would_be_changed:
        status = True
        message = "{} package(s) would be installed".format(len(would_be_changed))
    else:
        status = False
        message = "{} package(s) are already installed"
    module.exit_json(changed=status, msg=message)


def install_packages(module, packages):
    changed_iter = False
    for package in packages:
        matched = re.match(REGEX_PACKAGENAME, package)
        if not matched:
            module.fail_json(msg="invalid name {}".format(package))
        if check_package_installed(module, matched.group(1)):
            rc = 0
            continue
        rc, _, _ = makepkg(module, package)
        changed_iter = True
    message = "installed package(s)" if changed_iter else "package(s) already installed"
    module.exit_json(changed=changed_iter, msg=message, rc=rc)


def main():
    module = AnsibleModule(
        argument_spec={"name": {"type": "list"}},
        required_one_of=[["name"]],
        supports_check_mode=True,
    )
    params = module.params

    if module.check_mode:
        check_packages(module, params["name"])

    install_packages(module, params["name"])


if __name__ == "__main__":
    main()
