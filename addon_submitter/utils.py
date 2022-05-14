from __future__ import unicode_literals
import logging
import os
import re
import shutil
import subprocess
import sys
from collections import namedtuple
from io import open
from pprint import pformat
from xml.etree import ElementTree as etree
import requests
import time

__all__ = [
    'create_zip',
    'get_addon_info',
    'create_addon_branch',
    'create_pull_request'
]

AddonInfo = namedtuple(
    'AddonInfo', ['id', 'name', 'version', 'description', 'news', 'gh_url']
)

ADDON_REPO_URL_MASK = 'https://github.com/{}'
FORK_REPO_URL_MASK = 'https://{}:{}@github.com/{}.git'
PR_ENDPOINT_MASK = 'https://api.github.com/repos/xbmc/{}/pulls'
FORK_ENDPOINT_MASK = 'https://api.github.com/repos/xbmc/{}/forks'
USER_FORK_ENDPOINT_MASK = 'https://api.github.com/repos/{}/{}'


ADDON_VERSION_RE = re.compile(r'(<addon.+?version=")([^"]+)(")', re.I | re.DOTALL)
XBMC_PYTHON_VERSION_RE = re.compile(r'(addon="xbmc.python".+?version=")([^"]+)(")',
                                    re.I | re.DOTALL)

this_dir = os.path.dirname(os.path.abspath(__file__))

devnull = open(os.devnull, 'w')

logging.basicConfig(level=10, format='%(name)s - %(levelname)s: %(message)s')
logger = logging.getLogger('addon-submitter')


class AddonSubmissionError(Exception):
    pass


def create_zip(zip_name, addon_id, subdirectory):
    """Create a .zip for an addon

    :param zip_name: .zip file name
    :type zip_name: str
    :param addon_id: addon_id ID
    :type addon_id: str
    :param subdirectory:
    :type addon_id: bool
    """
    logger.info('Creating ZIP file...')
    if subdirectory:
        shell('git', 'archive', '-o', '{}.zip'.format(zip_name), 'HEAD', '--',
              addon_id)
    else:
        shell('git', 'archive', '-o', '{}.zip'.format(zip_name),
              '--prefix', '{}/'.format(addon_id), 'HEAD')
    logger.info('ZIP created successfully.')


def get_addon_info(xml_path):
    """Extract addon info from addon.xml

    :param xml_path: path to addon.xml
    """
    tree = etree.parse(xml_path)
    addon_tag = tree.getroot()
    descr_tag = addon_tag.find('.//description[@lang="en_GB"]')
    if descr_tag is None:
        descr_tag = addon_tag.find('.//description[@lang="en"]')
        if descr_tag is None:
            raise AddonSubmissionError(
                'Unable to find an English description in addon.xml!'
            )
    news_tag = addon_tag.find('.//news')
    if news_tag is not None:
        news = news_tag.text
    else:
        news = ''
    source_tag = addon_tag.find('.//source')
    if source_tag is not None:
        gh_url = source_tag.text
    else:
        repo_slug = os.environ.get('TRAVIS_REPO_SLUG') or os.environ.get('GITHUB_REPOSITORY')
        if repo_slug:
            gh_url = ADDON_REPO_URL_MASK.format(repo_slug)
        else:
            gh_url = ''
    return AddonInfo(
        addon_tag.attrib.get('id'),
        addon_tag.attrib.get('name'),
        addon_tag.attrib.get('version'),
        descr_tag.text,
        news,
        gh_url
    )


def shell(*args, **kwargs):
    """Execute shell command"""
    check = bool(kwargs.get('check'))
    if sys.version_info >= (3, 5):
        subprocess.run(args, check=check, stdout=devnull, stderr=devnull)
    else:
        if check:
            subprocess.check_call(args, stdout=devnull, stderr=devnull)
        else:
            subprocess.call(args, stdout=devnull, stderr=devnull)


