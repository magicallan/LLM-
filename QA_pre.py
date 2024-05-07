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
    # parser.add_argument("--config_path", type=str, default="./llms/remote/configs/mistral7B.json")
    parser.add_argument("--config_path", type=str, default="./llms/remote/configs/wsx_gpt35.json")
    args = parser.parse_args()

    # 定义一个Logger
    logger = set_logger("tmp.log")

    # 定义一个Agent
    chat_gpt = ChatGPTLLM(args.config_path)
    # chat_gpt = MistralLLM(args.config_path)

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
    # cn_data1 = {
    #     "{{Question}}": "《罪与罚》的作者陀思妥耶夫斯基展现的是____",
    #     "{{Type}}": "单选题",
    #     "{{Options}}": "A.对自然的讴歌，对自由自在生活的思考与探索。   B.对人间至情的叹惋，对生命荣枯的歌唱。  \
    #     C.浓厚的人文情怀与审美立场，对乡土风俗美，人性美的描绘。   D.对人类心灵的拷问，深刻的人道主义慈悲胸怀。",
    # }
    # cn_data2 = {
    #     "{{Question}}": """“王者匠心，真正的创新源于对____的探索。”机器智能的时代，有两种精神在工科院校极其重要：\
    #     其一，匠人精神；其二，创新精神，尤其人文创新精神。前者如稻盛和夫，他有一句非常精彩的由衷的话：做出好产品的人，能够听到产品的声音。\
    #     后者如乔布斯，他“Stay hungry, Stay foolish”,是匠心与创新精神的典范。他们的作品都是面向人的，他们的出色出于对人性的精微的把握。在工科院校，愿大家注重通识博雅情操的培养，注重人文学科的学习。\
    #     也愿这能贯穿我们所有人的一生。“王者匠心，真正的创新源于对人性的探索。”""",
    #     "{{Type}}": "单选题",
    #     "{{Options}}": "A.市场    B.时代     C.人性   D.社会",
    # }
    # cn_data3 = {
    #     "{{Question}}": "董其昌提出南北宗论董其昌认为中国绘画有两条线，当然他这里是以山水做例子：一种是由李思训所开创的北派，北派金碧辉煌，主要是要靠颜色来作画；\
    #     另外一点是逼真，靠刻苦和用功夫功力来完成绘画。另一种是以____所开创的南宗，认为绘画最重要的功能，不是为了完成某种任务，不是为皇家服务，而是为自我，寄托自己的情感，寄托自己对人生的感悟。\
    #     这两条线索画下来，尽管可能并不符合绘画史的本来样貌，但他从南北宗的角度来划分中国山水画，逐步抽象地把中国艺术的精神提炼出来了。",
    #     "{{Type}}": "单选题",
    #     "{{Options}}": "A.吴道子   B.王维",
    # }
    # cn_data4 = {
    #     "{{Question}}": "《名人传》是法国作家罗曼·罗兰所著____三部传记的总称。",
    #     "{{Type}}": "多选题",
    #     "{{Options}}": "A.《贝多芬传》   B.《米开朗琪罗传》  C.《托尔斯泰传》   D.《雨果传》",
    # }
    # cn_data5 = {
    #     "{{Question}}": "有我之境，以我观物，故物皆著我之色彩。无我之境，以物观物，故不知何者为我，何者为物。以下属于“无我之境”的是____",
    #     "{{Type}}": "多选题",
    #     "{{Options}}": "A.泪眼问花花不语，乱红飞过秋千去。   B.采菊东篱下，悠然见南山。  C.可堪孤馆闭春寒，杜鹃声里斜阳暮。   D.寒波澹澹起，白鸟悠悠下。",
    # }
    # en_data1 = {
    #     "{{Question}}": "The source of Steve Jobs’ lifelong inspiration lies in ____",
    #     "{{Type}}": "single-choice",
    #     "{{Options}}": "A.Chinese Taoist philosophy   B.Oriental wisdom of Zen Buddhism\
    #       C.The pragmatic spirit of Stanford University   D.The humanistic spirit of Harvard University",
    # }
    # en_data2 = {
    #     "{{Question}}": """What is the "Classicism spirit" of the West? ____""",
    #     "{{Type}}": "multiple-choice(here be more than one correct answer)",
    #     "{{Options}}": "A.The profound unity of inner beauty and outer beauty   B.A high degree of unity of reason and emotion\
    #     C.The profound unity of profound intellectual content and perfect artistic form \
    #     D.It's a very simple and elegant spiritual pursuit of human aesthetics, with the commonality of beauty, and lays the foundation of Western culture."
    # }
    # en_data3 = {
    #     "{{Question}}": "The ways of making Chinese characters include ____",
    #     "{{Type}}": "multiple-choice(here be more than one correct answer)",
    #     "{{Options}}": "A.pictograms   B.phono-semantic characters  C.simple ideograms  D. compound ideograms",
    # }

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
