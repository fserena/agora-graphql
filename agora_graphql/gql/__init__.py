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
from graphql import parse, build_ast_schema, MiddlewareManager, Source, validate, execute
from graphql.execution import ExecutionResult

from agora_graphql.gql.executor import AgoraExecutor
from agora_graphql.gql.middleware import AgoraMiddleware

__author__ = 'Fernando Serena'


class GraphQLProcessor(object):
    def __init__(self, gateway):
        self.__gateway = gateway

        with open('./schema.graphqls') as source:
            document = parse(source.read())
        self.__schema = build_ast_schema(document)

        self.__executor = AgoraExecutor(gateway)
        self.__middleware = MiddlewareManager(AgoraMiddleware(gateway))

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
                context_value= {
                    'query': q,
                    'introspection': 'introspection' in q.lower()
                },
                middleware=self.__middleware,
                executor=self.__executor
            )
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)
