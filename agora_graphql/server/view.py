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

from flask_graphql import GraphQLView

__author__ = 'Fernando Serena'

from flask import request


class AgoraGraphQLView(GraphQLView):
    def __init__(self, **kwargs):
        super(AgoraGraphQLView, self).__init__(**kwargs)

    def get_context(self):
        if request.method == 'GET':
            gql_query = request.args.get('query') or ''
        else:
            gql_query = request.json['query']

        q_params = dict(request.args.items())
        if 'query' in q_params:
            del q_params['query']

        return {
            'query': gql_query,
            'introspection': 'introspection' in gql_query.lower(),
            'parameters': q_params
        }
