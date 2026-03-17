import requests
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def ai_generate(request):
    text = request.query_params.get("q")

    if not text:
        return Response({"error": "Missing ?q= parameter"}, status=400)

    try:
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": text,
                "langpair": "en|fr"
            },
            timeout=5
        )

        r.raise_for_status()
        return Response(r.json())

    except requests.RequestException as e:
        return Response({"error": str(e)}, status=500)
