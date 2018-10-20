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
    parser.add_argument('-r', '--repo', nargs='?', default='repo-scripts',
                        help='GitHub repo for this addon type')
    parser.add_argument('-b', '--branch', nargs='?', default='krypton',
                        help='Addon repo branch (Kodi version codename)')
    parser.add_argument('--push-branch', action='store_true',
                        help='Push addon branch to addon repo fork')
    parser.add_argument('--pull-request', action='store_true',
                        help='Create a pull request')
    return parser.parse_args()


def main():
    args = parse_arguments()
    addon_info = utils.get_addon_info(
        os.path.join(work_dir, args.addon_id, 'addon.xml')
    )
    if args.zip:
        utils.create_zip(
            args.addon_id + '-' + addon_info.version, work_dir, args.addon_id
        )
    if args.push_branch or args.pull_request:
        utils.create_addon_branch(
            work_dir, args.repo, args.branch, args.addon_id, addon_info.version
        )
    if args.pull_request:
        utils.create_pull_request(
            args.repo, args.branch, args.addon_id, addon_info
        )


if __name__ == '__main__':
    main()
