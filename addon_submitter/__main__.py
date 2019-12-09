from __future__ import absolute_import, unicode_literals
import argparse
import os
from . import utils

work_dir = os.getcwd()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='CLI utility for submitting Kodi addons '
        'to the official addon repository'
    )
    parser.add_argument('addon_id', nargs='?', help='Addon ID')
    parser.add_argument('-z', '--zip', action='store_true',
                        help='Create a .zip file')
    parser.add_argument('-r', '--repo', nargs='?', default='',
                        help='GitHub repo for this addon type')
    parser.add_argument('-b', '--branch', nargs='?', default='',
                        help='Addon repo branch (Kodi version codename)')
    parser.add_argument('--push-branch', action='store_true',
                        help='Push addon branch to addon repo fork')
    parser.add_argument('--pull-request', action='store_true',
                        help='Create a pull request')
    parser.add_argument('-s', '--subdirectory', action='store_true',
                        help='Addon is stored in its own directory within the git repo')
    return parser.parse_args()


def main():
    args = parse_arguments()
    addon_info = utils.get_addon_info(
        os.path.join(work_dir, args.addon_id if args.subdirectory else '', 'addon.xml')
    )
    if args.zip:
        utils.create_zip(
            args.addon_id + '-' + addon_info.version, args.addon_id, args.subdirectory
        )
    if args.push_branch or args.pull_request:
        if not (args.repo and args.branch):
            raise utils.AddonSubmissionError(
                'Both --repo and --branch arguments must not defined!'
            )

        # fork the repo if the user does not have a personal repo fork
        if not utils.user_fork_exists(args.repo):
            utils.create_personal_fork(args.repo)

        utils.create_addon_branch(
            work_dir, args.repo, args.branch, args.addon_id, addon_info.version, args.subdirectory
        )

    if args.pull_request:
        utils.create_pull_request(
            args.repo, args.branch, args.addon_id, addon_info
        )


if __name__ == '__main__':
    main()
