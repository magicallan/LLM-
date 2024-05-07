import argparse
import json
from llms.applications.QA1prompt import MULTIPLE_QUESTION_ANSWER_PROMPT_PATTERN
from llms.applications.tmp_utils import set_logger
from llms.remote import RemoteLLMs
from llms.remote.ChatGPT import ChatGPTLLM
from llms.remote.Mistral7B import MistralLLM
from gevent import pywsgi
import flask


class QA1Agent:
    def __init__(self, logger, llm_model: RemoteLLMs, language,
                 in_context_examples=[], more_guidance=[], more_task_definition=[]):
        """
        :param logger:
        :param llm_model: 给定一个RemoteLLMs的实例化对象
        :param language:  数据的语言
        :param in_context_examples: 如果需要给定In Context的例子，给对应的数组，每个例子一个Dict
        :param more_guidance: 通过的数组的形式提供补助
        :param more_task_definition:  通过数组的形式提供更多的任务定义补充
        """
        self.logger = logger
        self.llm_model = llm_model
        self.prompt_pattern = MULTIPLE_QUESTION_ANSWER_PROMPT_PATTERN

        # 处理额外的输入
        more_task_definition = '\n'.join(more_task_definition)

        # In-Context Examples 的设置
        if len(in_context_examples) > 0:
            more_guidance.append('To help your judgment, some examples are provided in [Examples].')
            in_context_prompt = ["[Examples]", "'''"]
            in_context_prompt.append(json.dumps(in_context_examples, ensure_ascii=False, indent=4))
            in_context_prompt.append("'''")
            in_context_prompt = '\n'.join(in_context_prompt)
        else:
            in_context_prompt = ""

        # 是否有更多需要补充的指南
        tmp = []
        for idx, guidance in enumerate(more_guidance):
            tmp.append('%s. %s' % (idx + 4, guidance))
        more_guidance = '\n'.join(tmp)

        self.meta_dict = {
            "{{Language}}": language,
            "{{MORE_GUIDANCE}}": more_guidance,
            "{{MORE_TASK_DEFINITION}}": more_task_definition,
            "{{In-Context Examples}}": in_context_prompt
        }

    def change_language(self, language):
        self.meta_dict["{{Language}}"] = language

    def get_answer(self, case_data):
        llm_model = self.llm_model
        repeat_times = -1

        while True:
            repeat_times += 1
            if repeat_times >= llm_model.max_retries:
                break
            # 首先构造prompt
            prompt = llm_model.fit_case(pattern=self.prompt_pattern, data=case_data, meta_dict=self.meta_dict)
            contexts = llm_model.create_prompt(prompt)
            results = llm_model.request_llm(contexts, repeat_times=repeat_times)

            if results is not None and results[-1]['role'] == 'assistant':
                extracted_results = self.extract_answer(results[-1]['content'])
                if extracted_results is not None:
                    return prompt, extracted_results

        return None

    def extract_answer(self, last_response: str):
        try:
            last_response = last_response.strip('\r\n')
            # 找到JSON字符串的开始和结束位置
            start = last_response.find('{')
            end = last_response.rfind('}') + 1

            # 提取JSON字符串
            json_str = last_response[start:end]
            json_str = json_str.replace("\n", "")

            # 将JSON字符串解析为Python字典
            print(json_str)
            data_dict = json.loads(json_str)

            return data_dict
        except Exception as e:
            raise e
            return None


if __name__ == '__main__':
    # https://platform.openai.com/docs/api-reference

    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", type=str, default="./llms/remote/configs/mistral7B.json")
    args = parser.parse_args()

    # 定义一个Logger
    logger = set_logger("tmp.log")

    # 定义一个Agent
    chat_gpt = MistralLLM(args.config_path)

    # 定义参数
    language = "Chinese"
    # language = "English"

    more_guidance = ['']

    in_context_examples = [
        {
            "Input": {
                "Question": "鲁迅所生活的年代正是中国从传统向现代转换最艰难、最曲折、最痛苦的年代，他感应民族、时代的召唤，先是走科学救国的道路，后来转向文学救国的道路。\
                经过“中国是一个铁屋子万难打破也许能打破”的思辨，鲁迅开始时代的“呐喊”，这便是中国现代文学史上第一部真正具有划时代精神和美学追求的小说____。开启了自己的小说创作生涯，也开启了中国现代小说的序幕。",
                "type": "单选题",
                "Options": "A.《狂人日记    B.《阿Q正传》   C.《祥林嫂》   D.《药》",
            },
            "Output": {
                "Background": "鲁迅及中国现代文学史",
                "Right_answer": "A.《狂人日记》",
                "Options_analysis": "A.《狂人日记》：《狂人日记》是鲁迅的代表作之一，是中国现代文学史上第一部具有划时代精神和美学追求的小说，开启了中国现代小说的序幕，符合题干描述。\
                B.《阿Q正传》：《阿Q正传》是鲁迅的另一部代表作，虽然也具有重要意义，但并非中国现代文学史上第一部具有划时代精神和美学追求的小说。\
                C.《祥林嫂》：祥林嫂是鲁迅短片小数《祝福》中的人物，与现实不符故不正确。\
                D.《药》：《药》是鲁迅的散文之一，虽然也有其重要性，但并非小说作品，与题干描述不符",
            }
        }
    ]

    QA1_agent = QA1Agent(logger, chat_gpt, language=language,
                         more_guidance=more_guidance, in_context_examples=in_context_examples)

    app = flask.Flask(__name__)

    @app.route("/service/api/QA", methods=["GET", "POST"])
    def QA_analysis():
        data = {"success": 0}
        result = None
        param = flask.request.get_json()
        print(param)
        question = param["question"]
        print(question)
        language = param["language"]
        QA1_agent.change_language(language)
        print(language)
        _prompt, _res = QA1_agent.get_answer(question)
        data["data"] = _res
        data["success"] = 1
        return flask.jsonify(data)


    server = pywsgi.WSGIServer(("0.0.0.0", 60063), app)
    server.serve_forever()

