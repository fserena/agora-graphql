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

import traceback

from agora import Wrapper
from graphql.execution.executors.thread import ThreadExecutor
from rdflib import ConjunctiveGraph

__author__ = 'Fernando Serena'


class AgoraExecutor(ThreadExecutor):
    def __init__(self, gateway):
        super(AgoraExecutor, self).__init__(pool=False)
        self.gateway = gateway

    def execute_in_thread(self, fn, *args, **kwargs):
        info = args[1]

        try:
            info.context['introspection'] = info.context['introspection'] or info.field_name.startswith(
                '__') or info.parent_type.name.startswith('__')

            if 'fountain' not in info.context:
                info.context['fountain'] = Wrapper(self.gateway.agora.fountain)
                info.context['graph'] = ConjunctiveGraph()

        except Exception as e:
            traceback.print_exc()
        return super(AgoraExecutor, self).execute_in_thread(fn, *args, **kwargs)
