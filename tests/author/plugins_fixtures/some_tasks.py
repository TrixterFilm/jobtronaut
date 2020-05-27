# ######################################################################################################################
#  Copyright 2020 TRIXTER GmbH                                                                                         #
#                                                                                                                      #
#  Redistribution and use in source and binary forms, with or without modification, are permitted provided             #
#  that the following conditions are met:                                                                              #
#                                                                                                                      #
#  1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following #
#  disclaimer.                                                                                                         #
#                                                                                                                      #
#  2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the        #
#  following disclaimer in the documentation and/or other materials provided with the distribution.                    #
#                                                                                                                      #
#  3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote     #
#  products derived from this software without specific prior written permission.                                      #
#                                                                                                                      #
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,  #
#  INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE   #
#  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,  #
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS        #
#  OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF           #
#  LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY    #
#  OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.                                 #
# ######################################################################################################################


from trixter.farmsubmit.author import Task
from trixter.farmsubmit.author import ProcessorDefinition


TASKS_DICT = {
    "TaskOne": "",
    "TaskTwo": "",
    "TaskThree": ""
}

PROCESSOR_SCOPE = [
    ["uno.initial", "uno.processed"],
    ["dos.processed"],
    ["tres.initial"]
]

_task_names_sorted = sorted(TASKS_DICT.keys())
for i, _NAME in enumerate(_task_names_sorted):
    if i == 0:  # we expect the first task will get all other available tasks as required
        _required = _task_names_sorted[1:]
    else:
        _required = []
    TASKS_DICT[_NAME] = type(
        _NAME,
        (Task, ),
        {
            "argument_processors": [
                ProcessorDefinition(
                    name="ProcessorOne",
                    scope=PROCESSOR_SCOPE[i],
                    parameters={}
                )
            ],
            "required_tasks": _required,
            "elements_id": "uno",
        }
                             )
    locals()[_NAME] = TASKS_DICT[_NAME]