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
from expiringdict import ExpiringDict
from graphql import parse, build_ast_schema, MiddlewareManager, Source, validate, execute
from graphql.execution import ExecutionResult

from agora_graphql.gql.executor import AgoraExecutor
from agora_graphql.gql.middleware import AgoraMiddleware
from agora_graphql.gql.schema import create_gql_schema

__author__ = 'Fernando Serena'


class GraphQLProcessor(object):
    def __init__(self, gateway, schema_path=None, data_gw_cache=None, **kwargs):
        self.__gateway = gateway

        if schema_path:
            with open(schema_path) as f:
                source = f.read()
        else:
            self.__schema_source = create_gql_schema(gateway)
            source = self.__schema_source

        document = parse(source)
        self.__schema = build_ast_schema(document)
        abstract_types = filter(lambda x: hasattr(x, 'resolve_type'), dict(self.__schema.get_type_map()).values())
        for at in abstract_types:
            at.resolve_type = self.__resolve_type

        self.__executor = AgoraExecutor(gateway)

        if not data_gw_cache:
            data_gw_cache = {'max_age_seconds': 300, 'max_len': 1000}

        self.expiring_dict = ExpiringDict(**data_gw_cache)
        middleware = AgoraMiddleware(gateway, data_gw_cache=self.expiring_dict, **kwargs)
        self.__middleware = MiddlewareManager(middleware)

    def __resolve_type(self, *args, **kwargs):
        m = self.middleware.middlewares[0]
        return m.resolve_type(*args, **kwargs)

    @property
    def schema_text(self):
        return self.__schema_source

    @property
    def middleware(self):
        return self.__middleware

    @property
    def executor(self):
        return self.__executor

    @property
    def middleware(self):
        return self.__middleware

    @property
    def schema(self):
        return self.__schema

    def query(self, q):
        try:
            source = Source(q, name='GraphQL request')
            ast = parse(source)
            validation_errors = validate(self.schema, ast)
            if validation_errors:
                return ExecutionResult(
                    errors=validation_errors,
                    invalid=True,
                )
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)

        try:
            return execute(self.__schema,
                           ast,
                           root_value=None,
                           variable_values={},
                           operation_name=None,
                           context_value={
                               'query': q,
                               'introspection': 'introspection' in q.lower()
                           },
                           middleware=self.__middleware,
                           executor=self.__executor
                           )
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)
