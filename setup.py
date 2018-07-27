"""
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=#
  Copyright (C) 2018 Fernando Serena.
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=#
  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

            http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=#
"""

import json

from setuptools import setup, find_packages

__author__ = 'Fernando Serena'

with open("agora_graphql/metadata.json", 'r') as stream:
    metadata = json.load(stream)

setup(
    name="agora-graphql",
    version=metadata['version'],
    author=metadata['author'],
    author_email=metadata['email'],
    description=metadata['description'],
    license="Apache 2",
    keywords=["agora", "discovery", "linked data", "graphql"],
    url=metadata['github'],
    download_url="https://github.com/fserena/agora-graphql/tarball/{}".format(metadata['version']),
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    install_requires=['requests', 'futures', 'python-dateutil', 'graphql-core', 'Flask-Cors',
                      'Flask-GraphQL>=2.0', 'agora-gw', 'agora-wot', 'agora-py', 'shortuuid', 'expiringdict'],
    classifiers=[],
    include_package_data=True,
    package_dir={'agora_graphql': 'agora_graphql'},
    package_data={'agora_graphql': ['metadata.json']},
    scripts=['gql']
)
