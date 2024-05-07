from django.http import JsonResponse
from django.shortcuts import render, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from llms.applications.QA1 import QA1Agent
from api_get import QA_analysis
import argparse
import json
from llms.applications.QA1prompt import MULTIPLE_QUESTION_ANSWER_PROMPT_PATTERN
from llms.applications.tmp_utils import set_logger
from llms.remote import RemoteLLMs
from llms.remote.ChatGPT import ChatGPTLLM


# Create your views here.
def start(request):
    return render(request, "start.html")


@csrf_exempt
def predicts(request):
    # 从请求中获取input，length，nsamples的值
    print(request.body)
    data = json.loads(request.body)
    question = data.get("input")
    print(question)
    type = data.get("type")
    print(type)
    options = data.get("options")
    language = data.get("language")
    print(language)
    input = {
        "{{Question}}": question,
        "{{Type}}": type,
        "{{Options}}": options,
    }
    output = QA_analysis(input, language)
    analysis = output['Options_analysis']
    answer = output['Right_answer']
    topic = output['Topic']
    dot = '\n'
    format_output = fr"本题主要考察: {topic}{dot}正确选项为：{answer}{dot}选项分析:{dot}{analysis}"
    print(format_output)
    return JsonResponse({"output": format_output})  # 将输出转换为JSON格式的字符串，返回给前端

