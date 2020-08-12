#-*- coding:utf-8 -*-
# fabfile.py
# pip install fabric3
# fabric은 서버 세팅에 필요한 모든 과정을 파이썬으로 기록하여 
# 원격 PC에서 자동으로 서버를 세팅하는 자동화 지원 모듈이다. 

from fabric.contrib.files import append, exists, sed, put
from fabric.api import env, local, run, sudo
import os
import json

# 환경설정 파일 로드 

PROJECT_DIR     = os.path.dirname(os.path.abspath(__file__))
envs            = json.load(open(os.path.join(PROJECT_DIR, "deploy.json")))

# 환경설정 데이터 변수로 획득

REPO_URL        = envs['REPO_URL']
PROJECT_NAME    = envs['PROJECT_NAME']
REMOTE_HOST     = envs['REMOTE_HOST']
REMOTE_HOST_SSH = envs['REMOTE_HOST_SSH']
REMOTE_USER     = envs['REMOTE_USER']

env.user = REMOTE_USER
env.hosts = [
    REMOTE_HOST_SSH,
]
env.use_ssh_config = True

# ssh로 접속시 필요한 개인키의 상대경로
env.key_filename = '../kfq_pusan.pem'
# 리눅스에 세팅될 원격 위치
# /home/ubuntu/aws_deploy
project_folder = '/home/{}/{}'.format(env.user, PROJECT_NAME)

# 리눅스상에 기본적으로 설치해야할 모듈들!
# sudo apt-get curl...
apt_requirements = [
    'curl',
    'git',
    'python3-dev',
    'python3-pip',
    'build-essential',
    'apache2',
    'libapache2-mod-wsgi-py3',
    'python3-setuptools',
    'libssl-dev',
    'libffi-dev',
]

#--------------------------------------------------------- 
# 서버를 새로 배포하다 : 외부에서 명령어로 사용됨
# $> fab new_server
def new_server():
    setup()
    deploy()
# 서버 신규 세팅
def setup():
    _get_latest_apt()
    # 서비스 구동에 필요한 모듈을 설치하라
    _install_apt_requirements(apt_requirements)
    _make_virtualenv()
# 최초 배포, 업그레이드 배포
# 업그레이드 배포시 명령
# 코드 수정 -> 로컬테스트 완료 ->git 커밋, push -> fab deploy -> 상용 서버에 반영 완료
# $> fab deploy
def deploy():
    # 저장소에 가서 최신 소스로 서버 상태에 반영한다(git 연동)
    _get_latest_source()
    # _put_envs() <여기서는 생략 >
    # 가상환경 업데이트 
    _update_virtualenv()
    # 서버가 가동될때 홈디렉토리, 로그파일의 위치 등등 설정
    # *.conf 가 수정 및 생성된다. 
    # wsgi.py엔트리포인트가 설정되어 있다. 
    _make_virtualhost()
    # 권한 조정 -> ubuntu가 엑세스 할 수 있게 조정
    _grant_apache2()
    # 아파치 서버 재가동
    _restart_apache2()

#---------------------------------------------------------

def _put_envs():
    pass  # activate for envs.json file
    # put('envs.json', '~/{}/envs.json'.format(PROJECT_NAME))

def _get_latest_apt():
    update_or_not = input('would you update?: [y/n]')
    if update_or_not == 'y':
        # 현재 리눅스의 ㅍㅍ패키지를 최신 상태로 업데이트 해라
        # -y를 물어보면 yes
        # sudo() => root 권한으로 실행해라
        # $>sudo apt-get update && apt-get -y upgrade
        sudo('apt-get update && apt-get -y upgrade')


def _install_apt_requirements(apt_requirements):
    reqs = ''
    for req in apt_requirements:
        reqs += (' ' + req)
    # res => curl git ... install
    # 서비스 구동에 필요한 모듈을 설치하라
    sudo('apt-get -y install {}'.format(reqs))

def _make_virtualenv():
    if not exists('~/.virtualenvs'):
        script = '''"# python virtualenv settings
                    export WORKON_HOME=~/.virtualenvs
                    export VIRTUALENVWRAPPER_PYTHON="$(command \which python3)"  # location of python3
                    source /usr/local/bin/virtualenvwrapper.sh"'''
        run('mkdir ~/.virtualenvs')
        sudo('pip3 install virtualenv virtualenvwrapper')
        run('echo {} >> ~/.bashrc'.format(script))

def _get_latest_source():
    if exists(project_folder + '/.git'):
        # 저장소
        run('cd %s && git fetch' % (project_folder,))
    else:
        run('git clone %s %s' % (REPO_URL, project_folder))
    current_commit = local("git log -n 1 --format=%H", capture=True)
    run('cd %s && git reset --hard %s' % (project_folder, current_commit))
    #run('cd %s && git reset --hard' % (project_folder, ))

def _update_virtualenv():
    # 가상환경에서 서비스가 구동하고자 한다
    # 필요한 패키지를 설치하시오.
    # pip install -r %s/requirements.txt
    virtualenv_folder = project_folder + '/../.virtualenvs/{}'.format(PROJECT_NAME)
    if not exists(virtualenv_folder + '/bin/pip'):
        # $> cd/home/ubuntu/.virtualenvs
        # $> virtualenv aws_deploy : 가상환경을 만들어라
        run('cd /home/%s/.virtualenvs && virtualenv %s' % (env.user, PROJECT_NAME))
    # 해당 가상환경 안에, flask,scikit-learn 이 설치된다. 
    run('%s/bin/pip install -r %s/requirements.txt' % (
        virtualenv_folder, project_folder
    ))

def _ufw_allow():
    sudo("ufw allow 'Apache Full'")
    sudo("ufw reload")

# 서버가 가동될때 홈디렉토리, 로그파일의 위치 등등 설정
# *.conf 가 수정 및 생성된다. 
# wsgi.py엔트리포인트가 설정되어 있다. 
def _make_virtualhost():
    # 서비스 운영을 가상환경을 통해서 제공할 것입데, 
    # 그 가상 환경을 세팅하는 내용
    script = """'<VirtualHost *:80>
    ServerName {servername}
    <Directory /home/{username}/{project_name}>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>
    WSGIDaemonProcess {project_name} python-home=/home/{username}/.virtualenvs/{project_name} python-path=/home/{username}/{project_name}
    WSGIProcessGroup {project_name}
    WSGIScriptAlias / /home/{username}/{project_name}/wsgi.py
    
    ErrorLog ${{APACHE_LOG_DIR}}/error.log
    CustomLog ${{APACHE_LOG_DIR}}/access.log combined
    
    </VirtualHost>'""".format(
        username=REMOTE_USER,
        project_name=PROJECT_NAME,
        servername=REMOTE_HOST,
    )
    sudo('echo {} > /etc/apache2/sites-available/{}.conf'.format(script, PROJECT_NAME))
    sudo('a2ensite {}.conf'.format(PROJECT_NAME))

def _grant_apache2():
    sudo('chown -R :www-data ~/{}'.format(PROJECT_NAME))
    sudo('chmod -R 775 ~/{}'.format(PROJECT_NAME))

def _restart_apache2():
    sudo('sudo service apache2 restart')