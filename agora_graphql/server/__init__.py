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

from agora_gw import Gateway
from flask import Flask
from flask_cors import CORS

from agora_graphql.gql import GraphQLProcessor
from agora_graphql.server.view import AgoraGraphQLView

__author__ = 'Fernando Serena'


def build(**kwargs):
    app = Flask(__name__)
    CORS(app)

    schema_path = kwargs.get('schema', {}).get('path', None)

    gw = Gateway(**kwargs['gateway'])
    gql_processor = GraphQLProcessor(gw, schema_path, data_gw_cache=kwargs.get('gw_cache', None))

    app.add_url_rule('/graphql',
                     view_func=AgoraGraphQLView.as_view('graphql', schema=gql_processor.schema,
                                                        executor=gql_processor.executor,
                                                        middleware=gql_processor.middleware,
                                                        graphiql=True))

    return app
