from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["POST"])
def upload_pdf(request):
    # TODO: extract -> chunk -> embed -> store
    return Response({"message": "upload endpoint - not implemented yet"}, status=501)


@api_view(["POST"])
def ask_question(request):
    # TODO: embed query -> search -> generate answer
    return Response({"message": "ask endpoint - not implemented yet"}, status=501)


@api_view(["POST"])
def generate_quiz_view(request):
    # TODO: retrieve chunks -> generate MCQs
    return Response({"message": "quiz endpoint - not implemented yet"}, status=501)