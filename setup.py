import sys
from setuptools import setup
from setuptools import find_packages

reqs = [
  'sanic==21.9.*'
]

setup(
  name='concierge',
  version='0.1.0',
  description='realtime recommendation engine',
  url='https://github.com/victusfate/concierge',
  author='victusfate',
  author_email='messel@gmail.com',
  license='MIT',
  packages=find_packages(),
  install_requires = reqs,
  dependency_links = [
    'git+https://github.com/victusfate/rsyslog_cee.git@main#egg=rsyslog_cee',
    'git+https://github.com/victusfate/bandolier.git@main#egg=bandolier'
  ],
  zip_safe=False
)
