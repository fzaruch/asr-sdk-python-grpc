import asyncio
import getopt, sys
import grpc
import logging
import RecognizeService_pb2_grpc
import RecognizeService_pb2
from concurrent.futures import ThreadPoolExecutor

def usage(args):
    print("Usage:")
    print("\t{} -f <audio_file_name>".format(args[0]))
    print("\t{} -c <true/false>".format(args[0]))
    sys.exit(2)


def get_boolean_par(args, arg):
    value = False
    if args.get(arg) is not None:
        if args.get(arg.lower()) == "true":
            value = True
    return value

def fill_config_request(args):
    languageModel = []
    languageModel.append(
        RecognizeService_pb2.RecognitionConfig.LanguageModel(uri="builtin:slm/general", content_type="text/uri-list"))
    print("Continuos={}".format(get_boolean_par(args, "continuos_mode")))
    configRequest = RecognizeService_pb2.RecognitionConfig(lm=languageModel,
                                                           continuous_mode=get_boolean_par(args, "continuous_mode"),
                                                           age_scores_enabled=get_boolean_par(args, "cl_age"),
                                                           emotion_scores_enabled=get_boolean_par(args, "cl_emotion"),
                                                           gender_scores_enabled=get_boolean_par(args, "cl_gender")
                                                           )
    return configRequest

def show_result(response):
    is_last = False
    for r in response.result:
        print("Result status: {}".format(r.status))
        for a in r.alternatives:
            print("Text[{}]: {}".format(a.score, a.text))
        if r.age_score.event == "AGE RESULT":
            print("  Age:{}".format(r.age_score.age))
            print("  Confidence:{}".format(r.age_score.confidence))
        if r.emotion_score.event == "EMOTION RESULT":
            print("  Emotion:{}".format(r.emotion_score.emotion))
            print("  Group:{}".format(r.emotion_score.group))
        if r.gender_score.event == "GENDER RESULT":
            print("  Gender:{}".format(r.gender_score.gender))
        if r.last_segment:
            is_last = True
    return is_last


def get_file_stream(args):
    yield RecognizeService_pb2.StreamingRecognizeRequest(config=fill_config_request(args))
    data = bytes()
    with open(args["filename"], 'rb') as reader:
        for d in reader:
            data = data + d
            # print("Size: {}".format(len(data)))
            if len(data) > 20480:
                file_chunk = RecognizeService_pb2.StreamingRecognizeRequest(media=data, last_packet=False)
                data = bytes()
                yield file_chunk
    if len(data) == 0:
        data = b'\x00'
    yield RecognizeService_pb2.StreamingRecognizeRequest(media=data, last_packet=True)

def send_audio(args, stub):
    route_iterator = get_file_stream(args=args)
    response_stream = stub.StreamingRecognize(route_iterator)
    print("Sending audio")
    return response_stream

async def get_result(args, response_stream):
    is_last = False
    while not is_last:
        response = await response_stream.read()
        if response == grpc.aio.EOF:
            continue
        # for response in response_stream:
        print("Error: {}".format(response.error_code))
        print("Event: {}".format(response.event))
        is_last = show_result(response)

async def run_async(args):
    async with grpc.aio.insecure_channel("172.17.0.3:9090") as channel:
        stub = RecognizeService_pb2_grpc.RecognizeServiceStub(channel)
        response_stream = send_audio(args, stub)
        await get_result(args, response_stream)

def run(args):
    with grpc.insecure_channel("172.17.0.3:9090") as channel:
        stub = RecognizeService_pb2_grpc.RecognizeServiceStub(channel)

        file = open(args["filename"], 'rb')
        data = file.read()
        file.close()

        request = RecognizeService_pb2.RecognizeRequest(config=fill_config_request(args), media=data)
        response = stub.Recognize(request)
        print("Error: {}".format(response.error_code))
        print("Event: {}".format(response.event))
        show_result(response)


if __name__ == '__main__':
    logging.basicConfig()
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hsf:c:a:e:g:", ["help", "output="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage(sys.argv)

    steps = []
    args = {}
    run_sync = False
    for o, arg in opts:
        if o == "-f":
            args["filename"] = arg
        elif o == "-c":
            args["continuous_mode"] = arg
        elif o == "-a":
            args["cl_age"] = arg
        elif o == "-e":
            args["cl_emotion"] = arg
        elif o == "-g":
            args["cl_gender"] = arg
        elif o == "-s":
            run_sync = True
        elif o == "--help":
            usage(sys.argv)
    if run_sync:
        run(args)
    else:
        asyncio.get_event_loop().run_until_complete(run_async(args))