def create_addon_branch(work_dir, repo, branch, addon_id, version, subdirectory,
                        gh_username, gh_token, user_email, local_branch_name=None):
    """ Create and addon branch in your fork of the respective addon repo

    :param work_dir: working directory
    :param repo: addon repo name, e.g. 'repo-scripts' or 'repo-plugins'
    :param branch: repo branch that corresponds to Kodi version codename,
        e.g. 'leia'
    :param addon_id: addon ID, e.g. 'plugin.video.example'
    :param version: addon version
    :param subdirectory: addon code in a subdirectory
    :param gh_username: GitHub username
    :param gh_token: GitHub API token
    :param user_email: user's email
    :param local_branch_name: if different from addon ID
    """
    logger.info('Creating addon branch "{}"...'.format(branch))
    repo_fork = FORK_REPO_URL_MASK.format(
        gh_username, gh_token,
        '{}/{}'.format(gh_username, repo)
    )
    repo_dir = os.path.join(work_dir, repo)
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    shell('git', 'clone', '--branch', branch, '--origin', 'upstream',
          '--single-branch', 'https://github.com/xbmc/{}.git'.format(repo))
    os.chdir(repo)
    shell('git', 'config', '--global', 'user.name', '{}'.format(gh_username))
    shell('git', 'config', '--global', 'user.email', user_email)
    local_branch_name = local_branch_name or addon_id
    shell('git', 'checkout', '-b', local_branch_name, 'upstream/{}'.format(branch))
    shutil.rmtree(os.path.join(work_dir, repo, addon_id), ignore_errors=True)
    os.chdir('..')
    if subdirectory:
        shell(
            'sh', '-c',
            'git archive --format tgz HEAD -- {} | tar zxf - -C {}'.format(
                addon_id, repo_dir
            )
        )
    else:
        shell(
            'sh', '-c',
            'git archive --format tgz HEAD --prefix {}/ | tar zxf - -C {}'.format(
                addon_id, repo_dir
            )
        )
    os.chdir(repo)
    shell('git', 'add', '--', addon_id)
    shell('git', 'commit', '-m', '[{}] {}'.format(addon_id, version))
    shell('git', 'push', '-f', '-q', repo_fork, local_branch_name)
    os.chdir(work_dir)
    logger.info('Addon branch "{}" created successfully.'.format(branch))


def create_personal_fork(repo, gh_username, gh_token):
    """Create a personal fork for the official repo on GitHub

    :param repo: addon repo name, e.g. 'repo-scripts' or 'repo-plugins'
    :param gh_username: GitHub username
    :param gh_token: GitHub API token
    """
    logger.info('Creating a personal fork of {}...'.format(repo))
    resp = requests.post(
        FORK_ENDPOINT_MASK.format(
            repo
        ),
        headers={'Accept': 'application/vnd.github.v3+json'},
        auth=(gh_username, gh_token)
    )
    if resp.ok:
        # see: https://developer.github.com/v3/repos/forks/#create-a-forkCheck
        # this is an async operation, wait for a maximum of 5 minutes for the fork
        # to be created (with 20 seconds pause between checks)
        elapsed_time = 0
        while elapsed_time < 5 * 60:
            if not user_fork_exists(repo, gh_username, gh_token):
                time.sleep(20)
                elapsed_time += 20
            else:
                return
        raise AddonSubmissionError("Timeout waiting for fork creation exceeded")
    raise AddonSubmissionError(
        'GitHub API error: {}\n{}'.format(resp.status_code, resp.text)
    )


def user_fork_exists(repo, gh_username, gh_token):
    """Check if the user has a fork of the repository on Github

    :param repo: addon repo name, e.g. 'repo-scripts' or 'repo-plugins'
    :param gh_username: GitHub username
    :param gh_token: GitHub API token
    """
    resp = requests.get(
        USER_FORK_ENDPOINT_MASK.format(
            gh_username,
            repo
        ),
        headers={'Accept': 'application/vnd.github.v3+json'},
        params={
            'type': 'all'
        },
        auth=(gh_username, gh_token)
    )
    resp_json = resp.json()
    return resp.ok and resp_json.get('fork')


