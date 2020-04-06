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
    parser.add_argument('-m', '--matrix', action='store_true',
                        help='Submit to the matrix branch as well')
    parser.add_argument('--gh-username', nargs='?', default='',
                        help='GitHub username')
    parser.add_argument('--gh-token', nargs='?', default='',
                        help='GitHub API token')
    parser.add_argument('--user-email', nargs='?', default='',
                        help='User email')
    return parser.parse_args()


def main():
    args = parse_arguments()
    addon_xml_path = os.path.join(work_dir, args.addon_id if args.subdirectory else '', 'addon.xml')
    addon_info = utils.get_addon_info(addon_xml_path)
    if args.zip:
        utils.create_zip(
            args.addon_id + '-' + addon_info.version, args.addon_id, args.subdirectory
        )
    gh_username = os.getenv('GH_USERNAME') or args.gh_username
    gh_token = os.getenv('GH_TOKEN') or args.gh_token
    user_email = os.getenv('EMAIL') or args.user_email
    if args.push_branch or args.pull_request:
        if not (args.repo and args.branch):
            raise utils.AddonSubmissionError(
                'Both --repo and --branch arguments must not defined!'
            )
        if not (gh_username and gh_token and user_email):
            raise utils.AddonSubmissionError(
                'GitHub username, token and user email must be specified '
                'either via environment variables or as command line arguments'
            )

        # fork the repo if the user does not have a personal repo fork
        if not utils.user_fork_exists(args.repo, gh_username, gh_token):
            utils.create_personal_fork(args.repo, gh_username, gh_token)

        utils.create_addon_branch(
            work_dir, args.repo, args.branch, args.addon_id, addon_info.version,
            gh_username, gh_username, user_email, args.subdirectory
        )

    if args.pull_request:
        utils.create_pull_request(
            args.repo, args.branch, args.addon_id, addon_info, gh_username, gh_token
        )
    if args.matrix:
        os.chdir(work_dir)
        utils.modify_addon_xml_for_matrix(addon_xml_path)
        utils.create_git_commit('Modify versions for matrix branch')
        addon_info = utils.get_addon_info(addon_xml_path)
        local_branch_name = args.addon_id + '@matrix'
        utils.create_addon_branch(
            work_dir, args.repo, 'matrix', args.addon_id, addon_info.version, args.subdirectory,
            gh_username, gh_token, user_email, local_branch_name=local_branch_name
        )
        if args.pull_request:
            utils.create_pull_request(
                args.repo, 'matrix', local_branch_name, addon_info,
                gh_username, gh_token
            )


if __name__ == '__main__':
    main()
