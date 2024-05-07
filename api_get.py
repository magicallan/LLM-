import os
import re
import json
import requests
import random


def QA_analysis(text, language):
    url = 'http://127.0.0.1:60063/service/api/QA'
    data = {"question": text, "language": language}
    headers = {'Content-Type': 'application/json;charset=utf8'}
    reponse = requests.post(url, data=json.dumps(data), headers=headers)
    print(reponse.status_code)
    if reponse.status_code == 200:
        reponse = json.loads(reponse.text)
        return reponse['data']
    else:
        return -1


if __name__ == "__main__":

    cn_data1 = {
        "{{Question}}": "《罪与罚》的作者陀思妥耶夫斯基展现的是____",
        "{{Type}}": "单选题",
        "{{Options}}": "A.对自然的讴歌，对自由自在生活的思考与探索。   B.对人间至情的叹惋，对生命荣枯的歌唱。  \
            C.浓厚的人文情怀与审美立场，对乡土风俗美，人性美的描绘。   D.对人类心灵的拷问，深刻的人道主义慈悲胸怀。",
    }
    temple = """《名人传》是法国作家罗曼·罗兰所著____三部传记的总称。", A.《贝多芬传》   B.《米开朗琪罗传》  C.《托尔斯泰传》   D.《雨果传》"""
    print(type(cn_data1))
    reply = QA_analysis(cn_data1, "chinese")
    print(reply)
