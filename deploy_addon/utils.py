from __future__ import unicode_literals
import os
import shutil
import subprocess
import sys
from collections import namedtuple
from xml.etree import ElementTree as etree
import requests

__all__ = [
    'create_zip',
    'get_addon_info',
    'create_addon_branch',
    'create_pull_request'
]

AddonInfo = namedtuple('AddonInfo', ['name', 'version', 'description', 'news'])

REPO_URL_MASK = 'https://{gh_token}@github.com/{repo_slug}.git'
PR_ENDPOINT = 'https://api.github.com/xbmc/{}/pulls'


def clean_pyc(directory):
    """Clean .pyc files recursively in a directory
    
    :param directory: root directory to clean
    :type directory: str
    """
    cwd = os.getcwd()
    os.chdir(directory)
    paths = os.listdir(directory)
    for path in paths:
        abs_path = os.path.abspath(path)
        if os.path.isdir(abs_path):
            clean_pyc(abs_path)
        elif path[-4:] == '.pyc':
            os.remove(abs_path)
    os.chdir(cwd)


def create_zip(zip_name, work_dir, addon_id):
    """Create a .zip for an addon
    
    :param zip_name: .zip file name
    :type zip_name: str
    :param work_dir: working directory
    :type work_dir: str
    :param addon_id: addon_id ID
    :type addon_id: str
    """
    print('Creating ZIP file...')
    clean_pyc(os.path.join(work_dir, addon_id))
    shutil.make_archive(zip_name, 'zip', root_dir=work_dir, base_dir=addon_id)
    print('ZIP created successfully.')


def get_addon_info(xml_path):
    tree = etree.parse(xml_path)
    addon_tag = tree.getroot()
    descr_tag = addon_tag.find('.//description[@lang="en_GB"]')
    news_tag = addon_tag.find('.//news')
    if news_tag:
        news = news_tag.text
    else:
        news = ''
    return AddonInfo(
        addon_tag.attrib.get('name'),
        addon_tag.attrib.get('version'),
        descr_tag.text,
        news
    )


def shell(*args, check=True):
    devnull = open(os.devnull, 'w')
    if sys.version_info >= (3, 5):
        subprocess.run(args, check=check, stdout=devnull, stderr=devnull)
    else:
        if check:
            subprocess.check_call(args, stdout=devnull, stderr=devnull)
        else:
            subprocess.call(args, stdout=devnull, stderr=devnull)


def create_addon_branch(work_dir, repo, branch, addon_id, version):
    print('Creatind addon branch...')
    gh_username = os.environ['GH_USERNAME']
    gh_token = os.environ['GH_TOKEN']
    full_name = os.environ['FULL_NAME']
    email = os.environ['EMAIL']
    repo_fork = REPO_URL_MASK.format(
        gh_token=gh_token,
        repo_slug='{}/{}'.format(gh_username, repo)
    )
    shell('git', 'clone', repo_fork)
    os.chdir(repo)
    shell('git', 'config', 'user.name', '"{}"'.format(full_name))
    shell('git', 'config', 'user.email', email)
    shell('git', 'remote', 'add', 'upstream',
          'https://github.com/xbmc/{}.git'.format(repo))
    shell('git', 'fetch', 'upstream')
    shell('git', 'checkout', '-b', branch, '--track', 'origin/' + branch)
    shell('git', 'merge', 'upstream/' + branch)
    shell('git', 'branch', '-D', addon_id, check=False)
    shell('git', 'checkout', '-b', addon_id)
    clean_pyc(os.path.join(work_dir, addon_id))
    shutil.rmtree(os.path.join(work_dir, repo, addon_id), ignore_errors=True)
    shutil.copytree(
        os.path.join(work_dir, addon_id), os.path.join(work_dir, repo, addon_id)
    )
    shell('git', 'add', '--all', '.')
    shell(
        'git', 'commit',
        '-m', '"[{}] {}"'.format(addon_id, version)
    )
    shell('git', 'push', '-f', '-q', 'origin', addon_id)
    print('Addon branch created successfully.')


def create_pull_request(repo, branch, addon_id, addon_info):
    gh_username = os.environ['GH_USERNAME']
    gh_token = os.environ['GH_TOKEN']
    print('Checking pull request...')
    resp = requests.get(
        PR_ENDPOINT.format(repo),
        params={
            'head': '{}:{}'.format(gh_username, addon_id),
            'base': branch,
        },
        headers={'Accept': 'application/vnd.github.v3+json'},
        auth=(gh_username, gh_token)
    )
    print(resp.json())
    if resp.status_code == 200 and not resp.json():
        print('Submitting pull request...')
        payload = {
            'title': '[{}] {}'.format(addon_id, addon_info.version),
            'head': '{}:{}'.format(gh_username, addon_id),
            'base': branch,
            'body': '{}\n\n{}'.format(addon_info.description, addon_info.news),
            'maintainer_can_modify': True,
        }
        resp = requests.post(
            PR_ENDPOINT.format(repo),
            json=payload,
            headers={'Accept': 'application/vnd.github.v3+json'},
            auth=(gh_username, gh_token)
        )
        if resp.status_code != 201:
            raise RuntimeError(
                'GitHub API error: {}\n{}'.format(resp.status_code, resp.text)
            )
        print('Pull request submitted successfully:')
        print(resp.text)
    elif resp.status_code == 200 and resp.json():
        print(
            'Pull request in {} for {}:{} already exists.'.format(
                branch, gh_username, addon_id)
        )
    else:
        raise RuntimeError(
            'Unexpected GitHub error: {}'.format(resp.status_code)
        )