def create_pull_request(repo, upstream_branch, local_branch, addon_info,
                        gh_username, gh_token):
    """Create a pull request in the official repo on GitHub

    :param repo: addon repo name, e.g. 'repo-scripts' or 'repo-plugins'
    :param upstream_branch: repo branch that corresponds to Kodi version codename,
        e.g. 'leia'
    :param local_branch: local branch name,
        normally it's addon ID, e.g. 'plugin.video.example'
    :param addon_info: AddonInfo object
    :param gh_username: GitHub username
    :param gh_token: GitHub API token
    """
    logger.info('Checking pull request...')
    resp = requests.get(
        PR_ENDPOINT_MASK.format(repo),
        params={
            'head': '{}:{}'.format(gh_username, local_branch),
            'base': upstream_branch,
        },
        headers={'Accept': 'application/vnd.github.v3+json'},
        auth=(gh_username, gh_token)
    )
    if resp.status_code == 200 and not resp.json():
        logger.info('Submitting pull request...')
        with open(os.path.join(this_dir, 'pr-template.md'), 'r', encoding='utf-8') as fo:
            template = fo.read()
        pr_body = template.format(
            name=addon_info.name,
            id=addon_info.id,
            version=addon_info.version,
            kodi_repo_branch=upstream_branch,
            addon_gh_url=addon_info.gh_url,
            description=addon_info.description,
            news=addon_info.news
        )
        payload = {
            'title': '[{}] {}'.format(local_branch, addon_info.version),
            'head': '{}:{}'.format(gh_username, local_branch),
            'base': upstream_branch,
            'body': pr_body,
            'maintainer_can_modify': True,
        }
        url = PR_ENDPOINT_MASK.format(repo)
        resp = requests.post(
            url,
            json=payload,
            headers={'Accept': 'application/vnd.github.v3+json'},
            auth=(gh_username, gh_token)
        )
        if resp.status_code != 201:
            logger.debug('Pull request URL: {}'.format(url))
            logger.debug('Pull request payload: {}'.format(pformat(payload)))
            raise AddonSubmissionError(
                'GitHub API error: {}\n{}'.format(resp.status_code, pformat(resp.json()))
            )
        logger.info('Pull request submitted successfully:')
    elif resp.status_code == 200 and resp.json():
        logger.info(
            'Pull request in {} for {}:{} already exists.'.format(
                upstream_branch, gh_username, local_branch)
        )
    else:
        raise AddonSubmissionError(
            'Unexpected GitHub error: {}\n{}'.format(resp.status_code, pformat(resp.json()))
        )


def modify_addon_xml_for_matrix(addon_xml_path):
    logger.info('Modifying addon.xml for matrix branch')
    with open(addon_xml_path, 'r', encoding='utf-8') as fo:
        addon_xml = fo.read()
    addon_version_match = ADDON_VERSION_RE.search(addon_xml)
    if addon_version_match is None:
        raise AddonSubmissionError('Unable to parse addon version in addon.xml')
    xbmc_python_version_match = XBMC_PYTHON_VERSION_RE.search(addon_xml)
    if xbmc_python_version_match is None:
        raise AddonSubmissionError('Unable to parse xbmc.python version in addon.xml')
    addon_version = addon_version_match.group(2)
    matrix_addon_version = addon_version + '+matrix.1'
    matrix_addon_version_mask = r'\g<1>{}\g<3>'.format(matrix_addon_version)
    addon_xml = ADDON_VERSION_RE.sub(matrix_addon_version_mask, addon_xml)
    addon_xml = XBMC_PYTHON_VERSION_RE.sub(r'\g<1>3.0.0\g<3>', addon_xml)
    write_addonxml(addon_xml_path, addon_xml)


def get_addonxml_content(addon_xml_path):
    logger.info('Getting addon.xml file content')
    with open(addon_xml_path, 'r', encoding='utf-8') as addonxml:
        return addonxml.read()


def write_addonxml(addon_xml_path, addon_xml):
    with open(addon_xml_path, 'w', encoding='utf-8') as fo:
        fo.write(addon_xml)


def create_git_commit(message):
    os.system('git commit -a -m "{}"'.format(message))
